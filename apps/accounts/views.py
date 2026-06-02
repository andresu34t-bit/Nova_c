"""
Nova Capital Group - Accounts Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.conf import settings
from django.http import JsonResponse
from datetime import timedelta
from .models import User, ActivityLog, KYCDocument
from .forms import RegisterForm, ProfileUpdateForm, PasswordChangeForm
from .emails import (
    send_welcome_email, send_verification_email,
    send_password_reset_email
)
import logging

logger = logging.getLogger('apps')


def log_activity(user, action, request, description='', metadata=None):
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    if ',' in ip:
        ip = ip.split(',')[0].strip()
    ActivityLog.objects.create(
        user=user, action=action, description=description,
        ip_address=ip or None,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        metadata=metadata or {}
    )


# ── REGISTRO ──────────────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            token = get_random_string(64)
            user.email_verification_token = token
            user.email_verification_sent_at = timezone.now()
            user.save()

            verify_url = request.build_absolute_uri(f'/accounts/verify-email/{token}/')
            send_verification_email(user, verify_url)
            send_welcome_email(user)

            log_activity(user, 'login', request, 'Registro de nueva cuenta')
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'¡Bienvenido a Nova Capital Group, {user.first_name}! Revisa tu correo para verificar tu cuenta.')
            return redirect('dashboard:index')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def verify_email(request, token):
    try:
        user = User.objects.get(email_verification_token=token)
        user.email_verified = True
        user.email_verification_token = ''
        user.save()
        log_activity(user, 'email_verified', request, 'Email verificado exitosamente')
        messages.success(request, '¡Tu correo electrónico ha sido verificado exitosamente!')
    except User.DoesNotExist:
        messages.error(request, 'Token de verificación inválido o expirado.')
    return redirect('dashboard:index')


def logout_view(request):
    if request.user.is_authenticated:
        log_activity(request.user, 'logout', request, 'Cierre de sesión')
        logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('core:home')


# ── RECUPERACIÓN DE CONTRASEÑA ─────────────────────────────────
def forgot_password_view(request):
    """Solicitar recuperación de contraseña."""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        try:
            user = User.objects.get(email=email)
            token = get_random_string(64)
            user.email_verification_token = token
            user.email_verification_sent_at = timezone.now()
            user.save(update_fields=['email_verification_token', 'email_verification_sent_at'])

            reset_url = request.build_absolute_uri(f'/accounts/reset-password/{token}/')
            send_password_reset_email(user, reset_url)
            log_activity(user, 'password_change', request, 'Solicitud de recuperación de contraseña')
        except User.DoesNotExist:
            pass  # No revelar si el email existe

        messages.success(request, 'Si ese correo está registrado, recibirás un enlace para restablecer tu contraseña.')
        return redirect('accounts:forgot_password')

    return render(request, 'accounts/forgot_password.html')


def reset_password_view(request, token):
    """Restablecer contraseña con token."""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    # Verificar token válido y no expirado (1 hora)
    try:
        user = User.objects.get(email_verification_token=token)
        if user.email_verification_sent_at:
            expiry = user.email_verification_sent_at + timedelta(hours=1)
            if timezone.now() > expiry:
                messages.error(request, 'El enlace ha expirado. Solicita uno nuevo.')
                return redirect('accounts:forgot_password')
    except User.DoesNotExist:
        messages.error(request, 'Enlace inválido o ya utilizado.')
        return redirect('accounts:forgot_password')

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if len(new_password) < 10:
            messages.error(request, 'La contraseña debe tener al menos 10 caracteres.')
        elif new_password != confirm_password:
            messages.error(request, 'Las contraseñas no coinciden.')
        else:
            user.set_password(new_password)
            user.email_verification_token = ''
            user.save()
            log_activity(user, 'password_change', request, 'Contraseña restablecida via email')
            messages.success(request, '¡Contraseña restablecida exitosamente! Ya puedes iniciar sesión.')
            return redirect('two_factor:login')

    return render(request, 'accounts/reset_password.html', {'token': token})


# ── PERFIL ─────────────────────────────────────────────────────
@login_required
def profile_view(request):
    user = request.user
    activity_logs = ActivityLog.objects.filter(user=user).order_by('-created_at')[:20]
    kyc_docs = KYCDocument.objects.filter(user=user)

    context = {
        'user': user,
        'activity_logs': activity_logs,
        'kyc_docs': kyc_docs,
        'portfolio_value': user.get_portfolio_value(),
        'total_pnl': user.get_total_pnl(),
        'total_deposited': float(user.total_deposited),
        'total_withdrawn': float(user.total_withdrawn),
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_update_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            log_activity(request.user, 'profile_update', request, 'Perfil actualizado')
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile_update.html', {'form': form})


@login_required
def security_view(request):
    activity_logs = ActivityLog.objects.filter(user=request.user).order_by('-created_at')[:50]
    return render(request, 'accounts/security.html', {
        'activity_logs': activity_logs,
        'user': request.user,
    })


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            if not user.check_password(form.cleaned_data['current_password']):
                messages.error(request, 'La contraseña actual es incorrecta.')
            else:
                user.set_password(form.cleaned_data['new_password'])
                user.save()
                update_session_auth_hash(request, user)
                log_activity(user, 'password_change', request, 'Contraseña cambiada')
                messages.success(request, 'Contraseña actualizada correctamente.')
                return redirect('accounts:security')
    else:
        form = PasswordChangeForm()
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def upload_kyc_view(request):
    if request.method == 'POST':
        doc_type = request.POST.get('document_type')
        doc_file = request.FILES.get('document_file')
        if doc_type and doc_file:
            KYCDocument.objects.create(
                user=request.user, document_type=doc_type, document_file=doc_file
            )
            messages.success(request, 'Documento enviado para revisión.')
    return redirect('accounts:profile')


# ── REENVIAR VERIFICACIÓN ──────────────────────────────────────
@login_required
def resend_verification_view(request):
    user = request.user
    if user.email_verified:
        messages.info(request, 'Tu email ya está verificado.')
        return redirect('accounts:security')

    token = get_random_string(64)
    user.email_verification_token = token
    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=['email_verification_token', 'email_verification_sent_at'])

    verify_url = request.build_absolute_uri(f'/accounts/verify-email/{token}/')
    send_verification_email(user, verify_url)
    messages.success(request, 'Email de verificación reenviado. Revisa tu bandeja de entrada.')
    return redirect('accounts:security')


# ── REDIRECT INTELIGENTE POST-LOGIN ───────────────────────────
@login_required
def login_redirect_view(request):
    """
    Redirige al usuario al panel correcto según su tipo de cuenta.
    - Admin / Staff  → Panel de Administración
    - Usuario normal → Dashboard de usuario
    """
    if request.user.is_staff or request.user.is_superuser:
        return redirect('dashboard:admin_panel')
    return redirect('dashboard:index')
