import io
import os

import qrcode
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import PseudoForm
from .models import Photo, SlideshowSettings, UserIdentity


def _photo_payload(photo):
    return {
        "url": photo.image.url,
        "username": photo.username,
        "uploaded_at": photo.uploaded_at.isoformat(),
    }


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


def photo_list_api(request):
    photos = Photo.objects.order_by("uploaded_at")
    return JsonResponse([_photo_payload(photo) for photo in photos], safe=False)


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
