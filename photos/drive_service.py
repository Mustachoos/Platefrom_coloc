"""Google Drive integration.

Auth model: OAuth2 against a real personal Google account (not a service
account — service accounts have no Drive storage quota of their own outside
a Google Workspace Shared Drive, which a free Gmail account doesn't have).

The one-time interactive consent flow is run via
`python manage.py google_drive_auth` (see photos/management/commands/), which
writes a refresh token to GOOGLE_OAUTH_TOKEN_FILE. Every call in this module
reuses/refreshes that token; nothing here opens a browser.
"""

import io
import logging
import os
import re

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class DriveError(Exception):
    """Raised for any Drive setup/API failure; callers decide how to surface it."""


def token_file():
    """Path to the Drive OAuth token file (GOOGLE_OAUTH_TOKEN_FILE) — the
    one place this env var is read; admin_views.py and the google_drive_auth
    management command both import this instead of re-reading it."""
    return os.environ.get("GOOGLE_OAUTH_TOKEN_FILE", "").strip()


def client_secret_file():
    """Path to the shared OAuth client credentials file
    (GOOGLE_OAUTH_CLIENT_SECRET_FILE) — same one-place-to-read-it rationale
    as token_file() above. "Shared" because gmail_service.py's send-mail
    OAuth grant reuses this same client (see admin_views._google_flow)."""
    return os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "").strip()


def _configured_root_folder_id():
    """The env var wins if set (back-compat with existing installs); otherwise
    the DB-backed value the admin account page's Drive step writes — that one
    has to live in the DB rather than a file/env var since it must take
    effect without a container restart."""
    env_value = os.environ.get("GOOGLE_DRIVE_ROOT_FOLDER_ID", "").strip()
    if env_value:
        return env_value
    from .models import SiteSettings

    return SiteSettings.get_solo().drive_root_folder_id


def is_configured():
    """Cheap, no-network check for whether Drive backup is usable at all —
    Drive is optional, so callers use this to skip it silently (not surface
    an error) on installs where it was never set up."""
    token_path = token_file()
    return bool(token_path and os.path.exists(token_path) and _configured_root_folder_id())


def _root_folder_id():
    root = _configured_root_folder_id()
    if not root:
        raise DriveError(
            "No Drive root folder configured. Set it from the admin account page's Drive "
            "step, or set GOOGLE_DRIVE_ROOT_FOLDER_ID."
        )
    return root


def save_credentials(creds):
    """Persist credentials (from the initial consent flow or a refresh) to
    GOOGLE_OAUTH_TOKEN_FILE — the one place that writes this file, shared by
    the management command, the dashboard re-auth view, and token refresh."""
    token_path = token_file()
    if not token_path:
        raise DriveError("GOOGLE_OAUTH_TOKEN_FILE is not set.")
    os.makedirs(os.path.dirname(token_path) or ".", exist_ok=True)
    with open(token_path, "w") as f:
        f.write(creds.to_json())


def build_oauth_flow(redirect_uri):
    """Flow for the web-based (dashboard button) re-auth path — distinct
    from the management command's InstalledAppFlow, which opens its own
    local server/browser and only makes sense run interactively from a
    terminal, not from inside a request handler."""
    client_secret_path = client_secret_file()
    if not client_secret_path or not os.path.exists(client_secret_path):
        raise DriveError(
            "GOOGLE_OAUTH_CLIENT_SECRET_FILE is not set or the file doesn't exist."
        )
    return Flow.from_client_secrets_file(client_secret_path, scopes=SCOPES, redirect_uri=redirect_uri)


