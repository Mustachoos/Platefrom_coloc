from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from . import admin_views, views
from .forms import StyledSetPasswordForm

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="upload", permanent=False)),
    path("staff-login/", views.staff_login_view, name="staff-login"),
    path("logout/", LogoutView.as_view(next_page=reverse_lazy("staff-login")), name="staff-logout"),
    path("account/", views.account_view, name="account"),
    path("staff-login/reset/", admin_views.SupportEmailPasswordResetView.as_view(), name="password-reset"),
    path(
        "staff-login/reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="photos/password_reset_done.html"),
        name="password-reset-done",
    ),
    path(
        "staff-login/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="photos/password_reset_confirm.html",
            success_url=reverse_lazy("password-reset-complete"),
            form_class=StyledSetPasswordForm,
        ),
        name="password-reset-confirm",
    ),
    path(
        "staff-login/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="photos/password_reset_complete.html"),
        name="password-reset-complete",
    ),
    path("create-admin/", admin_views.create_admin_view, name="create-admin"),
    path("admin-account/", admin_views.admin_management_view, name="admin-management"),
    path("admin-account/drive/google/connect/", admin_views.drive_google_connect_view, name="drive-google-connect"),
    path("admin-account/drive/google/callback/", admin_views.drive_google_callback_view, name="drive-google-callback"),
    path(
        "admin-account/invites/<uuid:token>/revoke/",
        admin_views.revoke_invite_view,
        name="admin-invite-revoke",
    ),
    path(
        "admin-account/invites/<uuid:token>/delete/",
        admin_views.delete_invite_view,
        name="admin-invite-delete",
    ),
    path("admin-account/invite/<uuid:token>/", admin_views.subadmin_invite_view, name="subadmin-invite"),
    path(
        "admin-account/verify-ip/<uuid:token>/status/",
        admin_views.verify_ip_status_view,
        name="verify-ip-status",
    ),
    path("admin-account/verify-ip/<uuid:token>/", admin_views.verify_ip_page_view, name="verify-ip-page"),
    path(
        "admin-account/verify-support-email/<uuid:token>/",
        admin_views.verify_support_email_view,
        name="verify-support-email",
    ),
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
    path("dashboard/guests/<int:identity_id>/delete/", views.dashboard_delete_guest, name="dashboard-delete-guest"),
    path(
        "dashboard/whiteboard/<int:drawing_id>/delete/",
        views.dashboard_delete_whiteboard_drawing,
        name="dashboard-delete-whiteboard-drawing",
    ),
    path("dashboard/events/create/", views.create_event_view, name="create-event"),
    path("dashboard/events/<int:event_id>/switch/", views.event_switch_view, name="event-switch"),
    path("dashboard/drive/reauth/", views.drive_reauth_start, name="drive-reauth-start"),
    path("dashboard/drive/reauth/callback/", views.drive_reauth_callback, name="drive-reauth-callback"),
]
