#!/usr/bin/env bash
# Nova Capital Group - Render Build Script
set -o errexit

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running migrations..."
python manage.py migrate --no-input

echo "==> Creating admin user..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
email = 'admin@novacapital.com'
password = 'Admin2024Nova!'
if not User.objects.filter(email=email).exists():
    u = User.objects.create_superuser(
        username='admin',
        email=email,
        password=password,
        first_name='Admin',
        last_name='Nova Capital',
    )
    u.email_verified = True
    u.account_type = 'institutional'
    u.verification_status = 'verified'
    u.save()
    print('Admin creado: ' + email)
else:
    print('Admin ya existe: ' + email)
"

echo "==> Build complete!"
