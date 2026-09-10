import io
import logging
import re
import zipfile

import qrcode
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login as auth_login
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from . import drive_service, event_service, whiteboard_service
from .admin_views import superuser_required
from .forms import PseudoForm, ShareDriveForm, StaffLoginForm, StyledPasswordChangeForm
from .models import Event, Like, Photo, SiteSettings, SlideshowSettings, UserIdentity, WhiteboardDrawing

logger = logging.getLogger(__name__)

WHITEBOARD_COOLDOWN_SECONDS = 30


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


def account_view(request):
    identity = _get_user_identity(request)
    if not request.user.is_authenticated and not identity:
        return redirect("choose-pseudo")

    password_form = None
    if request.user.is_authenticated:
        if request.method == "POST" and "update_email" in request.POST:
            request.user.email = request.POST.get("email", "").strip()
            request.user.save(update_fields=["email"])
            messages.success(request, "Email updated.")
            return redirect("account")

        if request.method == "POST" and "change_password" in request.POST:
            password_form = StyledPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Changing your own password rotates the session auth hash —
                # without this you'd be logged out by your own request.
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed.")
                return redirect("account")
        else:
            password_form = StyledPasswordChangeForm(request.user)

    return render(request, "photos/account.html", {"identity": identity, "password_form": password_form})


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
                    if not active_event.drive_folder_id:
                        return redirect("upload")
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

    if not active_event.drive_folder_id:
        return redirect("upload")

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
    return render(
        request,
        "photos/upload.html",
        {"pseudo": pseudo, "just_uploaded": just_uploaded, "whiteboard_enabled": active_event.whiteboard_enabled},
    )


def tv_view(request):
    site_settings = SiteSettings.get_solo()
    wifi_qr_shown = bool(site_settings.wifi_qr_enabled and site_settings.wifi_ssid)
    return render(request, "photos/tv.html", {"wifi_qr_shown": wifi_qr_shown})


def whiteboard_draw_view(request):
    active_event = Event.get_active()
    if active_event is None or not active_event.whiteboard_enabled:
        return render(request, "photos/no_active_event.html")
    user = _get_user_identity(request)
    if not user:
        return redirect("choose-pseudo")

    last = (
        WhiteboardDrawing.objects.filter(event=active_event, username=user.pseudo)
        .order_by("-uploaded_at")
        .first()
    )
    cooldown_remaining = 0
    if last:
        elapsed = (timezone.now() - last.uploaded_at).total_seconds()
        cooldown_remaining = max(0, WHITEBOARD_COOLDOWN_SECONDS - elapsed)

    return render(
        request,
        "photos/whiteboard_draw.html",
        {
            "pseudo": user.pseudo,
            "board_image_url": active_event.whiteboard_image.url if active_event.whiteboard_image else "",
            "board_width": whiteboard_service.WIDTH,
            "board_height": whiteboard_service.HEIGHT,
            "pen_max": whiteboard_service.WIDTH // 300,
            "cooldown_remaining": cooldown_remaining,
            "cooldown_seconds": WHITEBOARD_COOLDOWN_SECONDS,
            "whiteboard_enabled": True,
        },
    )


def whiteboard_upload_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    active_event = Event.get_active()
    if not active_event or not active_event.whiteboard_enabled:
        return JsonResponse({"error": "The whiteboard is disabled."}, status=403)
    user = _get_user_identity(request)
    if not user:
        return JsonResponse({"error": "identity required"}, status=403)

    last = (
        WhiteboardDrawing.objects.filter(event=active_event, username=user.pseudo)
        .order_by("-uploaded_at")
        .first()
    )
    if last:
        elapsed = (timezone.now() - last.uploaded_at).total_seconds()
        if elapsed < WHITEBOARD_COOLDOWN_SECONDS:
            return JsonResponse(
                {"error": "cooldown", "retry_after": round(WHITEBOARD_COOLDOWN_SECONDS - elapsed, 1)},
                status=429,
            )

    image = request.FILES.get("drawing")
    if not image:
        return JsonResponse({"error": "No drawing provided."}, status=400)

    drawing = WhiteboardDrawing.objects.create(event=active_event, username=user.pseudo, image=image)
    whiteboard_service.add_layer(active_event, drawing)

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "tv_updates",
        {"type": "whiteboard.updated", "url": active_event.whiteboard_image.url},
    )
    return JsonResponse({"ok": True})


