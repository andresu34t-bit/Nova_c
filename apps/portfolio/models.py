"""
Nova Capital Group - Portfolio Models
"""
from django.db import models
from django.conf import settings
from apps.trading.models import Asset
import uuid


class Position(models.Model):
    """Open or closed trading position."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='positions')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='positions')
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    avg_buy_price = models.DecimalField(max_digits=20, decimal_places=8)
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    is_open = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    realized_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Posición'
        verbose_name_plural = 'Posiciones'
        ordering = ['-opened_at']

    def __str__(self):
        return f"{self.user.email} - {self.asset.symbol} x{self.quantity}"

    @property
    def cost_basis(self):
        return float(self.quantity) * float(self.avg_buy_price)

    @property
    def current_value(self):
        return float(self.quantity) * float(self.current_price)

    @property
    def unrealized_pnl(self):
        return self.current_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self):
        if self.cost_basis == 0:
            return 0
        return (self.unrealized_pnl / self.cost_basis) * 100


class PortfolioSnapshot(models.Model):
    """Daily snapshot of portfolio value for historical tracking."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portfolio_snapshots')
    total_value = models.DecimalField(max_digits=20, decimal_places=2)
    cash_balance = models.DecimalField(max_digits=20, decimal_places=2)
    total_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    snapshot_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Snapshot de Portafolio'
        verbose_name_plural = 'Snapshots de Portafolio'
        ordering = ['-snapshot_date']
        unique_together = ['user', 'snapshot_date']

    def __str__(self):
        return f"{self.user.email} - {self.snapshot_date} - ${self.total_value}"
