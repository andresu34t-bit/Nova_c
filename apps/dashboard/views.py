"""
Nova Capital Group - Dashboard Views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import timedelta
from apps.trading.models import Asset, Order
from apps.portfolio.models import Position, PortfolioSnapshot
from apps.finances.models import Transaction
from apps.news.models import NewsArticle


def is_admin(user):
    return user.is_staff or user.is_superuser


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


@login_required
@user_passes_test(is_admin, login_url='dashboard:index')
def admin_panel(request):
    """
    Panel de administración exclusivo para staff/superuser.
    Vista general de toda la plataforma.
    """
    from django.contrib.auth import get_user_model
    from apps.accounts.models import ActivityLog
    User = get_user_model()

    now = timezone.now()
    today = now.date()
    week_ago  = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # ── USUARIOS ────────────────────────────────────────────────
    total_users    = User.objects.count()
    new_today      = User.objects.filter(created_at__date=today).count()
    new_this_week  = User.objects.filter(created_at__gte=week_ago).count()
    active_users   = User.objects.filter(last_activity__gte=week_ago).count()
    suspended      = User.objects.filter(is_suspended=True).count()

    users_by_type = {
        'standard':      User.objects.filter(account_type='standard').count(),
        'premium':       User.objects.filter(account_type='premium').count(),
        'institutional': User.objects.filter(account_type='institutional').count(),
    }

    recent_users = User.objects.filter(
        is_staff=False, is_superuser=False
    ).order_by('-created_at')[:8]

    # ── FINANZAS ────────────────────────────────────────────────
    from django.db.models import Sum, Count

    total_deposited = Transaction.objects.filter(
        transaction_type='deposit', status='completed'
    ).aggregate(t=Sum('amount'))['t'] or 0

    total_withdrawn = Transaction.objects.filter(
        transaction_type='withdrawal', status='completed'
    ).aggregate(t=Sum('amount'))['t'] or 0

    deposits_today = Transaction.objects.filter(
        transaction_type='deposit', status='completed',
        created_at__date=today
    ).aggregate(t=Sum('amount'))['t'] or 0

    deposits_week = Transaction.objects.filter(
        transaction_type='deposit', status='completed',
        created_at__gte=week_ago
    ).aggregate(t=Sum('amount'))['t'] or 0

    pending_deposits    = Transaction.objects.filter(
        transaction_type='deposit', status='pending'
    ).select_related('user').order_by('-created_at')[:10]

    pending_withdrawals = Transaction.objects.filter(
        transaction_type='withdrawal', status='processing'
    ).select_related('user').order_by('-created_at')[:10]

    pending_count = (
        Transaction.objects.filter(transaction_type='deposit', status='pending').count()
        + Transaction.objects.filter(transaction_type='withdrawal', status='processing').count()
    )

    # ── TRADING ────────────────────────────────────────────────
    total_orders     = Order.objects.count()
    orders_today     = Order.objects.filter(created_at__date=today).count()
    orders_this_week = Order.objects.filter(created_at__gte=week_ago).count()

    trading_volume_total = Transaction.objects.filter(
        transaction_type__in=['trade_buy', 'trade_sell'], status='completed'
    ).aggregate(t=Sum('amount'))['t'] or 0

    trading_volume_week = Transaction.objects.filter(
        transaction_type__in=['trade_buy', 'trade_sell'], status='completed',
        created_at__gte=week_ago
    ).aggregate(t=Sum('amount'))['t'] or 0

    recent_orders = Order.objects.select_related('user', 'asset').order_by('-created_at')[:10]

    # ── ACTIVOS ────────────────────────────────────────────────
    total_assets    = Asset.objects.count()
    active_assets   = Asset.objects.filter(is_active=True).count()
    top_assets      = Asset.objects.filter(is_active=True).order_by('rank')[:8]

    # ── ACTIVIDAD ──────────────────────────────────────────────
    recent_activity = ActivityLog.objects.select_related('user').order_by('-created_at')[:15]

    logins_today = ActivityLog.objects.filter(
        action='login', created_at__date=today
    ).count()

    failed_logins = ActivityLog.objects.filter(
        action='login_failed', created_at__gte=week_ago
    ).count()

    # ── PLATAFORMA: saldo total en cuentas de usuario ──────────
    platform_balance = User.objects.filter(
        is_staff=False, is_superuser=False
    ).aggregate(t=Sum('balance'))['t'] or 0

    # Posiciones abiertas en toda la plataforma
    open_positions = Position.objects.filter(is_open=True).count()

    context = {
        # Usuarios
        'total_users':     total_users,
        'new_today':       new_today,
        'new_this_week':   new_this_week,
        'active_users':    active_users,
        'suspended':       suspended,
        'users_by_type':   users_by_type,
        'recent_users':    recent_users,
        # Finanzas
        'total_deposited':    float(total_deposited),
        'total_withdrawn':    float(total_withdrawn),
        'deposits_today':     float(deposits_today),
        'deposits_week':      float(deposits_week),
        'pending_deposits':   pending_deposits,
        'pending_withdrawals':pending_withdrawals,
        'pending_count':      pending_count,
        # Trading
        'total_orders':         total_orders,
        'orders_today':         orders_today,
        'orders_this_week':     orders_this_week,
        'trading_volume_total': float(trading_volume_total),
        'trading_volume_week':  float(trading_volume_week),
        'recent_orders':        recent_orders,
        # Activos
        'total_assets':  total_assets,
        'active_assets': active_assets,
        'top_assets':    top_assets,
        # Actividad
        'recent_activity': recent_activity,
        'logins_today':    logins_today,
        'failed_logins':   failed_logins,
        # Plataforma
        'platform_balance': float(platform_balance),
        'open_positions':   open_positions,
    }
    return render(request, 'dashboard/admin_panel.html', context)
