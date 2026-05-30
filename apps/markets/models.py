"""
Nova Capital Group - Markets Models
"""
from django.db import models


class MarketData(models.Model):
    """Cached market data from external APIs."""
    
    symbol = models.CharField(max_length=20)
    asset_type = models.CharField(max_length=20)
    data = models.JSONField(default=dict)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['symbol', 'asset_type']
        verbose_name = 'Dato de Mercado'
        verbose_name_plural = 'Datos de Mercado'

    def __str__(self):
        return f"{self.symbol} ({self.asset_type})"


class EconomicEvent(models.Model):
    """Economic calendar events."""
    
    IMPACT_LEVELS = [
        ('low', 'Bajo'),
        ('medium', 'Medio'),
        ('high', 'Alto'),
    ]

    title = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    currency = models.CharField(max_length=10)
    impact = models.CharField(max_length=10, choices=IMPACT_LEVELS)
    event_date = models.DateTimeField()
    actual = models.CharField(max_length=50, blank=True)
    forecast = models.CharField(max_length=50, blank=True)
    previous = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento Económico'
        verbose_name_plural = 'Eventos Económicos'
        ordering = ['event_date']

    def __str__(self):
        return f"{self.title} - {self.event_date}"
