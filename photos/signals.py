import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from . import drive_service
from .models import EventSettings, Photo, SlideshowSettings

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=Photo)
def remove_file_and_notify_tv(sender, instance, **kwargs):
    photo_url = instance.image.url if instance.image else None
    if instance.image:
        instance.image.delete(save=False)

    if instance.drive_file_id:
        try:
            drive_service.trash_file(instance.drive_file_id)
        except drive_service.DriveError as exc:
            logger.warning("Could not remove photo %s from Drive: %s", instance.id, exc)

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "tv_updates",
        {"type": "photo.deleted", "url": photo_url},
    )


@receiver(post_save, sender=SlideshowSettings)
def notify_tv_of_interval_change(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "tv_updates",
        {"type": "settings.changed", "interval_seconds": instance.interval_seconds},
    )


@receiver(post_save, sender=EventSettings)
def notify_tv_of_likes_setting(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "tv_updates",
        {"type": "likes.setting", "enabled": instance.likes_enabled},
    )
