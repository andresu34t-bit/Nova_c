from django.contrib import admin
from .models import MarketData, EconomicEvent


@admin.register(MarketData)
class MarketDataAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'asset_type', 'last_updated']
    list_filter = ['asset_type']
    search_fields = ['symbol']


@admin.register(EconomicEvent)
class EconomicEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'country', 'currency', 'impact', 'event_date']
    list_filter = ['impact', 'country']
    search_fields = ['title', 'country']
    ordering = ['event_date']
