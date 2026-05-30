"""
Nova Capital Group - Trading Models
"""
from django.db import models
from django.conf import settings
import uuid


class Asset(models.Model):
    """Financial asset (crypto, stock, forex, index)."""
    
    ASSET_TYPES = [
        ('crypto', 'Criptomoneda'),
        ('stock', 'Acción'),
        ('forex', 'Forex'),
        ('index', 'Índice'),
        ('commodity', 'Commodity'),
    ]

    symbol = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    price_change_24h = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    price_change_pct_24h = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    volume_24h = models.DecimalField(max_digits=30, decimal_places=2, default=0)
    market_cap = models.DecimalField(max_digits=30, decimal_places=2, default=0)
    high_24h = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    low_24h = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    image_url = models.URLField(blank=True)
    coingecko_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    rank = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Activo'
        verbose_name_plural = 'Activos'
        ordering = ['rank', 'symbol']

    def __str__(self):
        return f"{self.symbol} - {self.name}"

    @property
    def is_positive(self):
        return self.price_change_pct_24h >= 0


class Order(models.Model):
    """Trading order."""
    
    ORDER_TYPES = [
        ('market', 'Mercado'),
        ('limit', 'Límite'),
        ('stop', 'Stop'),
        ('stop_limit', 'Stop Límite'),
    ]
    
    SIDES = [
        ('buy', 'Compra'),
        ('sell', 'Venta'),
    ]
    
    STATUS = [
        ('pending', 'Pendiente'),
        ('filled', 'Ejecutada'),
        ('partially_filled', 'Parcialmente Ejecutada'),
        ('cancelled', 'Cancelada'),
        ('rejected', 'Rechazada'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='orders')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES, default='market')
    side = models.CharField(max_length=10, choices=SIDES)
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    filled_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    filled_quantity = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    fee = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    filled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.side.upper()} {self.quantity} {self.asset.symbol} @ {self.filled_price or self.price}"


class Watchlist(models.Model):
    """User watchlist for tracking assets."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watchlist')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    alert_price_high = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    alert_price_low = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)

    class Meta:
        verbose_name = 'Watchlist'
        unique_together = ['user', 'asset']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.email} - {self.asset.symbol}"
