from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ActivityLog, KYCDocument


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'account_type', 'verification_status', 'balance', 'is_active', 'created_at']
    list_filter = ['account_type', 'verification_status', 'email_verified', 'is_active', 'is_suspended']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'last_login_ip', 'referral_code']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Perfil Financiero', {
            'fields': ('phone', 'date_of_birth', 'country', 'city', 'address', 'avatar',
                      'account_type', 'balance', 'total_deposited', 'total_withdrawn')
        }),
        ('Verificación', {
            'fields': ('email_verified', 'verification_status', 'two_factor_enabled')
        }),
        ('Seguridad', {
            'fields': ('last_login_ip', 'last_activity', 'is_suspended', 'suspension_reason')
        }),
        ('Referidos', {
            'fields': ('referral_code', 'referred_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__email', 'ip_address', 'description']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ['user', 'document_type', 'status', 'uploaded_at', 'reviewed_at']
    list_filter = ['document_type', 'status']
    search_fields = ['user__email']
    ordering = ['-uploaded_at']
