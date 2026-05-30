"""
Nova Capital Group - Finances Models
"""
from django.db import models
from django.conf import settings
import uuid


class Transaction(models.Model):
    """Financial transaction (deposit, withdrawal, fee)."""
    
    TRANSACTION_TYPES = [
        ('deposit', 'Depósito'),
        ('withdrawal', 'Retiro'),
        ('fee', 'Comisión'),
        ('bonus', 'Bono'),
        ('transfer', 'Transferencia'),
        ('trade_buy', 'Compra'),
        ('trade_sell', 'Venta'),
    ]
    
    STATUS = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
        ('reversed', 'Revertido'),
    ]
    
    PAYMENT_METHODS = [
        ('bank_transfer', 'Transferencia Bancaria'),
        ('credit_card', 'Tarjeta de Crédito'),
        ('debit_card', 'Tarjeta de Débito'),
        ('crypto', 'Criptomoneda'),
        ('paypal', 'PayPal'),
        ('internal', 'Interno'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default='internal')
    reference = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    balance_before = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    balance_after = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Transacción'
        verbose_name_plural = 'Transacciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.transaction_type} ${self.amount} ({self.status})"

    @property
    def is_credit(self):
        return self.transaction_type in ['deposit', 'bonus', 'trade_sell']

    @property
    def is_debit(self):
        return self.transaction_type in ['withdrawal', 'fee', 'trade_buy']


class BankAccount(models.Model):
    """User's linked bank account for withdrawals."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=100)
    account_holder = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    routing_number = models.CharField(max_length=50, blank=True)
    iban = models.CharField(max_length=50, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)
    currency = models.CharField(max_length=10, default='USD')
    is_verified = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cuenta Bancaria'
        verbose_name_plural = 'Cuentas Bancarias'

    def __str__(self):
        return f"{self.user.email} - {self.bank_name} ****{self.account_number[-4:]}"
