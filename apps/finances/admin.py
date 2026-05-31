"""
Nova Capital Group - Finances Admin
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Transaction, BankAccount


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'type_display', 'amount_display', 'status_badge',
                    'payment_method', 'balance_after_display', 'created_at']
    list_filter = ['transaction_type', 'status', 'payment_method', 'created_at']
    search_fields = ['user__email', 'description', 'reference']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'user', 'balance_before', 'balance_after']
    list_per_page = 50
    date_hierarchy = 'created_at'
    actions = ['mark_completed', 'mark_failed']

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/accounts/user/{}/change/" style="color:#3385FF;">{}</a>',
            obj.user.pk, obj.user.email
        )
    user_link.short_description = "Usuario"

    def type_display(self, obj):
        icons = {
            'deposit': '📥', 'withdrawal': '📤',
            'trade_buy': '▲', 'trade_sell': '▼', 'fee': '%'
        }
        colors = {
            'deposit': '#00C896', 'withdrawal': '#FFB800',
            'trade_buy': '#0066FF', 'trade_sell': '#FF3B5C', 'fee': '#7A8BA8'
        }
        icon = icons.get(obj.transaction_type, '·')
        color = colors.get(obj.transaction_type, '#7A8BA8')
        return format_html(
            '<span style="color:{};font-weight:600;">{} {}</span>',
            color, icon, obj.get_transaction_type_display()
        )
    type_display.short_description = "Tipo"

    def amount_display(self, obj):
        is_credit = obj.transaction_type in ['deposit', 'trade_sell']
        color = '#00C896' if is_credit else '#FF3B5C'
        sign = '+' if is_credit else '-'
        return format_html(
            '<strong style="color:{};font-family:monospace;">{}{:,.2f}</strong>',
            color, sign, float(obj.amount)
        )
    amount_display.short_description = "Monto"

    def status_badge(self, obj):
        colors = {
            'completed': '#00C896', 'pending': '#FFB800',
            'processing': '#0066FF', 'failed': '#FF3B5C', 'cancelled': '#7A8BA8'
        }
        color = colors.get(obj.status, '#7A8BA8')
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Estado"

    def balance_after_display(self, obj):
        if obj.balance_after:
            return format_html(
                '<span style="font-family:monospace;">${:,.2f}</span>',
                float(obj.balance_after)
            )
        return '—'
    balance_after_display.short_description = "Saldo Después"

    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'{updated} transacción(es) marcada(s) como completada(s).')
    mark_completed.short_description = "✓ Marcar como completadas"

    def mark_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, f'{updated} transacción(es) marcada(s) como fallidas.')
    mark_failed.short_description = "✗ Marcar como fallidas"


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'bank_name', 'account_holder', 'currency', 'verified_badge', 'is_primary']
    list_filter = ['is_verified', 'is_primary', 'currency']
    search_fields = ['user__email', 'bank_name', 'account_holder']

    def verified_badge(self, obj):
        if obj.is_verified:
            return format_html('<span style="color:#00C896;font-weight:600;">✓ Verificada</span>')
        return format_html('<span style="color:#FFB800;">Pendiente</span>')
    verified_badge.short_description = "Verificación"
