"""PyInstaller entry point: boots Django against a per-user app-data
directory (see config/settings.py's IS_FROZEN branch), runs migrations,
and serves the app via Daphne directly — not `runserver`, whose
autoreloader re-execs sys.argv[0] and loops when that argv is a frozen
exe rather than `python manage.py`."""

import os
import sys
import threading
import webbrowser

# DJANGO_SETTINGS_MODULE is a string Django resolves dynamically via
# importlib — PyInstaller's static import analysis can't see that, so
# `config` (and asgi, referenced the same way further down) is imported
# directly here purely so PyInstaller's Analysis phase bundles it.
import config.settings  # noqa: F401
import config.asgi  # noqa: F401


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    from django.conf import settings

    creds_dir = settings.APP_DATA_DIR / "credentials"
    (settings.APP_DATA_DIR / "media").mkdir(parents=True, exist_ok=True)
    creds_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("GOOGLE_OAUTH_CLIENT_SECRET_FILE", str(creds_dir / "client_secret.json"))
    os.environ.setdefault("GOOGLE_OAUTH_TOKEN_FILE", str(creds_dir / "token.json"))
    os.environ.setdefault("GMAIL_SEND_TOKEN_FILE", str(creds_dir / "gmail_send_token.json"))

    from django.core.management import call_command

    call_command("migrate", interactive=False, verbosity=1)

    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:8000/")).start()

    from daphne.server import Server

    from config.asgi import application

    print("PartyBooth is running — closing this window stops the server.", flush=True)
    try:
        Server(application=application, endpoints=["tcp:port=8000:interface=0.0.0.0"]).run()
    except KeyboardInterrupt:
        print("PartyBooth stopped.", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
