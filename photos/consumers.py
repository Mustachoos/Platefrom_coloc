import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer


class PhotosConsumer(WebsocketConsumer):
    group_name = "tv_updates"

    def connect(self):
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def photo_uploaded(self, event):
        self.send(text_data=json.dumps({"event": "uploaded", "photo": event["photo"]}))

    def photo_deleted(self, event):
        self.send(text_data=json.dumps({"event": "deleted", "url": event["url"]}))

    def settings_changed(self, event):
        self.send(text_data=json.dumps({"event": "settings", "interval_seconds": event["interval_seconds"]}))

    def photo_liked(self, event):
        self.send(text_data=json.dumps({"event": "liked", "photo_id": event["photo_id"], "likes_count": event["likes_count"]}))

    def likes_setting(self, event):
        self.send(text_data=json.dumps({"event": "likes_setting", "enabled": event["enabled"]}))

    def event_switched(self, event):
        self.send(text_data=json.dumps({"event": "event_switched"}))

    def whiteboard_updated(self, event):
        self.send(text_data=json.dumps({"event": "whiteboard_updated", "url": event["url"]}))

    def tv_layout_changed(self, event):
        self.send(text_data=json.dumps({"event": "tv_layout_changed"}))