def my_photos_view(request):
    user = _get_user_identity(request)
    if not user:
        return redirect("choose-pseudo")
    photos = Photo.objects.filter(event=user.event, username=user.pseudo).order_by("uploaded_at")
    return render(
        request,
        "photos/my_photos.html",
        {"pseudo": user.pseudo, "photos": photos, "whiteboard_enabled": user.event.whiteboard_enabled},
    )


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
    photos = Photo.objects.filter(event=active_event, hidden=False).order_by("uploaded_at")
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
    if photo.hidden:
        return JsonResponse({"error": "photo is hidden"}, status=403)
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
    photos_qs = (
        Photo.objects.filter(event=active_event, hidden=False).order_by("-uploaded_at")
        if active_event
        else Photo.objects.none()
    )
    payloads = [_photo_payload(photo, user=user) for photo in photos_qs]
    likes_enabled = active_event.likes_enabled if active_event else True
    whiteboard_enabled = active_event.whiteboard_enabled if active_event else False
    return render(
        request,
        "photos/gallery.html",
        {"photos": payloads, "likes_enabled": likes_enabled, "whiteboard_enabled": whiteboard_enabled},
    )


def slideshow_settings_api(request):
    slideshow = SlideshowSettings.get_solo()
    active_event = Event.get_active()
    likes_enabled = active_event.likes_enabled if active_event else True
    tv_layout = active_event.tv_layout if active_event else Event.TV_LAYOUT_SLIDESHOW
    tv_bottom_right = active_event.tv_bottom_right if active_event else Event.TV_BOTTOM_RIGHT_NONE
    whiteboard_image_url = active_event.whiteboard_image.url if active_event and active_event.whiteboard_image else ""
    site_settings = SiteSettings.get_solo()
    wifi_qr_shown = bool(site_settings.wifi_qr_enabled and site_settings.wifi_ssid)
    return JsonResponse(
        {
            "interval_seconds": slideshow.interval_seconds,
            "likes_enabled": likes_enabled,
            "tv_layout": tv_layout,
            "tv_bottom_right": tv_bottom_right,
            "whiteboard_image_url": whiteboard_image_url,
            "wifi_qr_shown": wifi_qr_shown,
        }
    )


