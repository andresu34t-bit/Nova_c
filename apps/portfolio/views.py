"""
Nova Capital Group - Portfolio Views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Position, PortfolioSnapshot
from apps.trading.models import Order


@login_required
def portfolio_view(request):
    user = request.user
    positions = Position.objects.filter(user=user, is_open=True).select_related('asset').order_by('-opened_at')
    closed_positions = Position.objects.filter(user=user, is_open=False).select_related('asset').order_by('-closed_at')[:20]
    
    portfolio_value = sum(p.current_value for p in positions)
    total_cost = sum(p.cost_basis for p in positions)
    total_pnl = portfolio_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    total_realized = sum(float(p.realized_pnl) for p in closed_positions)
    
    # Asset distribution
    distribution = []
    for pos in positions:
        pct = (pos.current_value / portfolio_value * 100) if portfolio_value > 0 else 0
        distribution.append({
            'symbol': pos.asset.symbol,
            'name': pos.asset.name,
            'value': round(pos.current_value, 2),
            'pct': round(pct, 1),
            'pnl': round(pos.unrealized_pnl, 2),
            'pnl_pct': round(pos.unrealized_pnl_pct, 2),
        })
    
    # Historical snapshots
    snapshots = PortfolioSnapshot.objects.filter(user=user).order_by('snapshot_date')[:90]
    
    context = {
        'positions': positions,
        'closed_positions': closed_positions,
        'portfolio_value': portfolio_value,
        'total_cost': total_cost,
        'total_pnl': total_pnl,
        'total_pnl_pct': total_pnl_pct,
        'total_realized': total_realized,
        'cash_balance': float(user.balance),
        'total_assets': float(user.balance) + portfolio_value,
        'distribution': distribution,
        'snapshots': snapshots,
        'snapshot_labels': [s.snapshot_date.strftime('%d/%m') for s in snapshots],
        'snapshot_values': [float(s.total_value) for s in snapshots],
    }
    return render(request, 'portfolio/portfolio.html', context)


@login_required
def portfolio_api(request):
    """API for portfolio data."""
    user = request.user
    positions = Position.objects.filter(user=user, is_open=True).select_related('asset')
    
    data = []
    for pos in positions:
        data.append({
            'symbol': pos.asset.symbol,
            'name': pos.asset.name,
            'quantity': float(pos.quantity),
            'avg_price': float(pos.avg_buy_price),
            'current_price': float(pos.current_price),
            'value': round(pos.current_value, 2),
            'cost': round(pos.cost_basis, 2),
            'pnl': round(pos.unrealized_pnl, 2),
            'pnl_pct': round(pos.unrealized_pnl_pct, 2),
        })
    
    return JsonResponse({'positions': data, 'balance': float(user.balance)})
