"""
Django settings for gestion_stock project.
"""

from pathlib import Path
from decouple import config
import dj_database_url
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="unsafe-secret-key")
DEBUG = config("DEBUG", default=False, cast=bool)

# ✅ Update ALLOWED_HOSTS for local development
ALLOWED_HOSTS = [
    "darlokman.com",
    "www.darlokman.com",
    "localhost", 
    "127.0.0.1",
    "gestionstock-production.up.railway.app",  # Garder pour transition
    ".railway.app"
]

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=config("DATABASE_URL", default="postgresql://postgres:postgres@localhost:5432/gestion_stock"),
        conn_max_age=600,
        ssl_require=False if DEBUG else True,
    )
}

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config("CLOUDINARY_STORAGE_CLOUD_NAME", default=""),
    'API_KEY': config("CLOUDINARY_STORAGE_API_KEY", default=""),
    'API_SECRET': config("CLOUDINARY_STORAGE_API_SECRET", default=""),
}

# Application definition
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'authentification',
    'achats',
    'parametres',
    'produits',
    'rapports',
    'ventes',
    'corsheaders',
    'django_filters',
    'depenses',
    'transfert',
    'import_export',
    'notes',
    'cloudinary',
    'cloudinary_storage',
    'common',
    'django_redis',
    'debug_toolbar',
    'channels',
    'chat',
    'stats',
    'inventaire',
]

# ✅ FIX: Conditional Redis configuration - Use local memory cache for development
if DEBUG:
    # Development: Use local memory cache (no Redis required)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Use database for sessions
else:
    # Production: Use Redis
    REDIS_HOST = 'junction.proxy.rlwy.net'
    REDIS_PORT = 41907
    REDIS_PASSWORD = 'dVZwODtckOEHIVQHTZQQjRzMgqfFzaAW'
    
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 50,
                    'timeout': 20,
                },
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'RETRY_ON_TIMEOUT': True,
                'MAX_CONNECTIONS': 1000,
            },
            'KEY_PREFIX': 'gestion_stock',
            'TIMEOUT': 300,
        }
    }
    
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"],
            },
        },
    }
    
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'

ASGI_APPLICATION = "gestion_stock.asgi.application"

AUTH_USER_MODEL = 'authentification.CustomUser'

# settings.py - Add these CORS settings

# ✅ Fix CORS - Add all necessary headers
CORS_ALLOWED_ORIGINS = [
    "https://darlokman.netlify.app",
    "http://localhost:3000", 
    "http://127.0.0.1:3000",
    "https://darlokmanfront-production.up.railway.app",
    "https://darlokman.com",
    "https://www.darlokman.com",
]

CSRF_TRUSTED_ORIGINS = [
    'https://darlokman.com',
    'https://www.darlokman.com',
    'https://gestionstock-production.up.railway.app',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    "https://darlokman.netlify.app",
    "https://darlokmanfront-production.up.railway.app",
]

CORS_ALLOW_CREDENTIALS = True

# Allow all headers and methods for development
CORS_ALLOW_ALL_HEADERS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'cache-control',
    'pragma',
    'x-custom-header',
]

# Add CORS preflight max age
CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours

# For development, allow all origins
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True
import cloudinary
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

cloudinary.config( 
    cloud_name = CLOUDINARY_STORAGE['CLOUD_NAME'], 
    api_key = CLOUDINARY_STORAGE['API_KEY'], 
    api_secret = CLOUDINARY_STORAGE['API_SECRET'],
    secure=True
)

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',  
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'common.middleware.CacheInvalidationMiddleware',
    'common.middleware.PerformanceMiddleware',
]

# Only add cache middleware in production
if not DEBUG:
    MIDDLEWARE.insert(1, 'django.middleware.cache.UpdateCacheMiddleware')
    MIDDLEWARE.append('django.middleware.cache.FetchFromCacheMiddleware')

CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'gestion_stock'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter'
    ],
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20, 
}

ROOT_URLCONF = 'gestion_stock.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

template_path = "gestion_stock/templates_word"

WSGI_APPLICATION = 'gestion_stock.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Algiers'
USE_TZ = True
USE_I18N = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# Authentication settings
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Backblaze B2 Configuration (only if needed)
# B2_ACCOUNT_ID = "3677f4f8e220"
# B2_APPLICATION_KEY = "0037af877052a9cb3d985739482953dfdefefe2fa8"
# B2_BUCKET_NAME = "darlokman"

# File upload settings
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB