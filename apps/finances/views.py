"""
Nova Capital Group - Finances Views
Sistema de depósitos con aprobación manual del administrador
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction as db_transaction
from .models import Transaction, BankAccount
import logging

logger = logging.getLogger('apps')


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
    Depósito queda en estado PENDING hasta que el admin lo apruebe.
    El saldo NO se acredita hasta la aprobación.
    """
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0')
        payment_method = request.POST.get('payment_method', 'bank_transfer')
        bank_reference = request.POST.get('bank_reference', '').strip()
        bank_name = request.POST.get('bank_name', '').strip()
        notes = request.POST.get('notes', '').strip()

        try:
            amount = float(amount_str)
            if amount <= 0:
                messages.error(request, 'El monto debe ser mayor a 0.')
                return redirect('finances:deposit')
            if amount > 1_000_000:
                messages.error(request, 'El monto máximo por depósito es $1,000,000.')
                return redirect('finances:deposit')

            user = request.user

            # Crear transacción en estado PENDING — NO acreditar saldo todavía
            tx = Transaction.objects.create(
                user=user,
                transaction_type='deposit',
                amount=amount,
                status='pending',
                payment_method=payment_method,
                reference=bank_reference,
                description=f'Depósito via {payment_method}'
                            + (f' | Banco: {bank_name}' if bank_name else '')
                            + (f' | Ref: {bank_reference}' if bank_reference else '')
                            + (f' | Nota: {notes}' if notes else ''),
                balance_before=float(user.balance),
                balance_after=float(user.balance),  # No cambia hasta aprobación
                metadata={
                    'bank_name': bank_name,
                    'bank_reference': bank_reference,
                    'notes': notes,
                    'requested_at': timezone.now().isoformat(),
                }
            )

            messages.success(
                request,
                f'✓ Solicitud de depósito de ${amount:,.2f} USD enviada correctamente. '
                f'Tu depósito será revisado y aprobado por el equipo en las próximas horas. '
                f'Referencia: {str(tx.id)[:8].upper()}'
            )
            logger.info(f"Deposit request: user={user.email} amount={amount} method={payment_method}")

        except ValueError:
            messages.error(request, 'Monto inválido.')

        return redirect('finances:finances')

    return render(request, 'finances/deposit.html')


@login_required
def withdrawal_view(request):
    """
    Retiro queda en estado PROCESSING hasta que el admin lo apruebe.
    El saldo se descuenta inmediatamente (reservado).
    """
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0')
        payment_method = request.POST.get('payment_method', 'bank_transfer')
        bank_name = request.POST.get('bank_name', '').strip()
        account_number = request.POST.get('account_number', '').strip()
        notes = request.POST.get('notes', '').strip()

        try:
            amount = float(amount_str)
            user = request.user

            if amount <= 0:
                messages.error(request, 'El monto debe ser mayor a 0.')
                return redirect('finances:withdrawal')
            if amount > float(user.balance):
                messages.error(request, f'Saldo insuficiente. Disponible: ${float(user.balance):,.2f}')
                return redirect('finances:withdrawal')

            with db_transaction.atomic():
                balance_before = float(user.balance)
                user.balance = balance_before - amount
                user.save(update_fields=['balance'])

                tx = Transaction.objects.create(
                    user=user,
                    transaction_type='withdrawal',
                    amount=amount,
                    status='processing',
                    payment_method=payment_method,
                    description=f'Retiro via {payment_method}'
                                + (f' | Banco: {bank_name}' if bank_name else '')
                                + (f' | Cuenta: {account_number}' if account_number else '')
                                + (f' | Nota: {notes}' if notes else ''),
                    balance_before=balance_before,
                    balance_after=float(user.balance),
                    metadata={
                        'bank_name': bank_name,
                        'account_number': account_number,
                        'notes': notes,
                    }
                )

            messages.success(
                request,
                f'✓ Solicitud de retiro de ${amount:,.2f} USD enviada. '
                f'Se procesará en 1-3 días hábiles. Ref: {str(tx.id)[:8].upper()}'
            )

        except ValueError:
            messages.error(request, 'Monto inválido.')

        return redirect('finances:finances')

    return render(request, 'finances/withdrawal.html')


@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'finances/history.html', {'transactions': transactions})


