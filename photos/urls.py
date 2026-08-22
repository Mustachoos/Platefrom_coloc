from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from . import admin_views, setup_views, views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="upload", permanent=False)),
    path("staff-login/", views.staff_login_view, name="staff-login"),
    path("logout/", LogoutView.as_view(next_page=reverse_lazy("staff-login")), name="staff-logout"),
    path("setup/", setup_views.welcome_view, name="setup-welcome"),
    path("setup/admin/", setup_views.admin_account_view, name="setup-admin"),
    path("setup/drive/", setup_views.drive_view, name="setup-drive"),
    path("setup/google/connect/", setup_views.google_connect_view, name="setup-google-connect"),
    path("setup/google/callback/", setup_views.google_callback_view, name="setup-google-callback"),
    path("setup/network/", setup_views.network_view, name="setup-network"),
    path("setup/event/", setup_views.first_event_view, name="setup-event"),
    path("admin-account/", admin_views.admin_management_view, name="admin-management"),
    path(
        "admin-account/invites/<uuid:token>/revoke/",
        admin_views.revoke_invite_view,
        name="admin-invite-revoke",
    ),
    path("admin-account/invite/<uuid:token>/", admin_views.subadmin_invite_view, name="subadmin-invite"),
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
    path("qr/wifi.png", views.wifi_qr_code, name="wifi-qr-code"),
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
