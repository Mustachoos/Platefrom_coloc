import io
import logging
import os

import qrcode
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from . import drive_service, event_service
from .forms import PseudoForm, ShareDriveForm
from .models import Event, Photo, SlideshowSettings, UserIdentity, Like

logger = logging.getLogger(__name__)


def _drive_fix_summary(message, uploaded, failed):
    summary = f"{message}."
    if uploaded:
        summary += f" {uploaded} photo(s) re-uploaded."
    if failed:
        summary += f" {failed} failed to upload."
    return summary


def _dashboard_redirect(tab="events"):
    response = redirect("dashboard")
    if tab and tab != "events":
        response["Location"] += f"?tab={tab}"
    return response


def _photo_payload(photo, user=None):
    liked = False
    if user is not None:
        liked = Like.objects.filter(photo=photo, user=user).exists()
    return {
        "id": photo.id,
        "url": photo.image.url,
        "username": photo.username,
        "uploaded_at": photo.uploaded_at.isoformat(),
        "likes_count": photo.likes_count,
        "liked": liked,
    }


def _get_user_identity(request):
    session_key = request.session.session_key
    if not session_key:
        return None
    active_event = Event.get_active()
    if not active_event:
        return None
    return UserIdentity.objects.filter(session_key=session_key, event=active_event).first()


def choose_pseudo(request):
    active_event = Event.get_active()
    if active_event is None:
        return render(request, "photos/no_active_event.html")

    existing = _get_user_identity(request)
    if existing:
        request.session["pseudo"] = existing.pseudo
        return redirect("upload")

    if request.method == "POST":
        form = PseudoForm(request.POST)
        if form.is_valid():
            pseudo = form.cleaned_data["pseudo"].strip()
            if UserIdentity.objects.filter(event=active_event, pseudo__iexact=pseudo).exists():
                form.add_error("pseudo", "That name is already taken, please choose another one.")
            else:
                if not request.session.session_key:
                    request.session.create()
                try:
                    UserIdentity.objects.create(
                        event=active_event, pseudo=pseudo, session_key=request.session.session_key
                    )
                except IntegrityError:
                    form.add_error("pseudo", "That name is already taken, please choose another one.")
                else:
                    request.session["pseudo"] = pseudo
                    return redirect("share-drive")
    else:
        form = PseudoForm()
    return render(request, "photos/choose_pseudo.html", {"form": form})


def share_drive_view(request):
    user = _get_user_identity(request)
    if not user:
        return redirect("choose-pseudo")
    active_event = user.event
    pseudo = user.pseudo

    if request.method == "POST":
        if "skip" in request.POST:
            return redirect("upload")
        form = ShareDriveForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip()
            if email:
                try:
                    if active_event.drive_sharing_enabled:
                        permission_id = drive_service.share_folder_with_email(
                            active_event.drive_folder_id, email
                        )
                    else:
                        # Sharing isn't turned on yet: just prove this email
                        # *could* be granted access, without leaving real access behind.
                        drive_service.test_share(active_event.drive_folder_id, email)
                        permission_id = ""
                except drive_service.DriveError as exc:
                    logger.warning("Could not validate Drive sharing for %s: %s", email, exc)
                    messages.error(request, "Could not share the Drive folder, please try again.")
                    return render(request, "photos/share_drive.html", {"form": form, "pseudo": pseudo})
                else:
                    user.email = email
                    user.drive_shared = bool(permission_id)
                    user.drive_permission_id = permission_id
                    user.save(update_fields=["email", "drive_shared", "drive_permission_id"])
            return redirect("upload")
    else:
        form = ShareDriveForm()
    return render(request, "photos/share_drive.html", {"form": form, "pseudo": pseudo})


