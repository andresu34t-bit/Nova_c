import os
import sys
from django.core.wsgi import get_wsgi_application

# Forzar settings de producción si no está definido
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

application = get_wsgi_application()
