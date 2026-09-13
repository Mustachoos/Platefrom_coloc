from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("photos.urls")),
]

# Always served by Django itself, regardless of DEBUG — this app has no
# separate web server/reverse proxy in front of it (Docker or the packaged
# .exe/.dmg), so it's the only thing that ever serves guest-uploaded photos
# and whiteboard images. django.conf.urls.static.static() (the usual
# shortcut) deliberately no-ops when DEBUG is False, which would silently
# break every photo/whiteboard image once DEBUG=False in the packaged
# build (see settings.py) — wired directly here instead.
urlpatterns += [
    path(f"{settings.MEDIA_URL.lstrip('/')}<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
]
