from django.contrib import admin

from . import drive_service
from .models import EventSettings, Photo, SlideshowSettings, UserIdentity
from .models import Like


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("username", "uploaded_at")
    list_filter = ("username",)
    ordering = ("-uploaded_at",)


@admin.register(UserIdentity)
class UserIdentityAdmin(admin.ModelAdmin):
    list_display = ("pseudo", "email", "drive_shared", "created_at")
    ordering = ("-created_at",)


@admin.register(SlideshowSettings)
class SlideshowSettingsAdmin(admin.ModelAdmin):
    list_display = ("interval_seconds",)

    def has_add_permission(self, request):
        return not SlideshowSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "photo", "created_at")
    ordering = ("-created_at",)


@admin.register(EventSettings)
class EventSettingsAdmin(admin.ModelAdmin):
    list_display = ("drive_enabled", "drive_folder_name", "drive_folder_id")
    readonly_fields = ("drive_folder_id", "drive_folder_url")

    def has_add_permission(self, request):
        return not EventSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.drive_enabled:
            return
        try:
            folder_id, folder_url = drive_service.get_or_create_event_folder(obj.drive_folder_name)
        except drive_service.DriveError as exc:
            self.message_user(request, f"Google Drive folder not connected: {exc}", level="error")
            return
        EventSettings.objects.filter(pk=obj.pk).update(
            drive_folder_id=folder_id, drive_folder_url=folder_url
        )
        self.message_user(request, f"Drive folder '{obj.drive_folder_name}' connected: {folder_url}")
