"""
Nova Capital Group - Trading Admin
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import Asset, Order, Watchlist


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'asset_type', 'price_display', 'change_display',
                    'volume_display', 'rank', 'is_active', 'last_updated']
    list_filter = ['asset_type', 'is_active']
    search_fields = ['symbol', 'name']
    ordering = ['rank', 'symbol']
    list_per_page = 50
    list_editable = ['is_active', 'rank']
    readonly_fields = ['last_updated']
    actions = ['activate_assets', 'deactivate_assets']

    fieldsets = (
        ('Identificación', {
            'fields': ('symbol', 'name', 'asset_type', 'rank', 'is_active', 'image_url')
        }),
        ('Precios', {
            'fields': ('current_price', 'price_change_24h', 'price_change_pct_24h',
                      'high_24h', 'low_24h')
        }),
        ('Mercado', {
            'fields': ('volume_24h', 'market_cap', 'last_updated')
        }),
    )

    def price_display(self, obj):
        return format_html(
            '<strong style="font-family:monospace;">${:,.4f}</strong>',
            obj.current_price
        )
    price_display.short_description = "Precio"
    price_display.admin_order_field = 'current_price'

    def change_display(self, obj):
        pct = float(obj.price_change_pct_24h or 0)
        color = '#00C896' if pct >= 0 else '#FF3B5C'
        sign = '+' if pct >= 0 else ''
        return format_html(
            '<span style="color:{};font-weight:600;">{}{:.2f}%</span>',
            color, sign, pct
        )
    change_display.short_description = "Cambio 24h"
    change_display.admin_order_field = 'price_change_pct_24h'

    def volume_display(self, obj):
        vol = float(obj.volume_24h or 0)
        if vol >= 1_000_000_000:
            return format_html('${:.1f}B', vol / 1_000_000_000)
        if vol >= 1_000_000:
            return format_html('${:.1f}M', vol / 1_000_000)
        return format_html('${:,.0f}', vol)
    volume_display.short_description = "Volumen 24h"

    def activate_assets(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} activo(s) activado(s).')
    activate_assets.short_description = "Activar activos"

    def deactivate_assets(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} activo(s) desactivado(s).')
    deactivate_assets.short_description = "Desactivar activos"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'asset_display', 'side_display', 'order_type',
                    'quantity_display', 'price_display', 'total_display', 'status_badge', 'created_at']
    list_filter = ['side', 'order_type', 'status', 'created_at', 'asset__asset_type']
    search_fields = ['user__email', 'user__first_name', 'asset__symbol']
    ordering = ['-created_at']
    readonly_fields = ['user', 'asset', 'side', 'order_type', 'quantity', 'price',
                       'filled_price', 'filled_quantity', 'total_value', 'fee',
                       'status', 'filled_at', 'created_at']
    list_per_page = 50
    date_hierarchy = 'created_at'

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/accounts/user/{}/change/" style="color:#3385FF;">{}</a>',
            obj.user.pk, obj.user.email
        )
    user_link.short_description = "Usuario"

    def asset_display(self, obj):
        return format_html('<strong style="color:#fff;">{}</strong>', obj.asset.symbol)
    asset_display.short_description = "Activo"

    def side_display(self, obj):
        if obj.side == 'buy':
            return format_html('<span style="color:#00C896;font-weight:700;">▲ COMPRA</span>')
        return format_html('<span style="color:#FF3B5C;font-weight:700;">▼ VENTA</span>')
    side_display.short_description = "Lado"

    def quantity_display(self, obj):
        return format_html('<span style="font-family:monospace;">{:.6f}</span>', float(obj.quantity))
    quantity_display.short_description = "Cantidad"

    def price_display(self, obj):
        return format_html('<span style="font-family:monospace;">${:,.4f}</span>', float(obj.filled_price or 0))
    price_display.short_description = "Precio"

    def total_display(self, obj):
        return format_html('<strong style="font-family:monospace;">${:,.2f}</strong>', float(obj.total_value))
    total_display.short_description = "Total"

    def status_badge(self, obj):
        colors = {
            'filled': '#00C896', 'pending': '#FFB800',
            'cancelled': '#7A8BA8', 'failed': '#FF3B5C'
        }
        color = colors.get(obj.status, '#7A8BA8')
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Estado"


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'asset', 'added_at']
    search_fields = ['user__email', 'asset__symbol']
    list_filter = ['asset__asset_type']
