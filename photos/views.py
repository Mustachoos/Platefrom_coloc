from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import UploadForm
from .models import Photo


def _photo_payload(photo):
    return {
        "url": photo.image.url,
        "username": photo.username,
        "uploaded_at": photo.uploaded_at.isoformat(),
    }


def upload_view(request):
    if request.method == "POST":
        form = UploadForm(request.POST)
        # Django's FileField doesn't support multiple files cleanly, so the
        # file input is read directly from request.FILES instead of the form.
        images = request.FILES.getlist("images")
        if form.is_valid() and images:
            username = form.cleaned_data["username"]
            channel_layer = get_channel_layer()
            for image in images:
                photo = Photo.objects.create(username=username, image=image)
                async_to_sync(channel_layer.group_send)(
                    "tv_updates",
                    {"type": "photo.uploaded", "photo": _photo_payload(photo)},
                )
            messages.success(request, f"Uploaded {len(images)} photo(s). Thanks {username}!")
            return redirect("upload")
        if not images:
            messages.error(request, "Please choose at least one photo.")
    else:
        form = UploadForm()
    return render(request, "photos/upload.html", {"form": form})


def tv_view(request):
    return render(request, "photos/tv.html")


def photo_list_api(request):
    photos = Photo.objects.order_by("uploaded_at")
    return JsonResponse([_photo_payload(photo) for photo in photos], safe=False)