def _get_credentials():
    token_path = token_file()
    if not token_path or not os.path.exists(token_path):
        raise DriveError(
            "No Google Drive token found. Run 'python manage.py google_drive_auth' "
            "once (locally, with a browser) to authorize this app."
        )
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            # Google rejected the refresh token itself (revoked, expired, or
            # the OAuth consent screen is still in "Testing" publishing
            # status, where refresh tokens only last 7 days) — a different
            # failure mode than "no token file yet", but callers only need
            # to know Drive isn't reachable right now, same as any other
            # DriveError.
            raise DriveError(
                f"Google Drive authorization has expired or was revoked ({exc}). "
                "Use the 'Reconnect Google Drive' button on the dashboard to re-authorize."
            ) from exc
        save_credentials(creds)
        return creds
    raise DriveError(
        "Stored Google Drive credentials are invalid and can't be refreshed. "
        "Use the 'Reconnect Google Drive' button on the dashboard to re-authorize."
    )


def _get_service():
    try:
        creds = _get_credentials()
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except HttpError as exc:
        raise DriveError(f"Could not connect to Google Drive: {exc}") from exc


def connected_email_address():
    """The Google account currently authorized for Drive access, straight
    from Google — never trust a locally-cached value, since it must reflect
    a reconnect to a different account immediately."""
    service = _get_service()
    try:
        about = service.about().get(fields="user").execute()
    except HttpError as exc:
        raise DriveError(f"Could not read the connected Google account: {exc}") from exc
    return about.get("user", {}).get("emailAddress", "")


def list_root_folders():
    """Folders directly under "My Drive" (not trashed) — used by the setup
    wizard's picker so the user can choose an existing root folder instead
    of typing/pasting an ID."""
    service = _get_service()
    try:
        results = service.files().list(
            q=f"'root' in parents and mimeType = '{FOLDER_MIME_TYPE}' and trashed = false",
            fields="files(id, name)",
            spaces="drive",
            orderBy="name",
        ).execute()
        return results.get("files", [])
    except HttpError as exc:
        raise DriveError(f"Could not list your Drive folders: {exc}") from exc


def create_root_folder(name):
    """Create a new folder directly under "My Drive". Returns its id."""
    service = _get_service()
    try:
        folder = service.files().create(
            body={"name": name, "mimeType": FOLDER_MIME_TYPE, "parents": ["root"]},
            fields="id",
        ).execute()
        return folder["id"]
    except HttpError as exc:
        raise DriveError(f"Could not create Drive folder '{name}': {exc}") from exc


def get_or_create_event_folder(name):
    """Return (folder_id, web_view_link) for a folder named `name` directly
    under the configured root folder, creating it if it doesn't exist yet."""
    service = _get_service()
    root_id = _root_folder_id()
    safe_name = name.replace("'", "\\'")
    query = (
        f"name = '{safe_name}' and '{root_id}' in parents "
        f"and mimeType = '{FOLDER_MIME_TYPE}' and trashed = false"
    )
    try:
        results = service.files().list(
            q=query, fields="files(id, webViewLink)", spaces="drive"
        ).execute()
        existing = results.get("files", [])
        if existing:
            return existing[0]["id"], existing[0].get("webViewLink", "")

        folder = service.files().create(
            body={"name": name, "mimeType": FOLDER_MIME_TYPE, "parents": [root_id]},
            fields="id, webViewLink",
        ).execute()
        return folder["id"], folder.get("webViewLink", "")
    except HttpError as exc:
        raise DriveError(f"Could not create/find Drive folder '{name}': {exc}") from exc


def upload_photo(folder_id, file_path, filename):
    """Upload the file already saved on disk at file_path into folder_id.
    Returns the created Drive file's id."""
    service = _get_service()
    try:
        media = MediaFileUpload(file_path, resumable=False)
        file = service.files().create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media,
            fields="id",
        ).execute()
        return file["id"]
    except HttpError as exc:
        raise DriveError(f"Could not upload '{filename}' to Drive: {exc}") from exc


def trash_file(file_id):
    """Move a Drive file to trash (soft delete, recoverable from Drive's Trash)."""
    service = _get_service()
    try:
        service.files().update(fileId=file_id, body={"trashed": True}).execute()
    except HttpError as exc:
        raise DriveError(f"Could not remove Drive file '{file_id}': {exc}") from exc


