# PyInstaller spec for PartyBooth. Build with:
#   pyinstaller packaging/launcher.spec
# from the repo root, after `python manage.py collectstatic --noinput`
# (this spec bundles the collectstatic OUTPUT, not the raw static/ source
# tree — see the `staticfiles` entry below).
#
# Icons under packaging/{windows,macos,linux}/app-icon.* are generated from
# Icon/redPlaneIcon.png (upscaled from its native 64x64) — swap the source
# and regenerate, or replace the files directly, nothing else needs to change.

import os
import sys

import django
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

REPO_ROOT = os.path.dirname(os.path.abspath(SPECPATH))
DJANGO_DIR = os.path.dirname(django.__file__)

# collect_submodules() below imports `photos`/`config` immediately, at
# spec-parse time, before Analysis()'s own `pathex` takes effect.
sys.path.insert(0, REPO_ROOT)

datas = [
    (os.path.join(REPO_ROOT, "staticfiles"), "staticfiles"),
    # The raw static/ source tree, separate from the collectstatic OUTPUT
    # above: django.contrib.staticfiles.finders.find() (used directly by
    # photos/templatetags/icons.py to inline SVGs) searches STATICFILES_DIRS
    # — the source directories — not STATIC_ROOT, so both have to ship.
    (os.path.join(REPO_ROOT, "static"), "static"),
    (os.path.join(REPO_ROOT, "photos", "templates"), "photos/templates"),
    (os.path.join(DJANGO_DIR, "contrib", "admin", "templates"), "django/contrib/admin/templates"),
    (os.path.join(DJANGO_DIR, "contrib", "admin", "static"), "django/contrib/admin/static"),
    (os.path.join(DJANGO_DIR, "contrib", "auth", "templates"), "django/contrib/auth/templates"),
]

# Django resolves a lot of modules dynamically from strings (MIDDLEWARE
# entries, ROOT_URLCONF, INSTALLED_APPS, include(), DB backend ENGINE),
# which PyInstaller's static import analysis can't trace. Rather than
# hidden-importing modules one at a time as they're discovered at runtime,
# pull in every submodule of this project's own two packages wholesale —
# they're small and entirely our own code, so there's no size/risk cost
# to being exhaustive here. The postgresql backend is deliberately NOT
# listed — see requirements-frozen.txt.
hiddenimports = (
    collect_submodules("photos")
    + collect_submodules("config")
    + collect_submodules("whitenoise")
    + collect_submodules("daphne")
    + collect_submodules("channels")
    + [
        "django.contrib.admin.apps",
        "django.contrib.auth.apps",
        "django.contrib.contenttypes.apps",
        "django.contrib.sessions.apps",
        "django.contrib.messages.apps",
        "django.contrib.staticfiles.apps",
        "django.db.backends.sqlite3.base",
    ]
)

a = Analysis(
    [os.path.join(REPO_ROOT, "packaging", "launcher.py")],
    pathex=[REPO_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # autobahn.nvx is an optional CFFI-based native accelerator for
    # WebSocket UTF-8/XOR-mask handling; its Python wrapper reads a co-located
    # .c source file at import time via a hardcoded path that doesn't survive
    # freezing. Excluding it makes autobahn cleanly fall back to its
    # pure-Python implementation, which it already supports.
    excludes=["psycopg2", "autobahn.nvx", "_nvx_utf8validator", "_nvx_xormasker"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="launcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX-compressing compiled C extensions (Pillow's _imaging.pyd in
    # particular) is a well-documented cause of "cannot import name
    # '_imaging' from PIL" — the file survives but its exported symbols
    # break. Not worth the size savings for a one-time download.
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=os.path.join(REPO_ROOT, "packaging", "windows", "app-icon.ico") if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="launcher",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="PartyBooth.app",
        icon=os.path.join(REPO_ROOT, "packaging", "macos", "app-icon.icns"),
        bundle_identifier="com.partybooth.app",
        info_plist={"NSHighResolutionCapable": True},
    )
