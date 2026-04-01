# gestion_stock/asgi_websocket.py
import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_stock.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
import chat.routing

# No AuthMiddleware - just direct routing
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(
        chat.routing.websocket_urlpatterns
    ),
})