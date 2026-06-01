"""
Nova Capital Group - Signals
Captura automática de logins para el historial de sesiones
"""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """Registrar inicio de sesión con IP y user agent."""
    try:
        from .models import ActivityLog
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        ua = request.META.get('HTTP_USER_AGENT', '')[:500]

        ActivityLog.objects.create(
            user=user,
            action='login',
            description='Inicio de sesión exitoso',
            ip_address=ip or None,
            user_agent=ua,
        )

        # Actualizar último login
        user.last_login_ip = ip or None
        user.last_activity = timezone.now()
        user.save(update_fields=['last_login_ip', 'last_activity'])
    except Exception:
        pass


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    """Registrar cierre de sesión."""
    if not user:
        return
    try:
        from .models import ActivityLog
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        ActivityLog.objects.create(
            user=user,
            action='logout',
            description='Cierre de sesión',
            ip_address=ip or None,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
    except Exception:
        pass


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    """Registrar intento fallido de login."""
    try:
        from .models import ActivityLog, User
        email = credentials.get('username', '') or credentials.get('email', '')
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        if ',' in ip:
            ip = ip.split(',')[0].strip()

        try:
            user = User.objects.get(email=email)
            ActivityLog.objects.create(
                user=user,
                action='login_failed',
                description=f'Intento fallido desde {ip}',
                ip_address=ip or None,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except User.DoesNotExist:
            pass
    except Exception:
        pass
