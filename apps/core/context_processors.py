"""
Nova Capital Group - Global Context Processors
"""


def global_context(request):
    """Inject global context into all templates."""
    context = {
        'platform_name': 'Nova Capital Group',
        'platform_tagline': 'Inversiones de Clase Mundial',
    }

    if request.user.is_authenticated:
        try:
            from apps.trading.models import Watchlist
            context['watchlist_count'] = Watchlist.objects.filter(user=request.user).count()
        except Exception:
            context['watchlist_count'] = 0

        try:
            from apps.finances.models import Transaction
            if request.user.is_staff or request.user.is_superuser:
                # Para admins: contar depósitos pendientes + retiros en proceso
                context['pending_transactions'] = Transaction.objects.filter(
                    status__in=['pending', 'processing'],
                    transaction_type__in=['deposit', 'withdrawal']
                ).count()
            else:
                # Para usuarios normales: sus propias transacciones pendientes
                context['pending_transactions'] = Transaction.objects.filter(
                    user=request.user, status='pending'
                ).count()
        except Exception:
            context['pending_transactions'] = 0

    return context
