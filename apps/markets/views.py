"""
Nova Capital Group - Markets Views
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from apps.trading.models import Asset
import requests
import logging

logger = logging.getLogger('apps')


@login_required
def markets_overview(request):
    crypto = Asset.objects.filter(asset_type='crypto', is_active=True).order_by('rank')[:50]
    stocks = Asset.objects.filter(asset_type='stock', is_active=True).order_by('rank')[:30]
    forex = Asset.objects.filter(asset_type='forex', is_active=True).order_by('symbol')[:20]
    indices = Asset.objects.filter(asset_type='index', is_active=True).order_by('symbol')
    
    context = {
        'crypto': crypto,
        'stocks': stocks,
        'forex': forex,
        'indices': indices,
        'active_tab': request.GET.get('tab', 'crypto'),
    }
    return render(request, 'markets/overview.html', context)


@login_required
def asset_detail(request, symbol):
    asset = get_object_or_404(Asset, symbol=symbol.upper())
    
    # Check if in watchlist
    in_watchlist = False
    if request.user.is_authenticated:
        from apps.trading.models import Watchlist
        in_watchlist = Watchlist.objects.filter(user=request.user, asset=asset).exists()
    
    context = {
        'asset': asset,
        'in_watchlist': in_watchlist,
    }
    return render(request, 'markets/asset_detail.html', context)


@login_required
def api_prices(request):
    """API endpoint for live price data."""
    asset_type = request.GET.get('type', 'crypto')
    assets = Asset.objects.filter(asset_type=asset_type, is_active=True).order_by('rank')[:50]
    
    data = []
    for asset in assets:
        data.append({
            'symbol': asset.symbol,
            'name': asset.name,
            'price': float(asset.current_price),
            'change_24h': float(asset.price_change_24h),
            'change_pct_24h': float(asset.price_change_pct_24h),
            'volume_24h': float(asset.volume_24h),
            'market_cap': float(asset.market_cap),
            'high_24h': float(asset.high_24h),
            'low_24h': float(asset.low_24h),
            'image_url': asset.image_url,
            'rank': asset.rank,
        })
    
    return JsonResponse({'data': data, 'count': len(data)})


@login_required
def fetch_market_data(request):
    """Fetch and update market data from CoinGecko API."""
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 50,
            'page': 1,
            'sparkline': False,
            'price_change_percentage': '24h',
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            coins = response.json()
            updated = 0
            for coin in coins:
                asset, created = Asset.objects.update_or_create(
                    symbol=coin['symbol'].upper(),
                    defaults={
                        'name': coin['name'],
                        'asset_type': 'crypto',
                        'current_price': coin.get('current_price', 0) or 0,
                        'price_change_24h': coin.get('price_change_24h', 0) or 0,
                        'price_change_pct_24h': coin.get('price_change_percentage_24h', 0) or 0,
                        'volume_24h': coin.get('total_volume', 0) or 0,
                        'market_cap': coin.get('market_cap', 0) or 0,
                        'high_24h': coin.get('high_24h', 0) or 0,
                        'low_24h': coin.get('low_24h', 0) or 0,
                        'image_url': coin.get('image', ''),
                        'coingecko_id': coin.get('id', ''),
                        'rank': coin.get('market_cap_rank', 0) or 0,
                        'is_active': True,
                    }
                )
                updated += 1
            return JsonResponse({'status': 'ok', 'updated': updated})
        else:
            return JsonResponse({'status': 'error', 'message': f'API returned {response.status_code}'})
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)})