def upload_qr_code(request):
    # A verified address (see the admin account page) always wins — it's
    # been proven reachable by an actual phone scan, and already carries its
    # own port (captured straight from that verifying request's Host header).
    # Otherwise, derive it live from whatever request loaded this page.
    server_host = SiteSettings.get_solo().server_host
    if server_host:
        scheme = "https" if request.is_secure() else "http"
        upload_url = f"{scheme}://{server_host}{reverse('upload')}"
    else:
        upload_url = request.build_absolute_uri(reverse("upload"))
    image = qrcode.make(upload_url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


_WIFI_QR_ESCAPE_RE = re.compile(r'([\\;,"])')


def _wifi_qr_escape(value):
    # Per the WIFI: QR payload convention (no formal RFC, but universally
    # implemented this way): backslash, semicolon, comma and double-quote
    # are field/record separators or quoting characters, so a literal one
    # inside the SSID/password has to be backslash-escaped.
    return _WIFI_QR_ESCAPE_RE.sub(r"\\\1", value)


def wifi_qr_code(request):
    site_settings = SiteSettings.get_solo()
    if not site_settings.wifi_qr_enabled or not site_settings.wifi_ssid:
        return HttpResponse(status=404)
    ssid = site_settings.wifi_ssid
    if site_settings.wifi_security == SiteSettings.WIFI_SECURITY_NOPASS:
        payload = f"WIFI:T:nopass;S:{_wifi_qr_escape(ssid)};;"
    else:
        payload = (
            f"WIFI:T:{site_settings.wifi_security};"
            f"S:{_wifi_qr_escape(ssid)};"
            f"P:{_wifi_qr_escape(site_settings.wifi_password)};;"
        )
    image = qrcode.make(payload)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


@staff_member_required(login_url="staff-login")
def drive_reauth_start(request):
    """Kicks off the web-based OAuth flow: redirect the admin's own browser
    to Google's consent screen, distinct from `manage.py google_drive_auth`
    which opens a browser and a local server on whatever machine runs the
    command — meaningless from inside this container. Only works when the
    dashboard itself is loaded via localhost, since the OAuth client is a
    Desktop-app type (only accepts loopback redirect URIs)."""
    if request.method != "POST":
        return _dashboard_redirect(tab="features")
    redirect_uri = request.build_absolute_uri(reverse("drive-reauth-callback"))
    try:
        flow = drive_service.build_oauth_flow(redirect_uri)
    except drive_service.DriveError as exc:
        messages.error(request, f"Could not start Google Drive authorization: {exc}")
        return _dashboard_redirect(tab="features")
    auth_url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )
    request.session["drive_oauth_state"] = state
    return redirect(auth_url)


@staff_member_required(login_url="staff-login")
def drive_reauth_callback(request):
    expected_state = request.session.pop("drive_oauth_state", None)
    if not expected_state or request.GET.get("state") != expected_state:
        messages.error(request, "Google Drive authorization failed (session expired) — try again.")
        return _dashboard_redirect(tab="features")
    if "error" in request.GET:
        messages.error(request, f"Google Drive authorization was not completed: {request.GET['error']}")
        return _dashboard_redirect(tab="features")
    redirect_uri = request.build_absolute_uri(reverse("drive-reauth-callback"))
    try:
        flow = drive_service.build_oauth_flow(redirect_uri)
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        drive_service.save_credentials(flow.credentials)
    except Exception as exc:
        logger.warning("Drive re-auth callback failed: %s", exc)
        messages.error(request, f"Google Drive authorization failed: {exc}")
        return _dashboard_redirect(tab="features")
    messages.success(request, "Google Drive reconnected.")
    return _dashboard_redirect(tab="features")


def _post_login_redirect(user):
    return redirect("admin-management" if user.is_superuser else "dashboard")


def staff_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return _post_login_redirect(request.user)

    if request.method == "POST":
        form = StaffLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_staff:
                form.add_error(None, "This account doesn't have staff access.")
            else:
                auth_login(request, user)
                return _post_login_redirect(user)
    else:
        form = StaffLoginForm(request)
    recovery_email_configured = bool(SiteSettings.get_solo().support_email)
    return render(request, "photos/staff_login.html", {
        "form": form, "recovery_email_configured": recovery_email_configured,
    })


