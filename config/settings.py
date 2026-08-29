import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    import platformdirs

    APP_DATA_DIR = Path(platformdirs.user_data_dir("PartyBooth", appauthor=False))
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
else:
    APP_DATA_DIR = BASE_DIR

if IS_FROZEN:
    _secret_key_file = APP_DATA_DIR / "secret_key.txt"
    if _secret_key_file.exists():
        SECRET_KEY = _secret_key_file.read_text().strip()
    else:
        from django.core.management.utils import get_random_secret_key

        SECRET_KEY = get_random_secret_key()
        _secret_key_file.write_text(SECRET_KEY)
else:
    SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-secret-key-flatshare-photos")

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "photos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "photos.middleware.FirstRunRedirectMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

_db_engine = os.environ.get("DJANGO_DB_ENGINE", "sqlite" if IS_FROZEN else "postgresql")

if _db_engine == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": APP_DATA_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DJANGO_DB_NAME", "coloc_photos"),
            "USER": os.environ.get("DJANGO_DB_USER", "coloc"),
            "PASSWORD": os.environ.get("DJANGO_DB_PASSWORD", "coloc"),
            "HOST": os.environ.get("DJANGO_DB_HOST", "db"),
            "PORT": os.environ.get("DJANGO_DB_PORT", "5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = APP_DATA_DIR / "media" if IS_FROZEN else BASE_DIR / "data" / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
