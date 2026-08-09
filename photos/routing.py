from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/tv/$", consumers.PhotosConsumer.as_asgi()),
]