@staff_member_required(login_url="staff-login")
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
            return _dashboard_redirect(tab="features")
        if "toggle_likes" in request.POST:
            active_event.likes_enabled = not active_event.likes_enabled
            update_fields = ["likes_enabled"]
            if not active_event.likes_enabled and active_event.tv_bottom_right == Event.TV_BOTTOM_RIGHT_LEADERBOARD:
                # The TV can't keep showing a leaderboard for likes that just got turned off.
                active_event.tv_bottom_right = Event.TV_BOTTOM_RIGHT_NONE
                update_fields.append("tv_bottom_right")
            active_event.save(update_fields=update_fields)
            messages.success(request, "Likes " + ("enabled." if active_event.likes_enabled else "disabled."))
            return _dashboard_redirect(tab="tv-layout")
        if "toggle_whiteboard" in request.POST:
            active_event.whiteboard_enabled = not active_event.whiteboard_enabled
            update_fields = ["whiteboard_enabled"]
            if not active_event.whiteboard_enabled and active_event.tv_layout == Event.TV_LAYOUT_WHITEBOARD:
                # The TV can't keep showing a whiteboard that just got turned off.
                active_event.tv_layout = Event.TV_LAYOUT_SLIDESHOW
                update_fields.append("tv_layout")
            active_event.save(update_fields=update_fields)
            messages.success(request, "Whiteboard " + ("enabled." if active_event.whiteboard_enabled else "disabled."))
            return _dashboard_redirect(tab="tv-layout")
        if "set_tv_layout" in request.POST:
            layout = request.POST.get("set_tv_layout")
            valid_layouts = dict(Event.TV_LAYOUT_CHOICES)
            if layout not in valid_layouts:
                messages.error(request, "Unknown TV layout.")
            elif layout == Event.TV_LAYOUT_WHITEBOARD and not active_event.whiteboard_enabled:
                messages.error(request, "Enable the whiteboard feature first.")
            else:
                active_event.tv_layout = layout
                active_event.save(update_fields=["tv_layout"])
                messages.success(request, f"TV now shows the {valid_layouts[layout].lower()}.")
            return _dashboard_redirect(tab="tv-layout")
        if "set_tv_bottom_right" in request.POST:
            widget = request.POST.get("set_tv_bottom_right")
            valid_widgets = dict(Event.TV_BOTTOM_RIGHT_CHOICES)
            if widget not in valid_widgets:
                messages.error(request, "Unknown TV widget.")
            elif widget == Event.TV_BOTTOM_RIGHT_LEADERBOARD and not active_event.likes_enabled:
                messages.error(request, "Enable Photo likes first.")
            else:
                active_event.tv_bottom_right = widget
                active_event.save(update_fields=["tv_bottom_right"])
                messages.success(request, f"TV now shows {valid_widgets[widget].lower()} in the bottom-right frame.")
            return _dashboard_redirect(tab="tv-layout")
        return _dashboard_redirect(tab="features")

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
        whiteboard_drawings = active_event.whiteboard_drawings.order_by("-uploaded_at")
    else:
        identities = UserIdentity.objects.none()
        photos = Photo.objects.none()
        whiteboard_drawings = WhiteboardDrawing.objects.none()
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
            "whiteboard_drawings": whiteboard_drawings,
            "guests_with_email": guests_with_email,
            "guests_shared": guests_shared,
            "active_tab": active_tab,
            # Surfaces whether *this* staff session already holds a guest
            # identity, so the "Start a guest session" entry point can read
            # "Continue as guest" instead — no change to the identity
            # mechanism itself, just reusing it (see US-B1).
            "guest_identity": _get_user_identity(request),
        },
    )


@staff_member_required(login_url="staff-login")
def dashboard_delete_photo(request, photo_id):
    if request.method == "POST":
        photo = get_object_or_404(Photo, id=photo_id)
        photo.delete()
        messages.success(request, "Photo deleted.")
    return _dashboard_redirect(tab="photos")


@staff_member_required(login_url="staff-login")
def dashboard_toggle_photo_hidden(request, photo_id):
    if request.method == "POST":
        photo = get_object_or_404(Photo, id=photo_id)
        photo.hidden = not photo.hidden
        photo.save(update_fields=["hidden"])
        channel_layer = get_channel_layer()
        if photo.hidden:
            async_to_sync(channel_layer.group_send)(
                "tv_updates",
                {"type": "photo.hidden", "url": photo.image.url},
            )
            messages.success(request, "Photo hidden.")
        else:
            async_to_sync(channel_layer.group_send)(
                "tv_updates",
                {"type": "photo.uploaded", "photo": _photo_payload(photo)},
            )
            messages.success(request, "Photo unhidden.")
    return _dashboard_redirect(tab="photos")


