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
    list_display = ("drive_enabled", "drive_folder_name", "drive_folder_id", "likes_enabled")
    readonly_fields = ("drive_folder_url",)

    def has_add_permission(self, request):
        return not EventSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.drive_enabled:
            return
        if "drive_folder_id" in form.changed_data and obj.drive_folder_id.strip():
            ok, message = drive_service.connect_existing_folder(obj)
        else:
            ok, message = drive_service.connect_event_folder(obj)
        if ok:
            self.message_user(request, f"Drive folder '{obj.drive_folder_name}' connected: {message}")
        else:
            self.message_user(request, f"Google Drive folder not connected: {message}", level="error")
