# gestion_stock/asgi_simple.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_stock.settings')

# Simple ASGI without Channels for testing
application = get_asgi_application()