from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Photo, SlideshowSettings


@receiver(post_delete, sender=Photo)
def remove_file_and_notify_tv(sender, instance, **kwargs):
    photo_url = instance.image.url if instance.image else None
    if instance.image:
        instance.image.delete(save=False)

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
