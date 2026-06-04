"""
Nova Capital Group - Finances Views
Depósitos instantáneos con soporte multi-moneda
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.models import Sum
from .models import Transaction, BankAccount
from apps.accounts.emails import (
    send_deposit_approved_email, send_deposit_rejected_email,
    send_withdrawal_approved_email
)
import logging

logger = logging.getLogger('apps')

# Tasas de cambio aproximadas a USD (se actualizan manualmente)
EXCHANGE_RATES = {
    'USD': 1.0,    'EUR': 0.92,  'GBP': 0.79,   'COP': 4100.0,
    'MXN': 17.2,   'ARS': 890.0, 'BRL': 5.0,    'CLP': 950.0,
    'PEN': 3.75,   'CAD': 1.36,  'AUD': 1.53,   'JPY': 149.0,
    'CHF': 0.90,   'BTC': 0.000015, 'ETH': 0.00026, 'USDT': 1.0,
}

DEPOSIT_LIMITS = {
    'standard':      10_000,
    'premium':      100_000,
    'institutional':      0,   # Sin límite
}


def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
def finances_view(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:50]
    bank_accounts = BankAccount.objects.filter(user=user)

    total_deposited = sum(
        float(t.amount) for t in transactions
        if t.transaction_type == 'deposit' and t.status == 'completed'
    )
    total_withdrawn = sum(
        float(t.amount) for t in transactions
        if t.transaction_type == 'withdrawal' and t.status == 'completed'
    )
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
    """
    Depósito instantáneo en modo simulación.
    Soporta múltiples monedas con conversión automática a USD.
    """
    if request.method == 'POST':
        amount_str     = request.POST.get('amount', '0')
        payment_method = request.POST.get('payment_method', 'bank_transfer')
        currency       = request.POST.get('currency', 'USD').upper()

        try:
            amount = float(amount_str)
            if amount < 0.01:
                messages.error(request, 'El monto mínimo de depósito es $0.01.')
                return redirect('finances:deposit')

            # Convertir a USD
            rate       = EXCHANGE_RATES.get(currency, 1.0)
            amount_usd = round(amount / rate, 2)

            if amount_usd > 1_000_000:
                messages.error(request, 'El monto máximo por depósito es $1,000,000 USD.')
                return redirect('finances:deposit')

            user = request.user

            # Verificar límite diario
            daily_limit = DEPOSIT_LIMITS.get(user.account_type, 10_000)
            if daily_limit > 0:
                today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                deposited_today = Transaction.objects.filter(
                    user=user, transaction_type='deposit',
                    status='completed', created_at__gte=today_start
                ).aggregate(total=Sum('amount'))['total'] or 0
                if float(deposited_today) + amount_usd > daily_limit:
                    remaining = max(0, daily_limit - float(deposited_today))
                    messages.error(request, f'Límite diario: ${daily_limit:,.0f} USD. Disponible hoy: ${remaining:,.2f} USD.')
                    return redirect('finances:deposit')

            # Acreditar saldo instantáneamente
            with db_transaction.atomic():
                balance_before = float(user.balance)
                user.balance = balance_before + amount_usd
                user.total_deposited = float(user.total_deposited) + amount_usd
                user.save(update_fields=['balance', 'total_deposited'])

                currency_display = f'{amount:,.2f} {currency}' if currency != 'USD' else f'${amount_usd:,.2f} USD'
                Transaction.objects.create(
                    user=user,
                    transaction_type='deposit',
                    amount=amount_usd,
                    currency='USD',
                    status='completed',
                    payment_method=payment_method,
                    description=f'Depósito {currency_display} via {payment_method}',
                    balance_before=balance_before,
                    balance_after=float(user.balance),
                    completed_at=timezone.now(),
                    metadata={
                        'original_amount':   amount,
                        'original_currency': currency,
                        'exchange_rate':     rate,
                        'amount_usd':        amount_usd,
                    }
                )

            if currency != 'USD':
                messages.success(request, f'Depósito de {amount:,.2f} {currency} (≈ ${amount_usd:,.2f} USD) procesado exitosamente.')
            else:
                messages.success(request, f'Depósito de ${amount_usd:,.2f} USD procesado exitosamente.')

            logger.info(f"Deposit: user={user.email} amount_usd={amount_usd} currency={currency}")

        except ValueError:
            messages.error(request, 'Monto inválido.')

        return redirect('finances:finances')

    return render(request, 'finances/deposit.html')


@login_required
def withdrawal_view(request):
    if request.method == 'POST':
        amount_str     = request.POST.get('amount', '0')
        payment_method = request.POST.get('payment_method', 'bank_transfer')
        reference      = request.POST.get('reference', '').strip()

        try:
            amount = float(amount_str)
            user   = request.user

            if amount < 1:
                messages.error(request, 'El monto mínimo de retiro es $1.00 USD.')
                return redirect('finances:withdrawal')
            if amount > float(user.balance):
                messages.error(request, f'Saldo insuficiente. Disponible: ${float(user.balance):,.2f}')
                return redirect('finances:withdrawal')

            # Construir metadata con los datos bancarios / cripto / paypal
            metadata = {'payment_method': payment_method}
            if payment_method == 'bank_transfer':
                metadata['bank_name']       = request.POST.get('bank_name', '').strip()
                metadata['account_holder']  = request.POST.get('account_holder', '').strip()
                metadata['account_number']  = request.POST.get('account_number', '').strip()
            elif payment_method == 'crypto':
                metadata['crypto_network']  = request.POST.get('crypto_network', '').strip()
                metadata['wallet_address']  = request.POST.get('wallet_address', '').strip()
            elif payment_method == 'paypal':
                metadata['paypal_email']    = request.POST.get('paypal_email', '').strip()
            elif payment_method == 'debit_card':
                metadata['card_last4']      = request.POST.get('card_last4', '').strip()

            if reference:
                metadata['user_reference'] = reference

            with db_transaction.atomic():
                balance_before = float(user.balance)
                user.balance   = round(balance_before - amount, 2)
                user.save(update_fields=['balance'])

                method_label = {
                    'bank_transfer': 'Transferencia Bancaria',
                    'crypto':        'Criptomoneda',
                    'paypal':        'PayPal',
                    'debit_card':    'Tarjeta de Débito',
                }.get(payment_method, payment_method)

                Transaction.objects.create(
                    user=user,
                    transaction_type='withdrawal',
                    amount=amount,
                    currency='USD',
                    status='processing',
                    payment_method=payment_method,
                    description=f'Retiro via {method_label}{" — " + reference if reference else ""}',
                    balance_before=balance_before,
                    balance_after=float(user.balance),
                    metadata=metadata,
                )

            logger.info(f"Withdrawal request: user={user.email} amount={amount} method={payment_method}")
            messages.success(
                request,
                f'✓ Solicitud de retiro de ${amount:,.2f} USD enviada correctamente. '
                f'Procesamiento en 1-3 días hábiles. Tu nuevo saldo es ${float(user.balance):,.2f} USD.'
            )

        except ValueError:
            messages.error(request, 'Monto inválido. Ingresa un número válido.')

        return redirect('finances:finances')

    return render(request, 'finances/withdrawal.html')


@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'finances/history.html', {'transactions': transactions})


# ══════════════════════════════════════════════════════════════
# PANEL ADMIN — Solo staff/superuser
# ══════════════════════════════════════════════════════════════

@login_required
@user_passes_test(is_admin)
def admin_transactions_view(request):
    pending_deposits    = Transaction.objects.filter(
        transaction_type='deposit', status='pending'
    ).select_related('user').order_by('-created_at')

    pending_withdrawals = Transaction.objects.filter(
        transaction_type='withdrawal', status='processing'
    ).select_related('user').order_by('-created_at')

    all_transactions = Transaction.objects.select_related('user').order_by('-created_at')[:100]

    context = {
        'pending_deposits':    pending_deposits,
        'pending_withdrawals': pending_withdrawals,
        'all_transactions':    all_transactions,
        'pending_count':       pending_deposits.count() + pending_withdrawals.count(),
    }
    return render(request, 'finances/admin_transactions.html', context)


@login_required
@user_passes_test(is_admin)
def approve_transaction(request, tx_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    tx = get_object_or_404(Transaction, id=tx_id)

    if tx.transaction_type == 'deposit' and tx.status == 'pending':
        with db_transaction.atomic():
            user = tx.user
            balance_before = float(user.balance)
            user.balance = balance_before + float(tx.amount)
            user.total_deposited = float(user.total_deposited) + float(tx.amount)
            user.save(update_fields=['balance', 'total_deposited'])

            tx.status = 'completed'
            tx.balance_before = balance_before
            tx.balance_after  = float(user.balance)
            tx.completed_at   = timezone.now()
            tx.metadata['approved_by'] = request.user.email
            tx.metadata['approved_at'] = timezone.now().isoformat()
            tx.save()

        send_deposit_approved_email(tx.user, float(tx.amount), tx.id)
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'user_{tx.user.id}',
                {
                    'type':        'deposit_approved',
                    'amount':      str(tx.amount),
                    'new_balance': str(tx.user.balance),
                    'message':     f'Tu depósito de ${float(tx.amount):,.2f} ha sido aprobado.',
                }
            )
        except Exception:
            pass

        return JsonResponse({
            'success': True,
            'message': f'Depósito de ${float(tx.amount):,.2f} aprobado para {tx.user.email}',
            'new_balance': float(tx.user.balance),
        })

    elif tx.transaction_type == 'withdrawal' and tx.status == 'processing':
        with db_transaction.atomic():
            tx.status = 'completed'
            tx.completed_at = timezone.now()
            tx.user.total_withdrawn = float(tx.user.total_withdrawn) + float(tx.amount)
            tx.user.save(update_fields=['total_withdrawn'])
            tx.metadata['approved_by'] = request.user.email
            tx.save()

        send_withdrawal_approved_email(tx.user, float(tx.amount), tx.id)
        return JsonResponse({
            'success': True,
            'message': f'Retiro de ${float(tx.amount):,.2f} aprobado para {tx.user.email}',
        })

    return JsonResponse({'error': 'Transacción no válida o ya procesada.'}, status=400)


@login_required
@user_passes_test(is_admin)
def reject_transaction(request, tx_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    tx     = get_object_or_404(Transaction, id=tx_id)
    reason = request.POST.get('reason', 'Rechazado por el administrador')

    if tx.transaction_type == 'deposit' and tx.status == 'pending':
        tx.status = 'failed'
        tx.metadata['rejected_by']     = request.user.email
        tx.metadata['rejection_reason'] = reason
        tx.save()
        send_deposit_rejected_email(tx.user, float(tx.amount), reason, tx.id)
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'user_{tx.user.id}',
                {
                    'type':    'deposit_rejected',
                    'amount':  str(tx.amount),
                    'reason':  reason,
                    'message': f'Tu depósito de ${float(tx.amount):,.2f} fue rechazado: {reason}',
                }
            )
        except Exception:
            pass
        return JsonResponse({'success': True, 'message': f'Depósito rechazado.'})

    elif tx.transaction_type == 'withdrawal' and tx.status == 'processing':
        with db_transaction.atomic():
            user = tx.user
            user.balance = float(user.balance) + float(tx.amount)
            user.save(update_fields=['balance'])
            tx.status       = 'failed'
            tx.balance_after = float(user.balance)
            tx.metadata['rejected_by']     = request.user.email
            tx.metadata['rejection_reason'] = reason
            tx.save()
        return JsonResponse({
            'success': True,
            'message': f'Retiro rechazado. ${float(tx.amount):,.2f} devuelto a {tx.user.email}',
        })

    return JsonResponse({'error': 'Transacción no válida o ya procesada.'}, status=400)