# ══════════════════════════════════════════════════════════════
# VISTAS DE ADMINISTRACIÓN — Solo para staff/superuser
# ══════════════════════════════════════════════════════════════

@login_required
@user_passes_test(is_admin)
def admin_transactions_view(request):
    """Panel admin de transacciones pendientes."""
    pending_deposits    = Transaction.objects.filter(
        transaction_type='deposit', status='pending'
    ).select_related('user').order_by('-created_at')

    pending_withdrawals = Transaction.objects.filter(
        transaction_type='withdrawal', status='processing'
    ).select_related('user').order_by('-created_at')

    all_transactions = Transaction.objects.select_related('user').order_by('-created_at')[:100]

    context = {
        'pending_deposits': pending_deposits,
        'pending_withdrawals': pending_withdrawals,
        'all_transactions': all_transactions,
        'pending_count': pending_deposits.count() + pending_withdrawals.count(),
    }
    return render(request, 'finances/admin_transactions.html', context)


@login_required
@user_passes_test(is_admin)
def approve_transaction(request, tx_id):
    """Aprobar un depósito o retiro pendiente."""
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
            tx.balance_after = float(user.balance)
            tx.completed_at = timezone.now()
            tx.metadata['approved_by'] = request.user.email
            tx.metadata['approved_at'] = timezone.now().isoformat()
            tx.save()

        logger.info(f"Deposit APPROVED: {tx.user.email} ${tx.amount} by {request.user.email}")
        return JsonResponse({
            'success': True,
            'message': f'Depósito de ${float(tx.amount):,.2f} aprobado. Saldo acreditado a {tx.user.email}',
            'new_balance': float(tx.user.balance),
        })

    elif tx.transaction_type == 'withdrawal' and tx.status == 'processing':
        with db_transaction.atomic():
            tx.status = 'completed'
            tx.completed_at = timezone.now()
            tx.user.total_withdrawn = float(tx.user.total_withdrawn) + float(tx.amount)
            tx.user.save(update_fields=['total_withdrawn'])
            tx.metadata['approved_by'] = request.user.email
            tx.metadata['approved_at'] = timezone.now().isoformat()
            tx.save()

        logger.info(f"Withdrawal APPROVED: {tx.user.email} ${tx.amount} by {request.user.email}")
        return JsonResponse({
            'success': True,
            'message': f'Retiro de ${float(tx.amount):,.2f} aprobado para {tx.user.email}',
        })

    return JsonResponse({'error': 'Transacción no válida o ya procesada.'}, status=400)


@login_required
@user_passes_test(is_admin)
def reject_transaction(request, tx_id):
    """Rechazar un depósito o retiro pendiente."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    tx = get_object_or_404(Transaction, id=tx_id)
    reason = request.POST.get('reason', 'Rechazado por el administrador')

    if tx.transaction_type == 'deposit' and tx.status == 'pending':
        tx.status = 'failed'
        tx.metadata['rejected_by'] = request.user.email
        tx.metadata['rejected_at'] = timezone.now().isoformat()
        tx.metadata['rejection_reason'] = reason
        tx.save()

        logger.info(f"Deposit REJECTED: {tx.user.email} ${tx.amount} by {request.user.email}")
        return JsonResponse({
            'success': True,
            'message': f'Depósito de ${float(tx.amount):,.2f} rechazado.',
        })

    elif tx.transaction_type == 'withdrawal' and tx.status == 'processing':
        with db_transaction.atomic():
            # Devolver el saldo al usuario
            user = tx.user
            user.balance = float(user.balance) + float(tx.amount)
            user.save(update_fields=['balance'])

            tx.status = 'failed'
            tx.balance_after = float(user.balance)
            tx.metadata['rejected_by'] = request.user.email
            tx.metadata['rejected_at'] = timezone.now().isoformat()
            tx.metadata['rejection_reason'] = reason
            tx.save()

        logger.info(f"Withdrawal REJECTED: {tx.user.email} ${tx.amount} by {request.user.email}")
        return JsonResponse({
            'success': True,
            'message': f'Retiro rechazado. ${float(tx.amount):,.2f} devuelto a {tx.user.email}',
            'refunded_balance': float(tx.user.balance),
        })

    return JsonResponse({'error': 'Transacción no válida o ya procesada.'}, status=400)
