"""
Nova Capital Group - Admin Panel
Panel administrativo completo con gestión de usuarios, inversiones y datos en tiempo real
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal
from .models import User, ActivityLog, KYCDocument


# ── Personalización del sitio admin ──
admin.site.site_header  = "Nova Capital Group · Panel Administrativo"
admin.site.site_title   = "Nova Capital Admin"
admin.site.index_title  = "Centro de Control"


# ── Inline: Posiciones del usuario ──
class PositionInline(admin.TabularInline):
    from apps.portfolio.models import Position
    model = Position
    extra = 0
    readonly_fields = ['asset', 'quantity', 'avg_buy_price', 'current_price',
                       'current_value_display', 'unrealized_pnl_display', 'is_open', 'opened_at']
    fields = ['asset', 'quantity', 'avg_buy_price', 'current_price',
              'current_value_display', 'unrealized_pnl_display', 'is_open']
    can_delete = False
    show_change_link = True
    verbose_name = "Posición"
    verbose_name_plural = "Posiciones Abiertas"

    def current_value_display(self, obj):
        val = obj.current_value
        return format_html('<strong style="color:#00C896;">${:,.2f}</strong>', val)
    current_value_display.short_description = "Valor Actual"

    def unrealized_pnl_display(self, obj):
        pnl = obj.unrealized_pnl
        color = '#00C896' if pnl >= 0 else '#FF3B5C'
        sign = '+' if pnl >= 0 else ''
        return format_html('<strong style="color:{};">{}{:,.2f}</strong>', color, sign, pnl)
    unrealized_pnl_display.short_description = "P&L No Realizado"

    def get_queryset(self, request):
        from apps.portfolio.models import Position
        return Position.objects.filter(is_open=True).select_related('asset')


# ── Inline: Órdenes recientes ──
class OrderInline(admin.TabularInline):
    from apps.trading.models import Order
    model = Order
    extra = 0
    readonly_fields = ['asset', 'side_display', 'quantity', 'filled_price', 'total_value', 'fee', 'status', 'created_at']
    fields = ['asset', 'side_display', 'quantity', 'filled_price', 'total_value', 'status', 'created_at']
    can_delete = False
    max_num = 10
    ordering = ['-created_at']
    verbose_name = "Orden"
    verbose_name_plural = "Últimas Órdenes"

    def side_display(self, obj):
        if obj.side == 'buy':
            return format_html('<span style="color:#00C896;font-weight:700;">▲ COMPRA</span>')
        return format_html('<span style="color:#FF3B5C;font-weight:700;">▼ VENTA</span>')
    side_display.short_description = "Lado"

    def get_queryset(self, request):
        from apps.trading.models import Order
        return Order.objects.select_related('asset').order_by('-created_at')


# ── Admin principal de Usuario ──
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = [
        'email_display', 'full_name', 'account_type_badge',
        'balance_display', 'portfolio_value_display', 'total_pnl_display',
        'verification_badge', 'status_badge', 'created_at'
    ]
    list_filter = [
        'account_type', 'verification_status', 'email_verified',
        'two_factor_enabled', 'is_active', 'is_suspended', 'created_at'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'phone', 'country']
    ordering = ['-created_at']
    readonly_fields = [
        'created_at', 'updated_at', 'last_login_ip', 'referral_code',
        'portfolio_summary', 'financial_summary'
    ]
    list_per_page = 25
    date_hierarchy = 'created_at'
    save_on_top = True

    fieldsets = (
        ('Acceso', {
            'fields': ('email', 'username', 'password')
        }),
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'phone', 'date_of_birth',
                      'country', 'city', 'address', 'avatar')
        }),
        ('Cuenta', {
            'fields': ('account_type', 'verification_status', 'email_verified', 'two_factor_enabled')
        }),
        ('💰 Finanzas', {
            'fields': ('balance', 'total_deposited', 'total_withdrawn', 'financial_summary'),
            'classes': ('wide',)
        }),
        ('📊 Resumen de Portafolio', {
            'fields': ('portfolio_summary',),
            'classes': ('wide',)
        }),
        ('Seguridad', {
            'fields': ('is_active', 'is_suspended', 'suspension_reason',
                      'last_login_ip', 'last_activity'),
            'classes': ('collapse',)
        }),
        ('Referidos', {
            'fields': ('referral_code', 'referred_by'),
            'classes': ('collapse',)
        }),
        ('Permisos', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name',
                      'password1', 'password2', 'account_type', 'balance'),
        }),
    )

    inlines = [PositionInline, OrderInline]

    # ── Columnas personalizadas ──
    def email_display(self, obj):
        return format_html(
            '<a href="mailto:{}" style="color:#3385FF;font-weight:600;">{}</a>',
            obj.email, obj.email
        )
    email_display.short_description = "Email"
    email_display.admin_order_field = 'email'

    def full_name(self, obj):
        return format_html('<strong>{}</strong>', obj.get_full_name() or '—')
    full_name.short_description = "Nombre"
    full_name.admin_order_field = 'first_name'

    def account_type_badge(self, obj):
        colors = {
            'standard': '#7A8BA8',
            'premium': '#FFB800',
            'institutional': '#0066FF',
        }
        color = colors.get(obj.account_type, '#7A8BA8')
        return format_html(
            '<span style="background:{}22;color:{};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, color, obj.get_account_type_display()
        )
    account_type_badge.short_description = "Tipo"
    account_type_badge.admin_order_field = 'account_type'

    def balance_display(self, obj):
        return format_html(
            '<strong style="color:#00C896;font-family:monospace;">${:,.2f}</strong>',
            obj.balance
        )
    balance_display.short_description = "Saldo"
    balance_display.admin_order_field = 'balance'

    def portfolio_value_display(self, obj):
        try:
            val = obj.get_portfolio_value()
            return format_html(
                '<span style="color:#fff;font-family:monospace;">${:,.2f}</span>', val
            )
        except Exception:
            return format_html('<span style="color:#7A8BA8;">—</span>')
    portfolio_value_display.short_description = "Portafolio"

    def total_pnl_display(self, obj):
        try:
            pnl = obj.get_total_pnl()
            color = '#00C896' if pnl >= 0 else '#FF3B5C'
            sign = '+' if pnl >= 0 else ''
            return format_html(
                '<strong style="color:{};font-family:monospace;">{}{:,.2f}</strong>',
                color, sign, pnl
            )
        except Exception:
            return format_html('<span style="color:#7A8BA8;">—</span>')
    total_pnl_display.short_description = "P&L"

    def verification_badge(self, obj):
        badges = {
            'verified':   ('<span style="color:#00C896;">✓ Verificado</span>', ),
            'pending':    ('<span style="color:#FFB800;">⏳ Pendiente</span>', ),
            'unverified': ('<span style="color:#7A8BA8;">○ Sin verificar</span>', ),
            'rejected':   ('<span style="color:#FF3B5C;">✗ Rechazado</span>', ),
        }
        html = badges.get(obj.verification_status, ('<span>—</span>',))[0]
        return format_html(html)
    verification_badge.short_description = "KYC"
    verification_badge.admin_order_field = 'verification_status'

    def status_badge(self, obj):
        if obj.is_suspended:
            return format_html('<span style="color:#FF3B5C;font-weight:700;">🔒 Suspendido</span>')
        if not obj.is_active:
            return format_html('<span style="color:#7A8BA8;">Inactivo</span>')
        return format_html('<span style="color:#00C896;">● Activo</span>')
    status_badge.short_description = "Estado"

    def financial_summary(self, obj):
        try:
            portfolio_val = obj.get_portfolio_value()
            total_assets = float(obj.balance) + portfolio_val
            pnl = obj.get_total_pnl()
            pnl_color = '#00C896' if pnl >= 0 else '#FF3B5C'
            return format_html('''
                <table style="border-collapse:collapse;width:100%;max-width:500px;">
                    <tr style="background:#0A1628;">
                        <td style="padding:8px 12px;color:#7A8BA8;font-size:12px;">Saldo disponible</td>
                        <td style="padding:8px 12px;color:#00C896;font-weight:700;font-family:monospace;">${:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 12px;color:#7A8BA8;font-size:12px;">Valor portafolio</td>
                        <td style="padding:8px 12px;color:#fff;font-weight:700;font-family:monospace;">${:,.2f}</td>
                    </tr>
                    <tr style="background:#0A1628;">
                        <td style="padding:8px 12px;color:#7A8BA8;font-size:12px;">Activos totales</td>
                        <td style="padding:8px 12px;color:#fff;font-weight:700;font-family:monospace;">${:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 12px;color:#7A8BA8;font-size:12px;">P&L no realizado</td>
                        <td style="padding:8px 12px;font-weight:700;font-family:monospace;color:{};">${:,.2f}</td>
                    </tr>
                    <tr style="background:#0A1628;">
                        <td style="padding:8px 12px;color:#7A8BA8;font-size:12px;">Total depositado</td>
                        <td style="padding:8px 12px;color:#fff;font-family:monospace;">${:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 12px;color:#7A8BA8;font-size:12px;">Total retirado</td>
                        <td style="padding:8px 12px;color:#FF3B5C;font-family:monospace;">${:,.2f}</td>
                    </tr>
                </table>
            ''',
                float(obj.balance), portfolio_val, total_assets,
                pnl_color, pnl,
                float(obj.total_deposited), float(obj.total_withdrawn)
            )
        except Exception as e:
            return format_html('<span style="color:#FF3B5C;">Error: {}</span>', str(e))
    financial_summary.short_description = "Resumen Financiero"

    def portfolio_summary(self, obj):
        try:
            from apps.portfolio.models import Position
            from apps.trading.models import Order
            positions = Position.objects.filter(user=obj, is_open=True).select_related('asset')
            orders_count = Order.objects.filter(user=obj).count()
            if not positions:
                return format_html('<span style="color:#7A8BA8;">Sin posiciones abiertas</span>')
            rows = ''
            for pos in positions:
                pnl = pos.unrealized_pnl
                pnl_color = '#00C896' if pnl >= 0 else '#FF3B5C'
                sign = '+' if pnl >= 0 else ''
                rows += f'''
                    <tr>
                        <td style="padding:6px 12px;font-weight:700;color:#fff;">{pos.asset.symbol}</td>
                        <td style="padding:6px 12px;font-family:monospace;color:#E8EDF5;">{float(pos.quantity):.4f}</td>
                        <td style="padding:6px 12px;font-family:monospace;color:#E8EDF5;">${float(pos.avg_buy_price):,.4f}</td>
                        <td style="padding:6px 12px;font-family:monospace;color:#E8EDF5;">${float(pos.current_price):,.4f}</td>
                        <td style="padding:6px 12px;font-family:monospace;color:#00C896;font-weight:700;">${pos.current_value:,.2f}</td>
                        <td style="padding:6px 12px;font-family:monospace;color:{pnl_color};font-weight:700;">{sign}${pnl:,.2f}</td>
                    </tr>
                '''
            return format_html('''
                <div style="margin-bottom:8px;color:#7A8BA8;font-size:12px;">
                    {} posiciones abiertas · {} órdenes totales
                </div>
                <table style="border-collapse:collapse;width:100%;max-width:700px;font-size:12px;">
                    <thead>
                        <tr style="background:#0A1628;">
                            <th style="padding:6px 12px;text-align:left;color:#7A8BA8;">Activo</th>
                            <th style="padding:6px 12px;text-align:left;color:#7A8BA8;">Cantidad</th>
                            <th style="padding:6px 12px;text-align:left;color:#7A8BA8;">Precio Entrada</th>
                            <th style="padding:6px 12px;text-align:left;color:#7A8BA8;">Precio Actual</th>
                            <th style="padding:6px 12px;text-align:left;color:#7A8BA8;">Valor</th>
                            <th style="padding:6px 12px;text-align:left;color:#7A8BA8;">P&L</th>
                        </tr>
                    </thead>
                    <tbody>{}</tbody>
                </table>
            ''', positions.count(), orders_count, format_html(rows))
        except Exception as e:
            return format_html('<span style="color:#FF3B5C;">Error: {}</span>', str(e))
    portfolio_summary.short_description = "Portafolio Detallado"

    # ── Acciones masivas ──
    actions = [
        'activate_users', 'suspend_users', 'verify_users',
        'set_premium', 'set_standard', 'add_bonus_balance'
    ]

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True, is_suspended=False)
        self.message_user(request, f'{updated} usuario(s) activado(s).', messages.SUCCESS)
    activate_users.short_description = "✓ Activar usuarios seleccionados"

    def suspend_users(self, request, queryset):
        updated = queryset.update(is_suspended=True)
        self.message_user(request, f'{updated} usuario(s) suspendido(s).', messages.WARNING)
    suspend_users.short_description = "🔒 Suspender usuarios seleccionados"

    def verify_users(self, request, queryset):
        updated = queryset.update(verification_status='verified', email_verified=True)
        self.message_user(request, f'{updated} usuario(s) verificado(s).', messages.SUCCESS)
    verify_users.short_description = "✓ Verificar KYC de usuarios seleccionados"

    def set_premium(self, request, queryset):
        updated = queryset.update(account_type='premium')
        self.message_user(request, f'{updated} usuario(s) cambiado(s) a Premium.', messages.SUCCESS)
    set_premium.short_description = "⭐ Cambiar a cuenta Premium"

    def set_standard(self, request, queryset):
        updated = queryset.update(account_type='standard')
        self.message_user(request, f'{updated} usuario(s) cambiado(s) a Estándar.', messages.SUCCESS)
    set_standard.short_description = "Cambiar a cuenta Estándar"

    def add_bonus_balance(self, request, queryset):
        bonus = Decimal('1000.00')
        for user in queryset:
            user.balance = user.balance + bonus
            user.save(update_fields=['balance'])
        self.message_user(
            request,
            f'Se agregaron ${bonus:,.2f} de bono a {queryset.count()} usuario(s).',
            messages.SUCCESS
        )
    add_bonus_balance.short_description = "💰 Agregar $1,000 de bono"


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'action_badge', 'description_short', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__email', 'ip_address', 'description']
    readonly_fields = ['user', 'action', 'description', 'ip_address', 'user_agent', 'created_at']
    ordering = ['-created_at']
    list_per_page = 50
    date_hierarchy = 'created_at'

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/accounts/user/{}/change/" style="color:#3385FF;">{}</a>',
            obj.user.pk, obj.user.email
        )
    user_link.short_description = "Usuario"

    def action_badge(self, obj):
        colors = {
            'login': '#0066FF', 'logout': '#7A8BA8',
            'login_failed': '#FF3B5C', 'suspicious': '#FF3B5C',
            'trade': '#00C896', 'deposit': '#00C896',
            'withdrawal': '#FFB800', 'password_change': '#FFB800',
        }
        color = colors.get(obj.action, '#7A8BA8')
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            color, obj.get_action_display()
        )
    action_badge.short_description = "Acción"

    def description_short(self, obj):
        desc = obj.description or '—'
        return desc[:60] + '...' if len(desc) > 60 else desc
    description_short.short_description = "Descripción"


@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'document_type', 'status_badge', 'uploaded_at', 'reviewed_at', 'actions_display']
    list_filter = ['document_type', 'status', 'uploaded_at']
    search_fields = ['user__email']
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at']
    actions = ['approve_documents', 'reject_documents']

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/accounts/user/{}/change/" style="color:#3385FF;">{}</a>',
            obj.user.pk, obj.user.email
        )
    user_link.short_description = "Usuario"

    def status_badge(self, obj):
        colors = {'pending': '#FFB800', 'approved': '#00C896', 'rejected': '#FF3B5C'}
        color = colors.get(obj.status, '#7A8BA8')
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Estado"

    def actions_display(self, obj):
        if obj.status == 'pending':
            return format_html(
                '<a href="/admin/accounts/kycdocument/{}/change/" style="color:#00C896;">Revisar</a>',
                obj.pk
            )
        return '—'
    actions_display.short_description = "Acción"

    def approve_documents(self, request, queryset):
        updated = queryset.update(status='approved', reviewed_at=timezone.now())
        # Verificar usuarios
        for doc in queryset:
            doc.user.verification_status = 'verified'
            doc.user.save(update_fields=['verification_status'])
        self.message_user(request, f'{updated} documento(s) aprobado(s).', messages.SUCCESS)
    approve_documents.short_description = "✓ Aprobar documentos seleccionados"

    def reject_documents(self, request, queryset):
        updated = queryset.update(status='rejected', reviewed_at=timezone.now())
        self.message_user(request, f'{updated} documento(s) rechazado(s).', messages.WARNING)
    reject_documents.short_description = "✗ Rechazar documentos seleccionados"
