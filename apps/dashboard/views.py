"""
Nova Capital Group - Dashboard Views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from apps.trading.models import Asset, Order
from apps.portfolio.models import Position, PortfolioSnapshot
from apps.finances.models import Transaction
from apps.news.models import NewsArticle


@login_required
def index(request):
    user = request.user

    # Portfolio data — recalculate current_price from asset
    positions = Position.objects.filter(user=user, is_open=True).select_related('asset')

    # Sync current prices
    for pos in positions:
        if pos.asset.current_price != pos.current_price:
            pos.current_price = pos.asset.current_price
            pos.save(update_fields=['current_price'])

    portfolio_value = sum(p.current_value for p in positions)
    total_cost      = sum(p.cost_basis    for p in positions)
    total_pnl       = portfolio_value - total_cost
    total_pnl_pct   = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    # Recent orders
    recent_orders = Order.objects.filter(user=user).select_related('asset').order_by('-created_at')[:8]

    # Recent transactions
    recent_transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:5]

    # Portfolio snapshots for chart (last 30 days)
    snapshots = PortfolioSnapshot.objects.filter(
        user=user,
        snapshot_date__gte=timezone.now().date() - timedelta(days=30)
    ).order_by('snapshot_date')

    snapshot_labels = [s.snapshot_date.strftime('%d/%m') for s in snapshots]
    snapshot_values = [float(s.total_value) for s in snapshots]

    # Top movers
    top_gainers = Asset.objects.filter(is_active=True).order_by('-price_change_pct_24h')[:5]
    top_losers  = Asset.objects.filter(is_active=True).order_by('price_change_pct_24h')[:5]

    # Latest news
    latest_news = NewsArticle.objects.order_by('-published_at')[:3]

    # Asset distribution for pie chart
    asset_distribution = []
    if positions and portfolio_value > 0:
        for pos in positions:
            pct = (pos.current_value / portfolio_value * 100)
            asset_distribution.append({
                'symbol': pos.asset.symbol,
                'name':   pos.asset.name,
                'value':  round(pos.current_value, 2),
                'pct':    round(pct, 1),
                'pnl':    round(pos.unrealized_pnl, 2),
                'pnl_pct':round(pos.unrealized_pnl_pct, 2),
            })
        asset_distribution.sort(key=lambda x: x['value'], reverse=True)

    context = {
        'user':               user,
        'portfolio_value':    round(portfolio_value, 2),
        'total_cost':         round(total_cost, 2),
        'total_pnl':          round(total_pnl, 2),
        'total_pnl_pct':      round(total_pnl_pct, 2),
        'cash_balance':       float(user.balance),
        'total_assets':       round(float(user.balance) + portfolio_value, 2),
        'positions':          positions,
        'recent_orders':      recent_orders,
        'recent_transactions':recent_transactions,
        'snapshot_labels':    snapshot_labels,
        'snapshot_values':    snapshot_values,
        'top_gainers':        top_gainers,
        'top_losers':         top_losers,
        'latest_news':        latest_news,
        'asset_distribution': asset_distribution,
        'positions_count':    positions.count(),
        'orders_count':       Order.objects.filter(user=user).count(),
    }
    return render(request, 'dashboard/index.html', context)
