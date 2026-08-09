import io
import os

import qrcode
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import PseudoForm
from .models import Photo, SlideshowSettings, UserIdentity, Like
from django.shortcuts import get_object_or_404


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
    return UserIdentity.objects.filter(session_key=session_key).first()


def choose_pseudo(request):
    if request.session.get("pseudo"):
        return redirect("upload")

    if request.method == "POST":
        form = PseudoForm(request.POST)
        if form.is_valid():
            pseudo = form.cleaned_data["pseudo"].strip()
            if UserIdentity.objects.filter(pseudo__iexact=pseudo).exists():
                form.add_error("pseudo", "That name is already taken, please choose another one.")
            else:
                if not request.session.session_key:
                    request.session.create()
                try:
                    UserIdentity.objects.create(pseudo=pseudo, session_key=request.session.session_key)
                except IntegrityError:
                    form.add_error("pseudo", "That name is already taken, please choose another one.")
                else:
                    request.session["pseudo"] = pseudo
                    return redirect("upload")
    else:
        form = PseudoForm()
    return render(request, "photos/choose_pseudo.html", {"form": form})


def upload_view(request):
    pseudo = request.session.get("pseudo")
    if not pseudo:
        return redirect("choose-pseudo")

    if request.method == "POST":
        images = request.FILES.getlist("images")
        if images:
            channel_layer = get_channel_layer()
            for image in images:
                photo = Photo.objects.create(username=pseudo, image=image)
                async_to_sync(channel_layer.group_send)(
                    "tv_updates",
                    {"type": "photo.uploaded", "photo": _photo_payload(photo)},
                )
            messages.success(request, f"Uploaded {len(images)} photo(s). Thanks {pseudo}!")
            return redirect("upload")
        messages.error(request, "Please choose at least one photo.")
    return render(request, "photos/upload.html", {"pseudo": pseudo})


def tv_view(request):
    return render(request, "photos/tv.html")


def my_photos_view(request):
    pseudo = request.session.get("pseudo")
    if not pseudo:
        return redirect("choose-pseudo")
    photos = Photo.objects.filter(username=pseudo).order_by("uploaded_at")
    return render(request, "photos/my_photos.html", {"pseudo": pseudo, "photos": photos})


def photo_detail_view(request, photo_id):
    pseudo = request.session.get("pseudo")
    if not pseudo:
        return redirect("choose-pseudo")
    photo = get_object_or_404(Photo, id=photo_id, username=pseudo)
    return render(request, "photos/photo_detail.html", {"photo": photo})


def delete_own_photo(request, photo_id):
    pseudo = request.session.get("pseudo")
    if not pseudo:
        return redirect("choose-pseudo")
    if request.method == "POST":
        # username=pseudo in the lookup ensures a user can only ever delete
        # their own photos, not just anything visible in their session.
        photo = get_object_or_404(Photo, id=photo_id, username=pseudo)
        photo.delete()
        messages.success(request, "Photo deleted.")
    return redirect("my-photos")


def photo_list_api(request):
    user = _get_user_identity(request)
    photos = Photo.objects.order_by("uploaded_at")
    return JsonResponse([_photo_payload(photo, user=user) for photo in photos], safe=False)


def like_toggle_api(request, photo_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    user = _get_user_identity(request)
    if not user:
        return JsonResponse({"error": "identity required"}, status=403)
    photo = get_object_or_404(Photo, pk=photo_id)
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
    photos = Photo.objects.order_by("-uploaded_at")
    payloads = [_photo_payload(photo, user=user) for photo in photos]
    return render(request, "photos/gallery.html", {"photos": payloads})


def slideshow_settings_api(request):
    settings_obj = SlideshowSettings.get_solo()
    return JsonResponse({"interval_seconds": settings_obj.interval_seconds})


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