def folder_exists(folder_id):
    """Live check (never cached) that folder_id still exists, isn't trashed,
    and is actually a folder. Any failure — not found, trashed, wrong type,
    auth/network issue — is reported simply as False; callers only need to
    know 'is it safe to rely on this folder right now'."""
    if not folder_id:
        return False
    try:
        service = _get_service()
        folder = service.files().get(fileId=folder_id, fields="id, trashed, mimeType").execute()
    except (HttpError, DriveError):
        return False
    return not folder.get("trashed", False) and folder.get("mimeType") == FOLDER_MIME_TYPE


def list_folder_files(folder_id):
    """List non-trashed, non-folder files directly inside folder_id."""
    service = _get_service()
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false and mimeType != '{FOLDER_MIME_TYPE}'",
            fields="files(id, name)",
            spaces="drive",
            pageSize=1000,
        ).execute()
        return results.get("files", [])
    except HttpError as exc:
        raise DriveError(f"Could not list Drive folder '{folder_id}': {exc}") from exc


def download_file(file_id):
    """Return the raw bytes of a Drive file."""
    service = _get_service()
    try:
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()
    except HttpError as exc:
        raise DriveError(f"Could not download Drive file '{file_id}': {exc}") from exc


_FOLDER_URL_RE = re.compile(r"/folders/([a-zA-Z0-9_-]+)")


def extract_folder_id(value):
    """Accept either a bare Drive folder ID or a full folder URL and return the ID."""
    value = value.strip()
    match = _FOLDER_URL_RE.search(value)
    return match.group(1) if match else value


def connect_existing_folder(event):
    """Point `event` at an existing Drive folder, identified by the (possibly
    pasted-as-URL) id currently in event.drive_folder_id. Verifies the folder
    exists and refreshes drive_folder_url to match it. The event's own name
    is left untouched. Returns (ok, message)."""
    folder_id = extract_folder_id(event.drive_folder_id)
    service = _get_service()
    try:
        folder = service.files().get(
            fileId=folder_id, fields="id, name, webViewLink, mimeType", supportsAllDrives=True
        ).execute()
    except HttpError as exc:
        return False, f"Could not find Drive folder '{folder_id}': {exc}"

    if folder.get("mimeType") != FOLDER_MIME_TYPE:
        return False, f"'{folder_id}' is not a Drive folder."

    from .models import Event

    Event.objects.filter(pk=event.pk).update(
        drive_folder_id=folder["id"], drive_folder_url=folder.get("webViewLink", "")
    )
    event.drive_folder_id = folder["id"]
    event.drive_folder_url = folder.get("webViewLink", "")
    return True, folder.get("webViewLink", "")


def share_folder_with_email(folder_id, email, notify=True):
    """Grant reader access on folder_id to email. Returns the new permission's id,
    needed later to revoke that specific grant."""
    service = _get_service()
    try:
        permission = service.permissions().create(
            fileId=folder_id,
            body={"type": "user", "role": "reader", "emailAddress": email},
            sendNotificationEmail=notify,
            fields="id",
        ).execute()
        return permission["id"]
    except HttpError as exc:
        raise DriveError(f"Could not share Drive folder with {email}: {exc}") from exc


def revoke_folder_permission(folder_id, permission_id):
    service = _get_service()
    try:
        service.permissions().delete(fileId=folder_id, permissionId=permission_id).execute()
    except HttpError as exc:
        raise DriveError(f"Could not revoke access (permission {permission_id}): {exc}") from exc


def test_share(folder_id, email):
    """Verify sharing folder_id with email would succeed, without leaving real
    access behind: grants then immediately revokes a silent permission. Used
    when the master sharing toggle is off, so guests still get instant
    feedback if their email can't be granted access."""
    permission_id = share_folder_with_email(folder_id, email, notify=False)
    revoke_folder_permission(folder_id, permission_id)
