# chat/routing_minimal.py
from django.urls import re_path
from .consumers_minimal import MinimalConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/$', MinimalConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<room_id>\d+)/$', MinimalConsumer.as_asgi()),
]