def upload_view(request):
    active_event = Event.get_active()
    if active_event is None:
        return render(request, "photos/no_active_event.html")
    user = _get_user_identity(request)
    if not user:
        return redirect("choose-pseudo")
    pseudo = user.pseudo

    if request.method == "POST":
        images = request.FILES.getlist("images")
        if images:
            channel_layer = get_channel_layer()
            for image in images:
                photo = Photo.objects.create(event=active_event, username=pseudo, image=image)
                async_to_sync(channel_layer.group_send)(
                    "tv_updates",
                    {"type": "photo.uploaded", "photo": _photo_payload(photo)},
                )
                if active_event.drive_folder_id:
                    try:
                        file_id = drive_service.upload_photo(
                            active_event.drive_folder_id, photo.image.path, photo.filename
                        )
                    except drive_service.DriveError as exc:
                        logger.warning("Could not upload photo %s to Drive: %s", photo.id, exc)
                    else:
                        photo.drive_file_id = file_id
                        photo.save(update_fields=["drive_file_id"])
            return redirect(f"{reverse('upload')}?uploaded=1")
        messages.error(request, "Please choose at least one photo.")
    just_uploaded = request.GET.get("uploaded") == "1"
    return render(request, "photos/upload.html", {"pseudo": pseudo, "just_uploaded": just_uploaded})


def tv_view(request):
    return render(request, "photos/tv.html")


def my_photos_view(request):
    user = _get_user_identity(request)
    if not user:
        return redirect("choose-pseudo")
    photos = Photo.objects.filter(event=user.event, username=user.pseudo).order_by("uploaded_at")
    return render(request, "photos/my_photos.html", {"pseudo": user.pseudo, "photos": photos})


def delete_own_photo(request, photo_id):
    user = _get_user_identity(request)
    if not user:
        return redirect("choose-pseudo")
    if request.method == "POST":
        # event=user.event, username=user.pseudo ensures a guest can only
        # ever delete their own photos from their own event.
        photo = get_object_or_404(Photo, id=photo_id, event=user.event, username=user.pseudo)
        photo.delete()
        messages.success(request, "Photo deleted.")
    return redirect("my-photos")


def photo_list_api(request):
    user = _get_user_identity(request)
    active_event = Event.get_active()
    if not active_event:
        return JsonResponse([], safe=False)
    photos = Photo.objects.filter(event=active_event).order_by("uploaded_at")
    return JsonResponse([_photo_payload(photo, user=user) for photo in photos], safe=False)


def like_toggle_api(request, photo_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    active_event = Event.get_active()
    if not active_event or not active_event.likes_enabled:
        return JsonResponse({"error": "likes are disabled"}, status=403)
    user = _get_user_identity(request)
    if not user:
        return JsonResponse({"error": "identity required"}, status=403)
    photo = get_object_or_404(Photo, pk=photo_id, event=active_event)
    like, created = Like.objects.get_or_create(photo=photo, user=user)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    # broadcast updated likes
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "tv_updates",
        {"type": "photo.liked", "photo_id": photo.id, "likes_count": photo.likes_count},
    )
    return JsonResponse({"photo_id": photo.id, "likes_count": photo.likes_count, "liked": liked})


def gallery_view(request):
    user = _get_user_identity(request)
    active_event = Event.get_active()
    photos_qs = Photo.objects.filter(event=active_event).order_by("-uploaded_at") if active_event else Photo.objects.none()
    payloads = [_photo_payload(photo, user=user) for photo in photos_qs]
    likes_enabled = active_event.likes_enabled if active_event else True
    return render(request, "photos/gallery.html", {"photos": payloads, "likes_enabled": likes_enabled})


def slideshow_settings_api(request):
    slideshow = SlideshowSettings.get_solo()
    active_event = Event.get_active()
    likes_enabled = active_event.likes_enabled if active_event else True
    return JsonResponse({"interval_seconds": slideshow.interval_seconds, "likes_enabled": likes_enabled})


