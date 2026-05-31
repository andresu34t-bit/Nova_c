"""
Nova Capital Group - Script para crear superusuario admin
Ejecutar: python create_admin.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

email    = 'admin@novacapital.com'
password = 'Admin2024Nova!'

if User.objects.filter(email=email).exists():
    admin = User.objects.get(email=email)
    admin.is_staff     = True
    admin.is_superuser = True
    admin.is_active    = True
    admin.set_password(password)
    admin.save()
    print(f"✓ Admin actualizado: {email}")
else:
    admin = User.objects.create_superuser(
        username='admin',
        email=email,
        password=password,
        first_name='Admin',
        last_name='Nova Capital',
        is_staff=True,
        is_superuser=True,
    )
    print(f"✓ Admin creado: {email}")

print(f"  Email:    {email}")
print(f"  Password: {password}")
print(f"  Admin URL: /admin/")
