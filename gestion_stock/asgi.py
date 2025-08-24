import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import authentification.routing  # your chat routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_stock.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            authentification.routing.websocket_urlpatterns
        )
    ),
})
