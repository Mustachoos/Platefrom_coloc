import os

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Photo(models.Model):
    username = models.CharField(max_length=50)
    image = models.ImageField(upload_to="photos/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.username} - {self.uploaded_at:%Y-%m-%d %H:%M}"

    @property
    def filename(self):
        return os.path.basename(self.image.name)


class UserIdentity(models.Model):
    pseudo = models.CharField(max_length=50, unique=True)
    session_key = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.pseudo


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
