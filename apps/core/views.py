"""
Nova Capital Group - Core Views
"""
from django.shortcuts import render
from django.http import JsonResponse
from apps.trading.models import Asset
from apps.news.models import NewsArticle


def home_view(request):
    """Landing page."""
    if request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect('dashboard:index')
    
    # Get top assets — tolerante a errores de BD
    try:
        top_crypto = Asset.objects.filter(asset_type='crypto', is_active=True).order_by('rank')[:6]
        top_stocks = Asset.objects.filter(asset_type='stock', is_active=True).order_by('rank')[:6]
        latest_news = NewsArticle.objects.order_by('-published_at')[:3]
    except Exception:
        top_crypto = []
        top_stocks = []
        latest_news = []
    
    # Demo assets shown when DB is empty
    demo_assets = [
        ('BTC', 'Bitcoin',  '67,500', '▲ +2.45%', 'var(--nova-success)'),
        ('ETH', 'Ethereum', '3,850',  '▲ +1.82%', 'var(--nova-success)'),
        ('BNB', 'BNB',      '605',    '▼ -0.54%', 'var(--nova-danger)'),
        ('SOL', 'Solana',   '185',    '▲ +3.21%', 'var(--nova-success)'),
    ]
    
    context = {
        'top_crypto': top_crypto,
        'top_stocks': top_stocks,
        'latest_news': latest_news,
        'demo_assets': demo_assets,
    }
    return render(request, 'core/home.html', context)


def about_view(request):
    return render(request, 'core/about.html')


def contact_view(request):
    return render(request, 'core/contact.html')


def terms_view(request):
    return render(request, 'core/terms.html')


def privacy_view(request):
    return render(request, 'core/privacy.html')


def handler404(request, exception):
    return render(request, 'core/404.html', status=404)


def handler500(request):
    return render(request, 'core/500.html', status=500)


def health_check(request):
    """Health check endpoint para Render."""
    import django
    import sys
    return JsonResponse({
        'status': 'ok',
        'django': django.__version__,
        'python': sys.version,
        'debug': django.conf.settings.DEBUG,
    })
