"""Stdlib-only helpers for packaging/launcher.py: free-port selection, LAN
address detection, native message dialogs, and stdout/stderr redirection.

Kept free of Django/Twisted imports so it can be unit-tested (and imported
before Django is set up) without any of the app's dependencies."""

import json
import os
import re
import socket
import subprocess
import sys
import urllib.request

PREFERRED_PORT = 8000
PORT_SEARCH_LIMIT = 10  # tries 8000..8009, then lets the OS pick


def port_is_free(port, interface="0.0.0.0"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((interface, port))
        except OSError:
            return False
    return True


def pick_port(preferred=PREFERRED_PORT, limit=PORT_SEARCH_LIMIT):
    """First free port from `preferred` upward; falls back to an OS-assigned
    one so startup never fails just because 8000 is taken."""
    for port in range(preferred, preferred + limit):
        if port_is_free(port):
            return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 0))
        return s.getsockname()[1]


def lan_ip():
    """The address other devices on the Wi-Fi/LAN would use to reach this
    machine, or None when it isn't on a network. Connecting a UDP socket sends
    no packet — it only makes the OS choose the outgoing interface."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except OSError:
            return None
    return None if ip.startswith("127.") else ip


def with_port(host, port):
    """`host` ("192.168.1.13:8000", "192.168.1.13" or "") with its port
    replaced by `port`; blank stays blank."""
    if not host:
        return host
    return f"{host.split(':', 1)[0]}:{port}"


def show_dialog(title, message):
    """Native message box. Best effort: with no console to print to, a failure
    here must never take the app down, so any error is swallowed."""
    try:
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
        elif sys.platform == "darwin":
            script = 'display dialog {} with title {} buttons {{"OK"}} default button "OK"'.format(
                _applescript_quote(message), _applescript_quote(title)
            )
            subprocess.run(["osascript", "-e", script], check=False, timeout=600)
        else:
            subprocess.run(
                ["zenity", "--info", "--title", title, "--text", message, "--no-markup"],
                check=False,
                timeout=600,
            )
    except Exception:
        pass


def _applescript_quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def redirect_output_to_log(log_path):
    """A windowed build has no console (sys.stdout/stderr are None on Windows),
    so every print/traceback goes to a log file the user can find instead."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    stream = open(log_path, "a", buffering=1, encoding="utf-8")
    sys.stdout = stream
    sys.stderr = stream
    return stream


RELEASES_API = "https://api.github.com/repos/PablArb/Platefrom_coloc/releases/latest"


def parse_version(text):
    """"v0.4.1" / "0.4.1" -> (0, 4, 1); None for anything that isn't a plain
    numeric dotted version (e.g. "0.0.0-dev", a branch name, garbage)."""
    match = re.fullmatch(r"v?(\d+(?:\.\d+)*)", (text or "").strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def is_newer(latest, current):
    latest_v, current_v = parse_version(latest), parse_version(current)
    return latest_v is not None and current_v is not None and latest_v > current_v


def read_current_version(path):
    """Version baked in by CI (packaging/version.txt, written from the git
    tag); None for a dev run or a manual workflow build, where the check is
    skipped."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
    except OSError:
        return None
    return text if parse_version(text) else None


def check_for_update(current, api_url=RELEASES_API, timeout=5):
    """(tag, page_url) of a newer published release, else None. Never raises:
    offline, rate-limited, private repo (404) and malformed answers all just
    mean "no update to announce"."""
    if parse_version(current) is None:
        return None
    try:
        request = urllib.request.Request(
            api_url, headers={"Accept": "application/vnd.github+json", "User-Agent": "PartyBooth"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
        tag, url = data["tag_name"], data["html_url"]
    except Exception:
        return None
    return (tag, url) if is_newer(tag, current) else None
