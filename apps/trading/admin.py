from django.contrib import admin
from .models import Asset, Order, Watchlist


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'asset_type', 'current_price', 'price_change_pct_24h', 'rank', 'is_active']
    list_filter = ['asset_type', 'is_active']
    search_fields = ['symbol', 'name']
    ordering = ['rank', 'symbol']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'asset', 'side', 'order_type', 'quantity', 'filled_price', 'status', 'created_at']
    list_filter = ['side', 'order_type', 'status']
    search_fields = ['user__email', 'asset__symbol']
    ordering = ['-created_at']


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'asset', 'added_at']
    search_fields = ['user__email', 'asset__symbol']
