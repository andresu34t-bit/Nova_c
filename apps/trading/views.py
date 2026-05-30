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
    
    context = {
        'asset': asset,
        'watchlist': watchlist,
        'recent_orders': recent_orders,
        'all_assets': all_assets,
        'in_watchlist': in_watchlist,
        'user_balance': request.user.balance,
    }
    return render(request, 'trading/trading.html', context)


@login_required
def place_order(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        asset_symbol = request.POST.get('symbol', '').upper()
        side = request.POST.get('side', '')
        order_type = request.POST.get('order_type', 'market')
        quantity_str = request.POST.get('quantity', '0')
        
        if not all([asset_symbol, side, quantity_str]):
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        
        quantity = float(quantity_str)
        if quantity <= 0:
            return JsonResponse({'error': 'Cantidad inválida'}, status=400)
        
        asset = get_object_or_404(Asset, symbol=asset_symbol)
        user = request.user
        price = float(asset.current_price)
        total_value = quantity * price
        fee = total_value * 0.001  # 0.1% fee
        
        with db_transaction.atomic():
            if side == 'buy':
                total_cost = total_value + fee
                if float(user.balance) < total_cost:
                    return JsonResponse({'error': 'Saldo insuficiente'}, status=400)
                
                # Deduct balance
                user.balance = float(user.balance) - total_cost
                user.save(update_fields=['balance'])
                
                # Create or update position
                position, created = Position.objects.get_or_create(
                    user=user, asset=asset, is_open=True,
                    defaults={'quantity': 0, 'avg_buy_price': price, 'current_price': price}
                )
                if not created:
                    # Update average price
                    old_cost = float(position.quantity) * float(position.avg_buy_price)
                    new_cost = quantity * price
                    new_qty = float(position.quantity) + quantity
                    position.avg_buy_price = (old_cost + new_cost) / new_qty
                    position.quantity = new_qty
                else:
                    position.quantity = quantity
                    position.avg_buy_price = price
                position.current_price = price
                position.save()
                
                # Record transaction
                Transaction.objects.create(
                    user=user,
                    transaction_type='trade_buy',
                    amount=total_value,
                    status='completed',
                    description=f'Compra {quantity} {asset.symbol} @ ${price:.2f}',
                    balance_before=float(user.balance) + total_cost,
                    balance_after=float(user.balance),
                    fee_amount=fee,
                    completed_at=timezone.now(),
                )
                
            elif side == 'sell':
                position = Position.objects.filter(user=user, asset=asset, is_open=True).first()
                if not position or float(position.quantity) < quantity:
                    return JsonResponse({'error': 'No tienes suficientes activos para vender'}, status=400)
                
                proceeds = total_value - fee
                user.balance = float(user.balance) + proceeds
                user.save(update_fields=['balance'])
                
                # Update position
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
                    user=user,
                    transaction_type='trade_sell',
                    amount=total_value,
                    status='completed',
                    description=f'Venta {quantity} {asset.symbol} @ ${price:.2f}',
                    balance_before=float(user.balance) - proceeds,
                    balance_after=float(user.balance),
                    fee_amount=fee,
                    completed_at=timezone.now(),
                )
            
            # Create order record
            order = Order.objects.create(
                user=user,
                asset=asset,
                order_type=order_type,
                side=side,
                quantity=quantity,
                price=price,
                filled_price=price,
                filled_quantity=quantity,
                total_value=total_value,
                fee=fee,
                status='filled',
                filled_at=timezone.now(),
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Orden ejecutada: {side.upper()} {quantity} {asset.symbol} @ ${price:.2f}',
            'order_id': str(order.id),
            'new_balance': float(user.balance),
        })
    
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return JsonResponse({'error': f'Error al procesar la orden: {str(e)}'}, status=500)


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).select_related('asset').order_by('-created_at')
    return render(request, 'trading/order_history.html', {'orders': orders})


@login_required
def toggle_watchlist(request):
    if request.method == 'POST':
        symbol = request.POST.get('symbol', '').upper()
        asset = get_object_or_404(Asset, symbol=symbol)
        watchlist_item, created = Watchlist.objects.get_or_create(user=request.user, asset=asset)
        if not created:
            watchlist_item.delete()
            return JsonResponse({'status': 'removed', 'message': f'{symbol} eliminado de watchlist'})
        return JsonResponse({'status': 'added', 'message': f'{symbol} añadido a watchlist'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def watchlist_view(request):
    watchlist = Watchlist.objects.filter(user=request.user).select_related('asset').order_by('-added_at')
    return render(request, 'trading/watchlist.html', {'watchlist': watchlist})
