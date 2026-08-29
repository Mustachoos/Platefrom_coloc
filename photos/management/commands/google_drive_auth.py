"""One-time interactive Google Drive authorization.

Run this locally (not inside the docker container — it needs to open a
browser): python manage.py google_drive_auth

It writes a refresh token to GOOGLE_OAUTH_TOKEN_FILE, which the running app
then reuses (and auto-refreshes) for every Drive API call.
"""

import os

from django.core.management.base import BaseCommand, CommandError
from google_auth_oauthlib.flow import InstalledAppFlow

from photos.drive_service import SCOPES, save_credentials


class Command(BaseCommand):
    help = "Run the one-time Google Drive OAuth consent flow and save the token."

    def handle(self, *args, **options):
        client_secret_file = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "").strip()
        token_file = os.environ.get("GOOGLE_OAUTH_TOKEN_FILE", "").strip()

        if not client_secret_file or not os.path.exists(client_secret_file):
            raise CommandError(
                "GOOGLE_OAUTH_CLIENT_SECRET_FILE is not set or the file doesn't exist. "
                "Download it from Google Cloud Console (OAuth client, Desktop app type)."
            )
        if not token_file:
            raise CommandError("GOOGLE_OAUTH_TOKEN_FILE is not set.")

        flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
        creds = flow.run_local_server(port=0)
        save_credentials(creds)

        self.stdout.write(self.style.SUCCESS(f"Saved Google Drive token to {token_file}"))
