from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="upload", permanent=False)),
    path("pseudo/", views.choose_pseudo, name="choose-pseudo"),
    path("upload/", views.upload_view, name="upload"),
    path("my-photos/", views.my_photos_view, name="my-photos"),
    path("my-photos/<int:photo_id>/delete/", views.delete_own_photo, name="delete-own-photo"),
    path("tv/", views.tv_view, name="tv"),
    path("api/photos/", views.photo_list_api, name="photo-list-api"),
    path("api/settings/", views.slideshow_settings_api, name="slideshow-settings-api"),
    path("qr/upload.png", views.upload_qr_code, name="upload-qr-code"),
]
