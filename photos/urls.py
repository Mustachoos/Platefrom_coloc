from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="upload", permanent=False)),
    path("pseudo/", views.choose_pseudo, name="choose-pseudo"),
    path("pseudo/share-drive/", views.share_drive_view, name="share-drive"),
    path("upload/", views.upload_view, name="upload"),
    path("my-photos/", views.my_photos_view, name="my-photos"),
    path("my-photos/<int:photo_id>/delete/", views.delete_own_photo, name="delete-own-photo"),
    path("tv/", views.tv_view, name="tv"),
    path("whiteboard/", views.whiteboard_draw_view, name="whiteboard-draw"),
    path("whiteboard/upload/", views.whiteboard_upload_view, name="whiteboard-upload"),
    path("api/photos/", views.photo_list_api, name="photo-list-api"),
    path("api/photos/<int:photo_id>/like/", views.like_toggle_api, name="photo-like-api"),
    path("gallery/", views.gallery_view, name="gallery"),
    path("api/settings/", views.slideshow_settings_api, name="slideshow-settings-api"),
    path("qr/upload.png", views.upload_qr_code, name="upload-qr-code"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("dashboard/photos/<int:photo_id>/delete/", views.dashboard_delete_photo, name="dashboard-delete-photo"),
    path(
        "dashboard/whiteboard/<int:drawing_id>/delete/",
        views.dashboard_delete_whiteboard_drawing,
        name="dashboard-delete-whiteboard-drawing",
    ),
    path("dashboard/events/create/", views.create_event_view, name="create-event"),
    path("dashboard/events/<int:event_id>/switch/", views.event_switch_view, name="event-switch"),
]
