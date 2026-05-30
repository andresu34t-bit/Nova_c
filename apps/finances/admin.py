from django.contrib import admin
from .models import Transaction, BankAccount


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'currency', 'status', 'payment_method', 'created_at']
    list_filter = ['transaction_type', 'status', 'payment_method', 'currency']
    search_fields = ['user__email', 'reference', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'bank_name', 'account_holder', 'currency', 'is_verified', 'is_primary']
    list_filter = ['is_verified', 'is_primary', 'currency']
    search_fields = ['user__email', 'bank_name', 'account_holder']
