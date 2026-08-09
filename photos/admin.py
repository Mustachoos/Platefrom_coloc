from django.contrib import admin

from .models import Photo


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("username", "uploaded_at")
    list_filter = ("username",)
    ordering = ("-uploaded_at",)
