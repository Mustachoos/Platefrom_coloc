"""Google Drive integration.

Auth model: OAuth2 against a real personal Google account (not a service
account — service accounts have no Drive storage quota of their own outside
a Google Workspace Shared Drive, which a free Gmail account doesn't have).

The one-time interactive consent flow is run via
`python manage.py google_drive_auth` (see photos/management/commands/), which
writes a refresh token to GOOGLE_OAUTH_TOKEN_FILE. Every call in this module
reuses/refreshes that token; nothing here opens a browser.
"""

import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class DriveError(Exception):
    """Raised for any Drive setup/API failure; callers decide how to surface it."""


def _token_file():
    return os.environ.get("GOOGLE_OAUTH_TOKEN_FILE", "").strip()


def _client_secret_file():
    return os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "").strip()


def _root_folder_id():
    root = os.environ.get("GOOGLE_DRIVE_ROOT_FOLDER_ID", "").strip()
    if not root:
        raise DriveError(
            "GOOGLE_DRIVE_ROOT_FOLDER_ID is not set. Create a folder in your Drive, "
            "share it with yourself if needed, and put its ID in that env var."
        )
    return root


def _get_credentials():
    token_file = _token_file()
    if not token_file or not os.path.exists(token_file):
        raise DriveError(
            "No Google Drive token found. Run 'python manage.py google_drive_auth' "
            "once (locally, with a browser) to authorize this app."
        )
    creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, "w") as f:
            f.write(creds.to_json())
        return creds
    raise DriveError(
        "Stored Google Drive credentials are invalid and can't be refreshed. "
        "Run 'python manage.py google_drive_auth' again."
    )


def _get_service():
    try:
        creds = _get_credentials()
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except HttpError as exc:
        raise DriveError(f"Could not connect to Google Drive: {exc}") from exc


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
    """Upload the file already saved on disk at file_path into folder_id."""
    service = _get_service()
    try:
        media = MediaFileUpload(file_path, resumable=False)
        service.files().create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media,
            fields="id",
        ).execute()
    except HttpError as exc:
        raise DriveError(f"Could not upload '{filename}' to Drive: {exc}") from exc


def share_folder_with_email(folder_id, email):
    service = _get_service()
    try:
        service.permissions().create(
            fileId=folder_id,
            body={"type": "user", "role": "reader", "emailAddress": email},
            sendNotificationEmail=True,
            fields="id",
        ).execute()
    except HttpError as exc:
        raise DriveError(f"Could not share Drive folder with {email}: {exc}") from exc
