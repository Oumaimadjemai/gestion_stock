# passenger_wsgi.py
import os
import sys

# Ajouter le chemin du projet au PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__))

# Configurer les variables d'environnement
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_stock.settings')

# Essayer de charger .env si présent
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

# Importer l'application WSGI
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()