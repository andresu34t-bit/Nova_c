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
    
    # Get top assets for display
    top_crypto = Asset.objects.filter(asset_type='crypto', is_active=True).order_by('rank')[:6]
    top_stocks = Asset.objects.filter(asset_type='stock', is_active=True).order_by('rank')[:6]
    latest_news = NewsArticle.objects.order_by('-published_at')[:3]
    
    context = {
        'top_crypto': top_crypto,
        'top_stocks': top_stocks,
        'latest_news': latest_news,
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
