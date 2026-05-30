"""
Nova Capital Group - Accounts Views
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from .models import User, ActivityLog, KYCDocument
from .forms import RegisterForm, ProfileUpdateForm, PasswordChangeForm
import logging

logger = logging.getLogger('apps')


def log_activity(user, action, request, description='', metadata=None):
    """Helper to log user activity."""
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    if ',' in ip:
        ip = ip.split(',')[0].strip()
    ActivityLog.objects.create(
        user=user,
        action=action,
        description=description,
        ip_address=ip or None,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        metadata=metadata or {}
    )


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
            
            # Send verification email
            try:
                verify_url = request.build_absolute_uri(f'/accounts/verify-email/{token}/')
                send_mail(
                    'Verifica tu cuenta - Nova Capital Group',
                    f'Hola {user.first_name},\n\nVerifica tu cuenta haciendo clic en: {verify_url}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
            except Exception as e:
                logger.error(f"Error sending verification email: {e}")
            
            log_activity(user, 'login', request, 'Registro de nueva cuenta')
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'¡Bienvenido a Nova Capital Group, {user.first_name}! Verifica tu correo electrónico.')
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
                user=request.user,
                document_type=doc_type,
                document_file=doc_file
            )
            messages.success(request, 'Documento enviado para revisión.')
            return redirect('accounts:profile')
    return redirect('accounts:profile')
