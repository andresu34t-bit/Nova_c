from .base import *

DEBUG = True

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

INTERNAL_IPS = ['127.0.0.1']
