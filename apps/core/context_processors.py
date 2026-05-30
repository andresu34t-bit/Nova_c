"""
Nova Capital Group - Global Context Processors
"""
from apps.trading.models import Asset


def global_context(request):
    """Inject global context into all templates."""
    context = {
        'platform_name': 'Nova Capital Group',
        'platform_tagline': 'Inversiones de Clase Mundial',
    }
    
    if request.user.is_authenticated:
        try:
            from apps.trading.models import Watchlist
            watchlist_count = Watchlist.objects.filter(user=request.user).count()
            context['watchlist_count'] = watchlist_count
        except Exception:
            context['watchlist_count'] = 0
        
        try:
            from apps.finances.models import Transaction
            pending_transactions = Transaction.objects.filter(
                user=request.user, status='pending'
            ).count()
            context['pending_transactions'] = pending_transactions
        except Exception:
            context['pending_transactions'] = 0

    return context
