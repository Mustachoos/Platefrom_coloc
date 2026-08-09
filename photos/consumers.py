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
