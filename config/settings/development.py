from .base import *
from decouple import config as env_config

DEBUG = True

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# -------------------------------------------------------
# BASE DE DATOS: usa PostgreSQL si DB_PASSWORD está en .env
# Si no, usa SQLite para desarrollo rápido sin configuración
# -------------------------------------------------------
_db_password = env_config('DB_PASSWORD', default='')
_use_sqlite = env_config('USE_SQLITE', default='False', cast=bool)

if _use_sqlite or not _db_password:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db_dev.sqlite3',
        }
    }
    print("\n[WARNING] Usando SQLite para desarrollo. Para usar PostgreSQL, configura DB_PASSWORD en .env\n")
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env_config('DB_NAME', default='nova_capital_db'),
            'USER': env_config('DB_USER', default='postgres'),
            'PASSWORD': _db_password,
            'HOST': env_config('DB_HOST', default='localhost'),
            'PORT': env_config('DB_PORT', default='5432'),
        }
    }

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

INTERNAL_IPS = ['127.0.0.1']

# Email en consola para desarrollo
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