@staff_member_required(login_url="staff-login")
def dashboard_delete_guest(request, identity_id):
    if request.method == "POST":
        identity = get_object_or_404(UserIdentity, id=identity_id)
        pseudo = identity.pseudo
        revoke_failed = False
        if identity.drive_shared and identity.drive_permission_id and identity.event.drive_folder_id:
            try:
                drive_service.revoke_folder_permission(identity.event.drive_folder_id, identity.drive_permission_id)
            except drive_service.DriveError as exc:
                revoke_failed = True
                logger.warning("Could not revoke Drive access for %s: %s", identity.email, exc)
        identity.delete()
        if revoke_failed:
            messages.error(
                request,
                f"'{pseudo}' removed, but revoking their Drive access failed — "
                "you may need to remove it manually in Drive's sharing settings.",
            )
        else:
            messages.success(request, f"'{pseudo}' removed from the event.")
    return _dashboard_redirect(tab="guests")


@staff_member_required(login_url="staff-login")
def dashboard_delete_whiteboard_drawing(request, drawing_id):
    if request.method == "POST":
        drawing = get_object_or_404(WhiteboardDrawing, id=drawing_id)
        event = drawing.event
        drawing.delete()
        whiteboard_service.rebuild_board(event)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "tv_updates",
            {"type": "whiteboard.updated", "url": event.whiteboard_image.url if event.whiteboard_image else ""},
        )
        messages.success(request, "Drawing removed from the whiteboard.")
    return _dashboard_redirect(tab="whiteboard")


@staff_member_required(login_url="staff-login")
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
    if not event.drive_folder_id and drive_service.is_configured():
        ok, message = event_service.ensure_drive_folder(event)
        if not ok:
            messages.error(
                request,
                f"Event '{name}' saved, but its Drive folder could not be connected: {message}. "
                "Fix it from the events list, then switch to it.",
            )
            return redirect("dashboard")
    return redirect("event-switch", event_id=event.id)


@staff_member_required(login_url="staff-login")
def event_switch_view(request, event_id):
    target = get_object_or_404(Event, id=event_id)
    active = Event.get_active()

    if target.is_active:
        messages.info(request, f"'{target.name}' is already the active event.")
        return redirect("dashboard")

    # Live, uncached check every time this page is hit — a cached
    # drive_folder_id can't tell us the folder wasn't deleted/unshared since
    # the last time we looked. An event with no Drive folder at all (Drive
    # is optional) isn't "broken" — only a folder that existed and is now
    # unreachable counts as broken.
    active_drive_ok = drive_service.folder_exists(active.drive_folder_id) if (active and active.drive_folder_id) else True
    target_drive_ok = drive_service.folder_exists(target.drive_folder_id) if target.drive_folder_id else True
    broken = (
        active if (active and active.drive_folder_id and not active_drive_ok)
        else (target if (target.drive_folder_id and not target_drive_ok) else None)
    )

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
            if active and active.drive_folder_id:
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

    pending = event_service.unbacked_up_photo_count(active) if (active and active.drive_folder_id and active_drive_ok) else 0
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


@superuser_required
def event_delete_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method != "POST":
        return _dashboard_redirect(tab="events")

    if event.is_active:
        messages.error(request, "Switch to another event before deleting this one.")
        return _dashboard_redirect(tab="events")

    name = event.name
    for photo in event.photos.all():
        photo.image.delete(save=False)
    for drawing in event.whiteboard_drawings.all():
        drawing.image.delete(save=False)
    event.delete()
    messages.success(request, f"'{name}' deleted.")
    return _dashboard_redirect(tab="events")


@staff_member_required(login_url="staff-login")
def event_export_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for photo in event.photos.all():
            zip_file.write(photo.image.path, arcname=photo.filename)

    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    filename = f"{slugify(event.name)}-photos.zip"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
