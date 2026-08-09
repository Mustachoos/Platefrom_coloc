from django.contrib import admin

from .models import Photo, SlideshowSettings, UserIdentity
from .models import Like


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("username", "uploaded_at")
    list_filter = ("username",)
    ordering = ("-uploaded_at",)


@admin.register(UserIdentity)
class UserIdentityAdmin(admin.ModelAdmin):
    list_display = ("pseudo", "created_at")
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
