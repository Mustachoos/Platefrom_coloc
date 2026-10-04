"""PyInstaller entry point: boots Django against a per-user app-data
directory (see config/settings.py's IS_FROZEN branch), runs migrations,
and serves the app via Daphne directly — not `runserver`, whose
autoreloader re-execs sys.argv[0] and loops when that argv is a frozen
exe rather than `python manage.py`.

The build is windowed (no console): Daphne runs on a background thread and a
system-tray / menu-bar icon owns the main thread (macOS requires that) with
Open / guest address / Quit. Output goes to a log file in the app-data
folder, and fatal startup errors surface as a native dialog."""

import os
import sys
import threading
import traceback
import webbrowser

# DJANGO_SETTINGS_MODULE is a string Django resolves dynamically via
# importlib — PyInstaller's static import analysis can't see that, so
# `config` (and asgi, referenced the same way further down) is imported
# directly here purely so PyInstaller's Analysis phase bundles it.
import config.settings  # noqa: F401
import config.asgi  # noqa: F401

import launcher_support as support

APP_NAME = "PartyBooth"

FIRST_RUN_MESSAGE = (
    "PartyBooth is starting.\n\n"
    "Your computer may now ask whether to allow PartyBooth to accept incoming network "
    "connections (firewall prompt). Please click Allow: guests' phones need it to reach "
    "the app over your Wi-Fi.\n\n"
    "PartyBooth runs from the icon in your system tray / menu bar - use it to open the app "
    "or quit."
)


def _resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def _prepare_environment():
    from django.conf import settings

    creds_dir = settings.APP_DATA_DIR / "credentials"
    (settings.APP_DATA_DIR / "media").mkdir(parents=True, exist_ok=True)
    creds_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("GOOGLE_OAUTH_CLIENT_SECRET_FILE", str(creds_dir / "client_secret.json"))
    os.environ.setdefault("GOOGLE_OAUTH_TOKEN_FILE", str(creds_dir / "token.json"))
    os.environ.setdefault("GMAIL_SEND_TOKEN_FILE", str(creds_dir / "gmail_send_token.json"))
    return settings.APP_DATA_DIR


def _sync_stored_port(port):
    """The admin page stores the verified host as "ip:port". If this launch
    had to use a different port than last time, the stored one would send
    guests to a dead address, so rewrite just its port part."""
    from photos.models import SiteSettings

    site_settings = SiteSettings.get_solo()
    updated = support.with_port(site_settings.server_host, port)
    if updated != site_settings.server_host:
        site_settings.server_host = updated
        site_settings.save(update_fields=["server_host"])


def _serve(port, ready, failure):
    """Daphne on a worker thread. Signal handlers can only be installed from
    the main thread, hence signal_handlers=False."""
    try:
        from daphne.server import Server

        from config.asgi import application

        Server(
            application=application,
            endpoints=[f"tcp:port={port}:interface=0.0.0.0"],
            signal_handlers=False,
            ready_callable=ready.set,
        ).run()
    except BaseException:
        failure.append(traceback.format_exc())
        ready.set()


def _stop_server():
    from twisted.internet import reactor

    if reactor.running:
        reactor.callFromThread(reactor.stop)


def _check_update(update, icon):
    current = support.read_current_version(_resource_path("version.txt"))
    found = support.check_for_update(current) if current else None
    if found:
        update.update(tag=found[0], url=found[1])
        print(f"Update available: {found[0]} ({found[1]})", flush=True)
        icon.update_menu()


def _run_tray(local_url, guest_url, update):
    """Blocks on the main thread until the user picks Quit. Raises if no tray
    is available on this system (e.g. a Linux desktop without an indicator)."""
    import pystray
    from PIL import Image

    def open_app(icon=None, item=None):
        webbrowser.open(local_url)

    def quit_app(icon, item):
        icon.stop()

    def open_update(icon, item):
        webbrowser.open(update["url"])

    guest_label = f"Guests join at: {guest_url}" if guest_url else "Guests: not connected to a network"
    menu = pystray.Menu(
        pystray.MenuItem("Open PartyBooth", open_app, default=True),
        pystray.MenuItem(guest_label, None, enabled=False),
        pystray.MenuItem(
            lambda item: f"New version available: {update['tag']} - download",
            open_update,
            visible=lambda item: bool(update),
        ),
        pystray.MenuItem("Quit", quit_app),
    )
    icon = pystray.Icon(APP_NAME, Image.open(_resource_path("app-icon.png")), APP_NAME, menu)
    # Checked in the background so a slow/offline network never delays
    # startup; the menu item above just appears once an answer is in.
    threading.Thread(target=_check_update, args=(update, icon), daemon=True).start()
    icon.run()


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    app_data_dir = _prepare_environment()
    if getattr(sys, "frozen", False):
        support.redirect_output_to_log(str(app_data_dir / "logs" / "partybooth.log"))

    from django.core.management import call_command

    call_command("migrate", interactive=False, verbosity=1)

    port = support.pick_port()
    if port != support.PREFERRED_PORT:
        print(f"Port {support.PREFERRED_PORT} is busy, using {port} instead.", flush=True)
    _sync_stored_port(port)

    ready = threading.Event()
    failure = []
    threading.Thread(target=_serve, args=(port, ready, failure), daemon=True).start()
    ready.wait(timeout=30)
    if failure:
        raise RuntimeError(f"The server could not start:\n{failure[0]}")

    local_url = f"http://127.0.0.1:{port}/"
    ip = support.lan_ip()
    guest_url = f"http://{ip}:{port}/" if ip else None
    print(f"PartyBooth is running at {local_url} (guests: {guest_url or 'no network'})", flush=True)

    first_run_marker = app_data_dir / ".first_run_done"
    if not first_run_marker.exists():
        first_run_marker.touch()
        threading.Thread(target=support.show_dialog, args=(APP_NAME, FIRST_RUN_MESSAGE), daemon=True).start()

    webbrowser.open(local_url)

    try:
        _run_tray(local_url, guest_url, {})
    except Exception:
        # No tray on this system: keep serving rather than exit, the log says why.
        print("System tray unavailable, running without it:\n" + traceback.format_exc(), flush=True)
        support.show_dialog(
            APP_NAME,
            f"PartyBooth is running at {local_url}\n\nThere is no tray icon on this system; "
            "end the PartyBooth process to quit.",
        )
        threading.Event().wait()
    finally:
        _stop_server()
    print("PartyBooth stopped.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except BaseException:
        details = traceback.format_exc()
        print(details, file=sys.stderr, flush=True)
        support.show_dialog(
            APP_NAME,
            "PartyBooth could not start.\n\n" + details.strip().splitlines()[-1] + "\n\nDetails are in "
            "the logs folder inside the PartyBooth data folder.",
        )
        sys.exit(1)
