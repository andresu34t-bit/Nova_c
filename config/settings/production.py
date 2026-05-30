from .base import *
import dj_database_url

DEBUG = False

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True,
    )
}

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False   # Necesario para fetch() con CSRF en JS

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Render agrega el host automáticamente via ALLOWED_HOSTS en render.yaml
# pero también lo forzamos aquí como fallback
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='.onrender.com').split(',')
