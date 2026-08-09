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
    def likes_count(self):
        return self.likes.count()


class UserIdentity(models.Model):
    pseudo = models.CharField(max_length=50, unique=True)
    session_key = models.CharField(max_length=40, unique=True)
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
