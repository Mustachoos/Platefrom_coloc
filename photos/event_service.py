"""Multi-event orchestration: connecting an event to its Drive folder,
backing up local photos, and switching which event is active.

Exactly one Event is active at a time (Event.get_active()) — that's the one
the public pages (upload, tv, gallery) read and write. Local disk/DB storage
only ever holds the active event's photos: switching clears the outgoing
event's local copies (safe, since the caller only calls this once every one
of them is confirmed backed up to Drive) and downloads the incoming event's
photos fresh from its Drive folder. Drive is the durable store; local
storage is a working cache of "whichever event is live right now".
"""

import logging
import re

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.files.base import ContentFile

from . import drive_service
from .models import Event, Photo

logger = logging.getLogger(__name__)

_FILENAME_RE = re.compile(r"^(?P<user>.+)_\d{2}h\d{2}_[0-9a-f]{8}(?P<ext>\.[^.]*)$")


def _guess_username(filename):
    """Recover the uploader's slugified pseudo from our own upload filename
    pattern (<pseudo>_<HHhMM>_<uuid8>.<ext>), used when restoring photos that
    only exist on Drive."""
    match = _FILENAME_RE.match(filename)
    return match.group("user").replace("-", " ") if match else "unknown"


def ensure_drive_folder(event):
    """Make sure `event` has a connected Drive folder, creating/finding one
    by its name under the root folder if it doesn't have one yet.
    Returns (ok, message)."""
    if event.drive_folder_id:
        return True, event.drive_folder_url
    try:
        folder_id, folder_url = drive_service.get_or_create_event_folder(event.name)
    except drive_service.DriveError as exc:
        return False, str(exc)
    Event.objects.filter(pk=event.pk).update(drive_folder_id=folder_id, drive_folder_url=folder_url)
    event.drive_folder_id = folder_id
    event.drive_folder_url = folder_url
    return True, folder_url


def recreate_drive_folder(event):
    """The event's current Drive folder is gone (deleted/trashed/unreachable):
    create a brand new one under the root folder with the same name, mark
    every local photo as no-longer-backed-up (their old Drive copies are
    gone too), and immediately re-upload them into the new folder.
    Returns (ok, message, uploaded_count, failed_count)."""
    try:
        folder_id, folder_url = drive_service.get_or_create_event_folder(event.name)
    except drive_service.DriveError as exc:
        return False, str(exc), 0, 0
    Event.objects.filter(pk=event.pk).update(drive_folder_id=folder_id, drive_folder_url=folder_url)
    event.drive_folder_id = folder_id
    event.drive_folder_url = folder_url
    invalidate_drive_backups(event)
    uploaded, failed = backup_pending_photos(event)
    return True, folder_url, uploaded, failed


def relink_drive_folder(event, folder_id_or_url):
    """Point event at a different, existing Drive folder (pasted ID or
    Drive URL). Local photos' old drive_file_id no longer means anything for
    this folder, so they're marked no-longer-backed-up and immediately
    re-uploaded into it. Returns (ok, message, uploaded_count, failed_count)."""
    event.drive_folder_id = folder_id_or_url
    Event.objects.filter(pk=event.pk).update(drive_folder_id=folder_id_or_url)
    ok, message = drive_service.connect_existing_folder(event)
    if not ok:
        return False, message, 0, 0
    invalidate_drive_backups(event)
    uploaded, failed = backup_pending_photos(event)
    return True, message, uploaded, failed


def invalidate_drive_backups(event):
    """Forget any drive_file_id on event's local photos — used whenever the
    Drive folder they pointed to is gone or has been swapped for a different
    one, so unbacked_up_photo_count/backup_pending_photos correctly treat
    them as needing to be (re-)uploaded."""
    event.photos.exclude(drive_file_id="").update(drive_file_id="")


def drive_photo_count(event):
    """Photo count as Drive sees it — the source of truth now that local
    storage only ever holds the active event's photos. Returns None if the
    folder can't be reached (dashboard shows that as unknown rather than 0)."""
    if not event.drive_folder_id:
        return 0
    try:
        return len(drive_service.list_folder_files(event.drive_folder_id))
    except drive_service.DriveError as exc:
        logger.warning("Could not count Drive photos for event '%s': %s", event.name, exc)
        return None


def unbacked_up_photo_count(event):
    return event.photos.filter(drive_file_id="").count()


def backup_pending_photos(event):
    """Upload every local photo of `event` that isn't on Drive yet.
    Returns (uploaded_count, failed_count)."""
    if not event.drive_folder_id:
        return 0, event.photos.filter(drive_file_id="").count()
    uploaded, failed = 0, 0
    for photo in event.photos.filter(drive_file_id=""):
        try:
            file_id = drive_service.upload_photo(event.drive_folder_id, photo.image.path, photo.filename)
        except drive_service.DriveError as exc:
            failed += 1
            logger.warning("Could not back up photo %s: %s", photo.id, exc)
        else:
            photo.drive_file_id = file_id
            photo.save(update_fields=["drive_file_id"])
            uploaded += 1
    return uploaded, failed


def sync_photos_from_drive(event):
    """Download any file present in event's Drive folder but missing
    locally, recreating a Photo row for it. Returns (downloaded, failed)."""
    if not event.drive_folder_id:
        return 0, 0
    known_ids = set(event.photos.exclude(drive_file_id="").values_list("drive_file_id", flat=True))
    try:
        drive_files = drive_service.list_folder_files(event.drive_folder_id)
    except drive_service.DriveError as exc:
        logger.warning("Could not list Drive folder for event '%s': %s", event.name, exc)
        return 0, 0

    downloaded, failed = 0, 0
    for f in drive_files:
        if f["id"] in known_ids:
            continue
        try:
            content = drive_service.download_file(f["id"])
        except drive_service.DriveError as exc:
            failed += 1
            logger.warning("Could not restore '%s': %s", f["name"], exc)
            continue
        photo = Photo(event=event, username=_guess_username(f["name"]), drive_file_id=f["id"])
        photo.image.save(f["name"], ContentFile(content), save=True)
        downloaded += 1
    return downloaded, failed


def _clear_local_photos(event):
    """Delete every local Photo (row + file) for `event`, without touching
    its Drive copies. Only call this once unbacked_up_photo_count(event) is
    0 — every one of them is already safe on Drive."""
    for photo in event.photos.all():
        photo._local_cache_clear = True
        photo.delete()


def switch_active_event(event):
    """Clear the outgoing active event's local photos (they're already on
    Drive), download `event`'s photos fresh from its Drive folder, make it
    the active event, and tell connected TV screens to refresh. Returns
    (downloaded_count, failed_count) from the Drive download step."""
    previous = Event.get_active()
    if previous and previous.pk != event.pk:
        _clear_local_photos(previous)

    downloaded, failed = sync_photos_from_drive(event)
    Event.objects.exclude(pk=event.pk).update(is_active=False)
    Event.objects.filter(pk=event.pk).update(is_active=True)

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("tv_updates", {"type": "event.switched"})
    return downloaded, failed
