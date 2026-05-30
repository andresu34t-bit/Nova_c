from django.contrib import admin
from .models import Position, PortfolioSnapshot


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['user', 'asset', 'quantity', 'avg_buy_price', 'current_price', 'is_open', 'opened_at']
    list_filter = ['is_open', 'asset__asset_type']
    search_fields = ['user__email', 'asset__symbol']
    ordering = ['-opened_at']


@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_value', 'cash_balance', 'total_pnl', 'snapshot_date']
    ordering = ['-snapshot_date']
