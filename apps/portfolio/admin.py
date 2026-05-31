"""
Nova Capital Group - Portfolio Admin
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Position, PortfolioSnapshot


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'asset_display', 'quantity_display', 'avg_price_display',
                    'current_price_display', 'value_display', 'pnl_display', 'is_open', 'opened_at']
    list_filter = ['is_open', 'asset__asset_type', 'opened_at']
    search_fields = ['user__email', 'asset__symbol']
    ordering = ['-opened_at']
    readonly_fields = ['user', 'asset', 'opened_at', 'closed_at']
    list_per_page = 50
    date_hierarchy = 'opened_at'

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/accounts/user/{}/change/" style="color:#3385FF;">{}</a>',
            obj.user.pk, obj.user.email
        )
    user_link.short_description = "Usuario"

    def asset_display(self, obj):
        return format_html('<strong style="color:#fff;">{}</strong>', obj.asset.symbol)
    asset_display.short_description = "Activo"

    def quantity_display(self, obj):
        return format_html('<span style="font-family:monospace;">{:.6f}</span>', float(obj.quantity))
    quantity_display.short_description = "Cantidad"

    def avg_price_display(self, obj):
        return format_html('<span style="font-family:monospace;">${:,.4f}</span>', float(obj.avg_buy_price))
    avg_price_display.short_description = "Precio Entrada"

    def current_price_display(self, obj):
        return format_html('<span style="font-family:monospace;">${:,.4f}</span>', float(obj.current_price))
    current_price_display.short_description = "Precio Actual"

    def value_display(self, obj):
        return format_html(
            '<strong style="color:#00C896;font-family:monospace;">${:,.2f}</strong>',
            obj.current_value
        )
    value_display.short_description = "Valor"

    def pnl_display(self, obj):
        pnl = obj.unrealized_pnl
        pct = obj.unrealized_pnl_pct
        color = '#00C896' if pnl >= 0 else '#FF3B5C'
        sign = '+' if pnl >= 0 else ''
        return format_html(
            '<span style="color:{};font-weight:700;">{}{:,.2f} ({}{:.1f}%)</span>',
            color, sign, pnl, sign, pct
        )
    pnl_display.short_description = "P&L"


@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_value_display', 'cash_display', 'pnl_display', 'snapshot_date']
    list_filter = ['snapshot_date']
    search_fields = ['user__email']
    ordering = ['-snapshot_date']
    date_hierarchy = 'snapshot_date'

    def total_value_display(self, obj):
        return format_html(
            '<strong style="font-family:monospace;">${:,.2f}</strong>', float(obj.total_value)
        )
    total_value_display.short_description = "Valor Total"

    def cash_display(self, obj):
        return format_html('${:,.2f}', float(obj.cash_balance))
    cash_display.short_description = "Efectivo"

    def pnl_display(self, obj):
        pnl = float(obj.total_pnl)
        color = '#00C896' if pnl >= 0 else '#FF3B5C'
        sign = '+' if pnl >= 0 else ''
        return format_html('<span style="color:{};">{}{:,.2f}</span>', color, sign, pnl)
    pnl_display.short_description = "P&L"
