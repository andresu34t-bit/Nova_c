"""
Nova Capital Group - Finances Views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import Transaction, BankAccount
import logging

logger = logging.getLogger('apps')


@login_required
def finances_view(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:50]
    bank_accounts = BankAccount.objects.filter(user=user)
    
    # Stats
    total_deposited = sum(float(t.amount) for t in transactions if t.transaction_type == 'deposit' and t.status == 'completed')
    total_withdrawn = sum(float(t.amount) for t in transactions if t.transaction_type == 'withdrawal' and t.status == 'completed')
    total_fees = sum(float(t.fee_amount) for t in transactions if t.status == 'completed')
    
    context = {
        'transactions': transactions,
        'bank_accounts': bank_accounts,
        'total_deposited': total_deposited,
        'total_withdrawn': total_withdrawn,
        'total_fees': total_fees,
        'balance': float(user.balance),
    }
    return render(request, 'finances/finances.html', context)


@login_required
def deposit_view(request):
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0')
        payment_method = request.POST.get('payment_method', 'bank_transfer')
        
        try:
            amount = float(amount_str)
            if amount <= 0:
                messages.error(request, 'El monto debe ser mayor a 0.')
                return redirect('finances:finances')
            if amount > 1000000:
                messages.error(request, 'El monto máximo por depósito es $1,000,000.')
                return redirect('finances:finances')
            
            user = request.user
            balance_before = float(user.balance)
            user.balance = balance_before + amount
            user.total_deposited = float(user.total_deposited) + amount
            user.save(update_fields=['balance', 'total_deposited'])
            
            Transaction.objects.create(
                user=user,
                transaction_type='deposit',
                amount=amount,
                status='completed',
                payment_method=payment_method,
                description=f'Depósito via {payment_method}',
                balance_before=balance_before,
                balance_after=float(user.balance),
                completed_at=timezone.now(),
            )
            
            messages.success(request, f'Depósito de ${amount:,.2f} USD procesado exitosamente.')
        except ValueError:
            messages.error(request, 'Monto inválido.')
        
        return redirect('finances:finances')
    
    return render(request, 'finances/deposit.html')


@login_required
def withdrawal_view(request):
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0')
        payment_method = request.POST.get('payment_method', 'bank_transfer')
        
        try:
            amount = float(amount_str)
            user = request.user
            
            if amount <= 0:
                messages.error(request, 'El monto debe ser mayor a 0.')
                return redirect('finances:finances')
            if amount > float(user.balance):
                messages.error(request, 'Saldo insuficiente.')
                return redirect('finances:finances')
            
            balance_before = float(user.balance)
            user.balance = balance_before - amount
            user.total_withdrawn = float(user.total_withdrawn) + amount
            user.save(update_fields=['balance', 'total_withdrawn'])
            
            Transaction.objects.create(
                user=user,
                transaction_type='withdrawal',
                amount=amount,
                status='processing',
                payment_method=payment_method,
                description=f'Retiro via {payment_method}',
                balance_before=balance_before,
                balance_after=float(user.balance),
            )
            
            messages.success(request, f'Solicitud de retiro de ${amount:,.2f} USD enviada. Procesamiento en 1-3 días hábiles.')
        except ValueError:
            messages.error(request, 'Monto inválido.')
        
        return redirect('finances:finances')
    
    return render(request, 'finances/withdrawal.html')


@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'finances/history.html', {'transactions': transactions})
