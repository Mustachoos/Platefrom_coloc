from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="upload", permanent=False)),
    path("upload/", views.upload_view, name="upload"),
    path("tv/", views.tv_view, name="tv"),
    path("api/photos/", views.photo_list_api, name="photo-list-api"),
]
