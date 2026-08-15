import os
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def photo_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    username_part = slugify(instance.username) or "user"
    time_part = timezone.localtime().strftime("%Hh%M")
    unique_id = uuid.uuid4().hex[:8]
    return f"photos/{username_part}_{time_part}_{unique_id}{ext}"


class Photo(models.Model):
    username = models.CharField(max_length=50)
    image = models.ImageField(upload_to=photo_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.username} - {self.uploaded_at:%Y-%m-%d %H:%M}"

    @property
    def filename(self):
        return os.path.basename(self.image.name)
    @property
    def likes_count(self):
        return self.likes.count()


class UserIdentity(models.Model):
    pseudo = models.CharField(max_length=50, unique=True)
    session_key = models.CharField(max_length=40, unique=True)
    email = models.EmailField(blank=True)
    drive_shared = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.pseudo


class Like(models.Model):
    photo = models.ForeignKey(Photo, related_name="likes", on_delete=models.CASCADE)
    user = models.ForeignKey(UserIdentity, related_name="likes", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("photo", "user")

    def __str__(self):
        return f"{self.user.pseudo} ♥ {self.photo.id}"


class SlideshowSettings(models.Model):
    interval_seconds = models.FloatField(
        default=5.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(100)],
        help_text="How long each photo stays on screen, in seconds (0.1-100).",
    )

    class Meta:
        verbose_name = "Slideshow settings"
        verbose_name_plural = "Slideshow settings"

    def __str__(self):
        return f"Slideshow interval: {self.interval_seconds}s"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


def default_drive_folder_name():
    return timezone.localtime().strftime("%d/%m/%Y")


class EventSettings(models.Model):
    """Per-event toggles and config. Singleton, like SlideshowSettings.

    Meant to grow into the home for other optional features (chat,
    whiteboard, ...) alongside drive_enabled, following the same on/off +
    config pattern.
    """

    drive_enabled = models.BooleanField(
        default=False,
        help_text="When on, uploaded photos are also copied to a Google Drive folder, "
        "and guests are offered to share that folder to their email.",
    )
    drive_folder_name = models.CharField(
        max_length=200,
        default=default_drive_folder_name,
        help_text="Name of the Drive folder for this event. Reused if it already exists "
        "under the configured root folder; created otherwise.",
    )
    drive_folder_id = models.CharField(max_length=100, blank=True)
    drive_folder_url = models.URLField(blank=True)
    likes_enabled = models.BooleanField(
        default=True,
        help_text="When off, the heart/like button is hidden and the TV leaderboard is hidden.",
    )

    class Meta:
        verbose_name = "Event settings"
        verbose_name_plural = "Event settings"

    def __str__(self):
        return f"Event settings (drive {'on' if self.drive_enabled else 'off'})"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
