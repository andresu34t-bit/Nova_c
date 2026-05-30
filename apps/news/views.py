"""
Nova Capital Group - News Views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import NewsArticle
from apps.markets.models import EconomicEvent
from django.utils import timezone
import requests
import logging

logger = logging.getLogger('apps')


@login_required
def news_view(request):
    category = request.GET.get('category', 'all')
    
    articles = NewsArticle.objects.all()
    if category != 'all':
        articles = articles.filter(category=category)
    articles = articles.order_by('-published_at')[:50]
    
    featured = NewsArticle.objects.filter(is_featured=True).order_by('-published_at')[:3]
    
    upcoming_events = EconomicEvent.objects.filter(
        event_date__gte=timezone.now()
    ).order_by('event_date')[:10]
    
    context = {
        'articles': articles,
        'featured': featured,
        'upcoming_events': upcoming_events,
        'active_category': category,
        'categories': NewsArticle.CATEGORIES,
    }
    return render(request, 'news/news.html', context)


@login_required
def fetch_news(request):
    """Fetch news from NewsAPI."""
    from django.conf import settings
    api_key = settings.NEWS_API_KEY
    
    if not api_key:
        # Use mock data if no API key
        return JsonResponse({'status': 'no_api_key', 'message': 'Configure NEWS_API_KEY'})
    
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': 'cryptocurrency OR bitcoin OR stocks OR forex',
            'language': 'es',
            'sortBy': 'publishedAt',
            'pageSize': 20,
            'apiKey': api_key,
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            created = 0
            for article in articles:
                if article.get('title') and article.get('url'):
                    _, was_created = NewsArticle.objects.get_or_create(
                        source_url=article['url'],
                        defaults={
                            'title': article['title'][:500],
                            'summary': article.get('description', '')[:1000],
                            'source': article.get('source', {}).get('name', 'Unknown'),
                            'image_url': article.get('urlToImage', ''),
                            'published_at': article.get('publishedAt', timezone.now()),
                            'category': 'general',
                        }
                    )
                    if was_created:
                        created += 1
            return JsonResponse({'status': 'ok', 'created': created})
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)})
