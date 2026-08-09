from django.contrib import admin

from .models import Photo, SlideshowSettings


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("username", "uploaded_at")
    list_filter = ("username",)
    ordering = ("-uploaded_at",)


@admin.register(SlideshowSettings)
class SlideshowSettingsAdmin(admin.ModelAdmin):
    list_display = ("interval_seconds",)

    def has_add_permission(self, request):
        return not SlideshowSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