def upload_qr_code(request):
    forced_ip = os.environ.get("QR_HOST_IP", "").strip()
    if forced_ip:
        scheme = "https" if request.is_secure() else "http"
        raw_host = request.get_host()
        if raw_host.count(":") == 1 and not raw_host.startswith("["):
            _, port = raw_host.rsplit(":", 1)
        else:
            port = request.get_port()
        default_port = "443" if scheme == "https" else "80"
        host = forced_ip if str(port) == default_port else f"{forced_ip}:{port}"
        upload_url = f"{scheme}://{host}{reverse('upload')}"
    else:
        upload_url = request.build_absolute_uri(reverse("upload"))
    image = qrcode.make(upload_url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


@staff_member_required
def dashboard_view(request):
    active_event = Event.get_active()

    if request.method == "POST":
        if active_event is None:
            messages.error(request, "No active event yet — create one below first.")
            return _dashboard_redirect()

        if "recreate_drive_folder" in request.POST:
            ok, message, uploaded, failed = event_service.recreate_drive_folder(active_event)
            if ok:
                messages.success(
                    request,
                    _drive_fix_summary(f"New Drive folder created for '{active_event.name}': {message}", uploaded, failed),
                )
            else:
                messages.error(request, f"Could not create a new Drive folder: {message}")
            return _dashboard_redirect(tab="features")
        if "toggle_drive_sharing" in request.POST:
            if not active_event.drive_folder_id:
                messages.error(request, "Connect a Drive folder before sharing it.")
            else:
                active_event.drive_sharing_enabled = not active_event.drive_sharing_enabled
                active_event.save(update_fields=["drive_sharing_enabled"])
                if active_event.drive_sharing_enabled:
                    granted, failed = 0, 0
                    for guest in active_event.identities.exclude(email=""):
                        if guest.drive_shared and guest.drive_permission_id:
                            continue
                        try:
                            permission_id = drive_service.share_folder_with_email(
                                active_event.drive_folder_id, guest.email
                            )
                        except drive_service.DriveError as exc:
                            failed += 1
                            logger.warning("Could not share Drive with %s: %s", guest.email, exc)
                        else:
                            guest.drive_shared = True
                            guest.drive_permission_id = permission_id
                            guest.save(update_fields=["drive_shared", "drive_permission_id"])
                            granted += 1
                    summary = f"Drive sharing on: {granted} guest(s) granted access"
                    if failed:
                        summary += f", {failed} failed"
                    messages.success(request, summary)
                else:
                    revoked, failed = 0, 0
                    for guest in active_event.identities.filter(drive_shared=True):
                        if guest.drive_permission_id:
                            try:
                                drive_service.revoke_folder_permission(
                                    active_event.drive_folder_id, guest.drive_permission_id
                                )
                            except drive_service.DriveError as exc:
                                failed += 1
                                logger.warning("Could not revoke Drive access for %s: %s", guest.email, exc)
                                continue
                        guest.drive_shared = False
                        guest.drive_permission_id = ""
                        guest.save(update_fields=["drive_shared", "drive_permission_id"])
                        revoked += 1
                    summary = f"Drive sharing off: access revoked for {revoked} guest(s)"
                    if failed:
                        summary += f", {failed} failed"
                    messages.success(request, summary)
        elif "toggle_likes" in request.POST:
            active_event.likes_enabled = not active_event.likes_enabled
            active_event.save(update_fields=["likes_enabled"])
            messages.success(request, "Likes " + ("enabled." if active_event.likes_enabled else "disabled."))
        return _dashboard_redirect(request, default_tab="features")

    events = list(Event.objects.all())
    for event in events:
        # Live check every time — a stored drive_folder_id doesn't guarantee
        # the folder is still actually there.
        if not event.drive_folder_id:
            event.drive_status = "disconnected"
        elif drive_service.folder_exists(event.drive_folder_id):
            event.drive_status = "ok"
            event.drive_count = event_service.drive_photo_count(event)
        else:
            event.drive_status = "broken"
    if active_event:
        active_event = next(e for e in events if e.pk == active_event.pk)  # reuse the drive_status-annotated instance
        identities = active_event.identities.order_by("-created_at")
        photos = active_event.photos.order_by("-uploaded_at")
    else:
        identities = UserIdentity.objects.none()
        photos = Photo.objects.none()
    guests_with_email = identities.exclude(email="").count()
    guests_shared = identities.filter(drive_shared=True).count()
    active_tab = request.GET.get("tab", "events")
    return render(
        request,
        "photos/dashboard.html",
        {
            "events": events,
            "active_event": active_event,
            "identities": identities,
            "photos": photos,
            "guests_with_email": guests_with_email,
            "guests_shared": guests_shared,
            "active_tab": active_tab,
        },
    )


@staff_member_required
def dashboard_delete_photo(request, photo_id):
    if request.method == "POST":
        photo = get_object_or_404(Photo, id=photo_id)
        photo.delete()
        messages.success(request, "Photo deleted.")
    return _dashboard_redirect(tab="photos")


@staff_member_required
def create_event_view(request):
    if request.method != "POST":
        return redirect("dashboard")
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Give the event a name.")
        return redirect("dashboard")

    event = Event.objects.filter(name=name).first()
    if event is None:
        event = Event.objects.create(name=name)
    if not event.drive_folder_id:
        ok, message = event_service.ensure_drive_folder(event)
        if not ok:
            messages.error(
                request,
                f"Event '{name}' saved, but its Drive folder could not be connected: {message}. "
                "Fix it from the events list, then switch to it.",
            )
            return redirect("dashboard")
    return redirect("event-switch", event_id=event.id)


@staff_member_required
def event_switch_view(request, event_id):
    target = get_object_or_404(Event, id=event_id)
    active = Event.get_active()

    if target.is_active:
        messages.info(request, f"'{target.name}' is already the active event.")
        return redirect("dashboard")

    # Live, uncached check every time this page is hit — a cached
    # drive_folder_id can't tell us the folder wasn't deleted/unshared since
    # the last time we looked.
    active_drive_ok = drive_service.folder_exists(active.drive_folder_id) if active else True
    target_drive_ok = drive_service.folder_exists(target.drive_folder_id)
    broken = active if (active and not active_drive_ok) else (target if not target_drive_ok else None)

    if request.method == "POST":
        if "recreate_folder" in request.POST:
            ev = get_object_or_404(Event, id=request.POST.get("broken_event_id"))
            ok, message, uploaded, failed = event_service.recreate_drive_folder(ev)
            if ok:
                messages.success(
                    request,
                    _drive_fix_summary(f"New Drive folder created for '{ev.name}': {message}", uploaded, failed),
                )
            else:
                messages.error(request, f"Could not create a new Drive folder: {message}")
            return redirect("event-switch", event_id=target.id)

        if "relink_folder" in request.POST:
            ev = get_object_or_404(Event, id=request.POST.get("broken_event_id"))
            link = request.POST.get("drive_folder_id_or_url", "").strip()
            if not link:
                messages.error(request, "Paste a Drive folder ID or URL.")
                return redirect("event-switch", event_id=target.id)
            ok, message, uploaded, failed = event_service.relink_drive_folder(ev, link)
            if ok:
                messages.success(
                    request,
                    _drive_fix_summary(f"'{ev.name}' now points to a different Drive folder: {message}", uploaded, failed),
                )
            else:
                messages.error(request, f"Could not connect that folder: {message}")
            return redirect("event-switch", event_id=target.id)

        if "force_switch" in request.POST:
            downloaded, failed = event_service.switch_active_event(target)
            summary = (
                f"Switched to '{target.name}' by force — any local photo without a working "
                "Drive backup was discarded."
            )
            if downloaded:
                summary += f" Restored {downloaded} photo(s) from Drive."
            if failed:
                summary += f" {failed} file(s) could not be restored."
            messages.warning(request, summary)
            return redirect("dashboard")

        if "retry_backup" in request.POST:
            if active:
                uploaded, failed = event_service.backup_pending_photos(active)
                if failed:
                    messages.error(request, f"{uploaded} photo(s) backed up, {failed} still failing.")
                else:
                    messages.success(request, f"{uploaded} photo(s) backed up to Drive.")
            return redirect("event-switch", event_id=target.id)

        if "confirm" in request.POST:
            if broken:
                messages.error(request, f"Drive folder for '{broken.name}' is still unreachable.")
                return redirect("event-switch", event_id=target.id)
            if active:
                pending = event_service.unbacked_up_photo_count(active)
                if pending:
                    messages.error(
                        request,
                        f"'{active.name}' still has {pending} photo(s) not backed up to Drive — "
                        "can't switch safely yet.",
                    )
                    return redirect("event-switch", event_id=target.id)
            downloaded, failed = event_service.switch_active_event(target)
            summary = f"Switched to '{target.name}'."
            if downloaded:
                summary += f" Restored {downloaded} photo(s) from Drive."
            if failed:
                summary += f" {failed} file(s) could not be restored."
            messages.success(request, summary)
            return redirect("dashboard")

        return redirect("event-switch", event_id=target.id)

    pending = event_service.unbacked_up_photo_count(active) if (active and active_drive_ok) else 0
    active_photo_count = active.photos.count() if active else 0
    return render(
        request,
        "photos/event_switch_confirm.html",
        {
            "target": target,
            "active": active,
            "pending": pending,
            "active_photo_count": active_photo_count,
            "broken": broken,
        },
    )
