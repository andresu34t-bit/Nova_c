from .base import *
import dj_database_url
from decouple import config

DEBUG = False

# Base de datos — usa DATABASE_URL de Render
DATABASE_URL = config('DATABASE_URL', default='')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    # Fallback SQLite si no hay DATABASE_URL (no recomendado en producción)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Seguridad
SECURE_SSL_REDIRECT = False  # Render maneja HTTPS en el proxy, no necesitamos redirigir
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False  # Necesario para fetch() con CSRF en JS

# Hosts permitidos — acepta onrender.com, railway.app y cualquier host configurado
_allowed = config('ALLOWED_HOSTS', default='.onrender.com,.railway.app,.up.railway.app')
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(',')]
# Siempre incluir localhost para health checks
if 'localhost' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS += ['localhost', '127.0.0.1']

# Cache en memoria
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Logging solo a consola en Render
import sys
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'apps':   {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
