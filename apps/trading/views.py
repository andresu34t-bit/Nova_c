"""
Nova Capital Group - Trading Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction as db_transaction
from .models import Asset, Order, Watchlist
from apps.portfolio.models import Position
from apps.finances.models import Transaction
import logging

logger = logging.getLogger('apps')

# Comisiones por tipo de cuenta
FEE_RATES = {
    'standard':     0.002,   # 0.2%
    'premium':      0.001,   # 0.1%
    'institutional': 0.0005, # 0.05%
}

# Límites de depósito diario por tipo de cuenta
DEPOSIT_LIMITS = {
    'standard':     10_000,
    'premium':      100_000,
    'institutional': 0,  # Sin límite
}


def get_fee_rate(user):
    return FEE_RATES.get(user.account_type, 0.002)


@login_required
def trading_view(request):
    symbol = request.GET.get('symbol', 'BTC')
    asset = Asset.objects.filter(symbol=symbol.upper()).first()
    if not asset:
        asset = Asset.objects.filter(asset_type='crypto', is_active=True).first()

    watchlist = Watchlist.objects.filter(user=request.user).select_related('asset')
    recent_orders = Order.objects.filter(user=request.user).select_related('asset').order_by('-created_at')[:10]
    all_assets = Asset.objects.filter(is_active=True).order_by('rank')[:100]
    in_watchlist = Watchlist.objects.filter(user=request.user, asset=asset).exists() if asset else False
    fee_rate = get_fee_rate(request.user)

    context = {
        'asset': asset,
        'watchlist': watchlist,
        'recent_orders': recent_orders,
        'all_assets': all_assets,
        'in_watchlist': in_watchlist,
        'user_balance': request.user.balance,
        'fee_rate': fee_rate,
        'fee_pct': fee_rate * 100,
    }
    return render(request, 'trading/trading.html', context)


@login_required
def place_order(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        asset_symbol = request.POST.get('symbol', '').upper()
        side         = request.POST.get('side', '')
        order_type   = request.POST.get('order_type', 'market')
        quantity_str = request.POST.get('quantity', '0')

        if not all([asset_symbol, side, quantity_str]):
            return JsonResponse({'error': 'Datos incompletos'}, status=400)

        quantity = float(quantity_str)
        if quantity <= 0:
            return JsonResponse({'error': 'Cantidad inválida'}, status=400)

        asset = get_object_or_404(Asset, symbol=asset_symbol)
        user  = request.user
        price = float(asset.current_price)
        total_value = quantity * price
        fee_rate = get_fee_rate(user)
        fee = total_value * fee_rate

        with db_transaction.atomic():
            if side == 'buy':
                total_cost = total_value + fee
                if float(user.balance) < total_cost:
                    return JsonResponse({'error': 'Saldo insuficiente'}, status=400)

                user.balance = float(user.balance) - total_cost
                user.save(update_fields=['balance'])

                position, created = Position.objects.get_or_create(
                    user=user, asset=asset, is_open=True,
                    defaults={'quantity': 0, 'avg_buy_price': price, 'current_price': price}
                )
                if not created:
                    old_cost = float(position.quantity) * float(position.avg_buy_price)
                    new_cost = quantity * price
                    new_qty  = float(position.quantity) + quantity
                    position.avg_buy_price = (old_cost + new_cost) / new_qty
                    position.quantity = new_qty
                else:
                    position.quantity = quantity
                    position.avg_buy_price = price
                position.current_price = price
                position.save()

                Transaction.objects.create(
                    user=user, transaction_type='trade_buy', amount=total_value,
                    status='completed',
                    description=f'Compra {quantity} {asset.symbol} @ ${price:.2f}',
                    balance_before=float(user.balance) + total_cost,
                    balance_after=float(user.balance),
                    fee_amount=fee, completed_at=timezone.now(),
                )

            elif side == 'sell':
                position = Position.objects.filter(user=user, asset=asset, is_open=True).first()
                if not position or float(position.quantity) < quantity:
                    return JsonResponse({'error': 'No tienes suficientes activos para vender'}, status=400)

                proceeds = total_value - fee
                user.balance = float(user.balance) + proceeds
                user.save(update_fields=['balance'])

                new_qty = float(position.quantity) - quantity
                if new_qty <= 0.000001:
                    realized_pnl = proceeds - (quantity * float(position.avg_buy_price))
                    position.realized_pnl = float(position.realized_pnl) + realized_pnl
                    position.is_open = False
                    position.closed_at = timezone.now()
                    position.save()
                else:
                    position.quantity = new_qty
                    position.current_price = price
                    position.save()

                Transaction.objects.create(
                    user=user, transaction_type='trade_sell', amount=total_value,
                    status='completed',
                    description=f'Venta {quantity} {asset.symbol} @ ${price:.2f}',
                    balance_before=float(user.balance) - proceeds,
                    balance_after=float(user.balance),
                    fee_amount=fee, completed_at=timezone.now(),
                )

            order = Order.objects.create(
                user=user, asset=asset, order_type=order_type, side=side,
                quantity=quantity, price=price, filled_price=price,
                filled_quantity=quantity, total_value=total_value,
                fee=fee, status='filled', filled_at=timezone.now(),
            )

        # Email de confirmación (async-safe)
        try:
            from apps.accounts.emails import send_trade_confirmation_email
            send_trade_confirmation_email(user, side, asset.symbol, quantity, price, total_value, fee)
        except Exception:
            pass

        return JsonResponse({
            'success': True,
            'message': f'Orden ejecutada: {side.upper()} {quantity} {asset.symbol} @ ${price:.2f}',
            'order_id': str(order.id),
            'new_balance': float(user.balance),
            'fee': round(fee, 4),
            'fee_pct': fee_rate * 100,
        })

    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return JsonResponse({'error': f'Error al procesar la orden: {str(e)}'}, status=500)


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).select_related('asset').order_by('-created_at')
    buy_count    = orders.filter(side='buy').count()
    sell_count   = orders.filter(side='sell').count()
    filled_count = orders.filter(status='filled').count()
    return render(request, 'trading/order_history.html', {
        'orders': orders,
        'buy_count': buy_count,
        'sell_count': sell_count,
        'filled_count': filled_count,
    })


@login_required
def toggle_watchlist(request):
    if request.method == 'POST':
        symbol = request.POST.get('symbol', '').upper()
        asset  = get_object_or_404(Asset, symbol=symbol)
        item, created = Watchlist.objects.get_or_create(user=request.user, asset=asset)
        if not created:
            item.delete()
            return JsonResponse({'status': 'removed'})
        return JsonResponse({'status': 'added'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def watchlist_view(request):
    watchlist = Watchlist.objects.filter(user=request.user).select_related('asset').order_by('-added_at')
    return render(request, 'trading/watchlist.html', {'watchlist': watchlist})


@login_required
def set_price_alert(request):
    """Configurar alerta de precio alta/baja para un activo."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    symbol     = request.POST.get('symbol', '').upper()
    alert_high = request.POST.get('alert_high', '').strip()
    alert_low  = request.POST.get('alert_low', '').strip()

    try:
        asset = get_object_or_404(Asset, symbol=symbol)
        wl, _ = Watchlist.objects.get_or_create(user=request.user, asset=asset)
        wl.alert_price_high = float(alert_high) if alert_high else None
        wl.alert_price_low  = float(alert_low)  if alert_low  else None
        wl.save()
        return JsonResponse({
            'success': True,
            'message': f'Alertas configuradas para {symbol}',
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def profit_calculator(request):
    """API: calculadora de ganancias para una posición."""
    symbol       = request.GET.get('symbol', '').upper()
    entry_price  = float(request.GET.get('entry', 0))
    quantity     = float(request.GET.get('qty', 0))
    target_price = float(request.GET.get('target', 0))

    if not all([symbol, entry_price, quantity, target_price]):
        return JsonResponse({'error': 'Parámetros incompletos'}, status=400)

    cost       = entry_price * quantity
    value      = target_price * quantity
    fee_rate   = get_fee_rate(request.user)
    fee_buy    = cost * fee_rate
    fee_sell   = value * fee_rate
    gross_pnl  = value - cost
    net_pnl    = gross_pnl - fee_buy - fee_sell
    pnl_pct    = (net_pnl / cost * 100) if cost > 0 else 0

    return JsonResponse({
        'symbol':       symbol,
        'entry_price':  entry_price,
        'target_price': target_price,
        'quantity':     quantity,
        'cost':         round(cost, 2),
        'value':        round(value, 2),
        'gross_pnl':    round(gross_pnl, 2),
        'net_pnl':      round(net_pnl, 2),
        'pnl_pct':      round(pnl_pct, 2),
        'total_fees':   round(fee_buy + fee_sell, 4),
        'fee_rate_pct': fee_rate * 100,
    })
