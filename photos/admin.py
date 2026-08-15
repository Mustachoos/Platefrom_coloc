from django.contrib import admin

from . import drive_service, event_service
from .models import Event, Photo, SlideshowSettings, UserIdentity
from .models import Like


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("username", "event", "uploaded_at")
    list_filter = ("event", "username")
    ordering = ("-uploaded_at",)


@admin.register(UserIdentity)
class UserIdentityAdmin(admin.ModelAdmin):
    list_display = ("pseudo", "event", "email", "drive_shared", "created_at")
    list_filter = ("event",)
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


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "drive_folder_id", "likes_enabled", "drive_sharing_enabled", "created_at")
    readonly_fields = ("drive_folder_url",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if "drive_folder_id" in form.changed_data and obj.drive_folder_id.strip():
            ok, message = drive_service.connect_existing_folder(obj)
        else:
            ok, message = event_service.ensure_drive_folder(obj)
        if ok:
            self.message_user(request, f"Drive folder connected: {message}")
        else:
            self.message_user(request, f"Google Drive folder not connected: {message}", level="error")
