"""Sends the admin/subadmin password-reset email via the Gmail API under a
real Google account's OAuth2 consent — not SMTP with a Gmail app password.

Google has rejected plain-password SMTP logins since 2022; the only ways to
send as a Gmail account now are an app password (16-char, requires 2FA) or
OAuth2. This reuses the same OAuth2 client (client_secret.json) already
required for Google Drive, requesting the narrow gmail.send scope only —
enough to send mail as that account, not read or manage it. The connect
flow and token storage mirror drive_service.py exactly, down to reusing its
"real personal account, not a service account" reasoning.
"""

import base64
import logging
import os
from email.mime.text import MIMEText

from django.core.mail.backends.base import BaseEmailBackend
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailError(Exception):
    """Raised for any Gmail-send setup/API failure; callers decide how to surface it."""


def _token_file():
    return os.environ.get("GMAIL_SEND_TOKEN_FILE", "").strip()


def _client_secret_file():
    # Deliberately the same env var as drive_service — one Google Cloud
    # OAuth client covers both scopes; admins only ever upload one
    # credentials file, then authorize it separately for Drive and for
    # sending mail (possibly as different Google accounts).
    return os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "").strip()


def is_configured():
    token_file = _token_file()
    return bool(token_file and os.path.exists(token_file))


def save_credentials(creds):
    token_file = _token_file()
    if not token_file:
        raise GmailError("GMAIL_SEND_TOKEN_FILE is not set.")
    os.makedirs(os.path.dirname(token_file) or ".", exist_ok=True)
    with open(token_file, "w") as f:
        f.write(creds.to_json())


def disconnect():
    token_file = _token_file()
    if token_file and os.path.exists(token_file):
        os.remove(token_file)


def build_oauth_flow(redirect_uri):
    client_secret_file = _client_secret_file()
    if not client_secret_file or not os.path.exists(client_secret_file):
        raise GmailError(
            "GOOGLE_OAUTH_CLIENT_SECRET_FILE is not set or the file doesn't exist — "
            "upload Google credentials in the Drive section first."
        )
    return Flow.from_client_secrets_file(client_secret_file, scopes=SCOPES, redirect_uri=redirect_uri)


def _get_credentials():
    token_file = _token_file()
    if not token_file or not os.path.exists(token_file):
        raise GmailError("No Gmail account connected yet.")
    creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            raise GmailError(
                f"Gmail authorization has expired or was revoked ({exc}). Reconnect below."
            ) from exc
        save_credentials(creds)
        return creds
    raise GmailError("Stored Gmail credentials are invalid and can't be refreshed. Reconnect below.")


def _get_service():
    creds = _get_credentials()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def connected_email_address():
    """The Gmail address currently authorized to send, straight from Google
    (never trust a locally-cached value — if the account changed on Google's
    side this must reflect that immediately)."""
    service = _get_service()
    try:
        profile = service.users().getProfile(userId="me").execute()
    except HttpError as exc:
        raise GmailError(f"Could not read the connected Gmail account: {exc}") from exc
    return profile.get("emailAddress", "")


def _send_raw(to_address, subject, body):
    service = _get_service()
    mime = MIMEText(body)
    mime["to"] = to_address
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
    try:
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
    except HttpError as exc:
        raise GmailError(f"Gmail refused to send to {to_address}: {exc}") from exc


class GmailApiBackend(BaseEmailBackend):
    """Django email backend that sends through the Gmail API instead of SMTP
    — swapped in wherever code previously passed an SMTP EmailBackend, so
    Django's built-in PasswordResetForm.save() keeps working unmodified."""

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            try:
                for to_address in message.to:
                    _send_raw(to_address, message.subject, message.body)
                sent += 1
            except GmailError:
                if not self.fail_silently:
                    raise
                logger.exception("Gmail send failed (fail_silently=True)")
        return sent
