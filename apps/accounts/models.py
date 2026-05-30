"""
Nova Capital Group - Accounts Models
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class User(AbstractUser):
    """Custom user model with extended financial profile fields."""
    
    VERIFICATION_STATUS = [
        ('unverified', 'Sin Verificar'),
        ('pending', 'Pendiente'),
        ('verified', 'Verificado'),
        ('rejected', 'Rechazado'),
    ]
    
    ACCOUNT_TYPE = [
        ('standard', 'Estándar'),
        ('premium', 'Premium'),
        ('institutional', 'Institucional'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE, default='standard')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='unverified')
    
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    
    two_factor_enabled = models.BooleanField(default=False)
    
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    total_deposited = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    total_withdrawn = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.TextField(blank=True)
    
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_portfolio_value(self):
        from apps.portfolio.models import Position
        total = sum(p.current_value for p in self.positions.filter(is_open=True))
        return total

    def get_total_pnl(self):
        from apps.portfolio.models import Position
        total = sum(p.unrealized_pnl for p in self.positions.filter(is_open=True))
        return total

    def save(self, *args, **kwargs):
        if not self.referral_code:
            import random, string
            self.referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)


class ActivityLog(models.Model):
    """Log of all user activities for security and audit."""
    
    ACTION_TYPES = [
        ('login', 'Inicio de Sesión'),
        ('logout', 'Cierre de Sesión'),
        ('login_failed', 'Intento Fallido'),
        ('password_change', 'Cambio de Contraseña'),
        ('profile_update', 'Actualización de Perfil'),
        ('deposit', 'Depósito'),
        ('withdrawal', 'Retiro'),
        ('trade', 'Operación'),
        ('2fa_enabled', '2FA Activado'),
        ('2fa_disabled', '2FA Desactivado'),
        ('email_verified', 'Email Verificado'),
        ('suspicious', 'Actividad Sospechosa'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=30, choices=ACTION_TYPES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Registro de Actividad'
        verbose_name_plural = 'Registros de Actividad'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.created_at}"


class KYCDocument(models.Model):
    """Know Your Customer document verification."""
    
    DOC_TYPES = [
        ('passport', 'Pasaporte'),
        ('id_card', 'Cédula de Identidad'),
        ('drivers_license', 'Licencia de Conducir'),
        ('utility_bill', 'Factura de Servicios'),
        ('bank_statement', 'Estado de Cuenta Bancario'),
    ]
    
    STATUS = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kyc_documents')
    document_type = models.CharField(max_length=30, choices=DOC_TYPES)
    document_file = models.FileField(upload_to='kyc_documents/')
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    rejection_reason = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Documento KYC'
        verbose_name_plural = 'Documentos KYC'

    def __str__(self):
        return f"{self.user.email} - {self.document_type}"
