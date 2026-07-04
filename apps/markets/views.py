"""
Nova Capital Group - Markets Views
Integración real: CoinGecko (crypto) + Finnhub (stocks/forex/indices)
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings
from apps.trading.models import Asset, Watchlist
import requests
import logging

logger = logging.getLogger('apps')

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
STOCK_SYMBOLS = ['AAPL','MSFT','NVDA','AMZN','GOOGL','META','TSLA','NFLX','KO','JPM']

STOCK_NAMES = {
    'AAPL': 'Apple Inc.',     'MSFT': 'Microsoft',     'NVDA': 'Nvidia',
    'AMZN': 'Amazon',         'GOOGL': 'Alphabet',      'META': 'Meta Platforms',
    'TSLA': 'Tesla',          'NFLX': 'Netflix',        'KO': 'Coca-Cola',
    'JPM': 'JPMorgan Chase',
}

STOCK_LOGOS = {
    'AAPL': 'https://logo.clearbit.com/apple.com',
    'MSFT': 'https://logo.clearbit.com/microsoft.com',
    'NVDA': 'https://logo.clearbit.com/nvidia.com',
    'AMZN': 'https://logo.clearbit.com/amazon.com',
    'GOOGL': 'https://logo.clearbit.com/google.com',
    'META':  'https://logo.clearbit.com/meta.com',
    'TSLA': 'https://logo.clearbit.com/tesla.com',
    'NFLX': 'https://logo.clearbit.com/netflix.com',
    'KO':   'https://logo.clearbit.com/coca-cola.com',
    'JPM':  'https://logo.clearbit.com/jpmorganchase.com',
}

FOREX_PAIRS = [
    'EUR/USD','GBP/USD','USD/JPY','USD/CHF',
    'AUD/USD','NZD/USD','USD/CAD','EUR/JPY',
    'GBP/JPY','EUR/GBP',
]

INDICES_LIST = [
    {'symbol': 'SPX',    'name': 'S&P 500',       'finnhub': '^GSPC'},
    {'symbol': 'NDX',    'name': 'NASDAQ 100',     'finnhub': '^NDX'},
    {'symbol': 'DJI',    'name': 'Dow Jones',      'finnhub': '^DJI'},
    {'symbol': 'RUT',    'name': 'Russell 2000',   'finnhub': '^RUT'},
    {'symbol': 'DAX',    'name': 'DAX',            'finnhub': '^GDAXI'},
    {'symbol': 'FTSE',   'name': 'FTSE 100',       'finnhub': '^FTSE'},
    {'symbol': 'CAC',    'name': 'CAC 40',         'finnhub': '^FCHI'},
    {'symbol': 'N225',   'name': 'Nikkei 225',     'finnhub': '^N225'},
    {'symbol': 'HSI',    'name': 'Hang Seng',      'finnhub': '^HSI'},
    {'symbol': 'IBEX',   'name': 'IBEX 35',        'finnhub': '^IBEX'},
]


def _finnhub_key():
    return getattr(settings, 'FINNHUB_API_KEY', '')


def _fmt(val, decimals=2):
    try:
        return round(float(val), decimals)
    except Exception:
        return 0.0


# ─────────────────────────────────────────────
# MAIN VIEW
# ─────────────────────────────────────────────
@login_required
def markets_overview(request):
    active_tab = request.GET.get('tab', 'crypto')
    context = {'active_tab': active_tab}
    return render(request, 'markets/overview.html', context)


@login_required
def asset_detail(request, symbol):
    asset = get_object_or_404(Asset, symbol=symbol.upper())
    in_watchlist = Watchlist.objects.filter(user=request.user, asset=asset).exists()
    return render(request, 'markets/asset_detail.html', {
        'asset': asset,
        'in_watchlist': in_watchlist,
    })


# ─────────────────────────────────────────────
# API — CRYPTO  (CoinGecko, sin key requerida)
# ─────────────────────────────────────────────
@login_required
@require_GET
def api_crypto(request):
    try:
        url = 'https://api.coingecko.com/api/v3/coins/markets'
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 50,
            'page': 1,
            'sparkline': False,
            'price_change_percentage': '24h',
        }
        key = getattr(settings, 'COINGECKO_API_KEY', '')
        headers = {'x-cg-demo-api-key': key} if key else {}
        r = requests.get(url, params=params, headers=headers, timeout=12)
        r.raise_for_status()
        coins = r.json()

        data = []
        for coin in coins:
            price = _fmt(coin.get('current_price', 0), 8)
            chg_pct = _fmt(coin.get('price_change_percentage_24h', 0), 2)
            chg_usd = _fmt(coin.get('price_change_24h', 0), 6)
            data.append({
                'rank':       coin.get('market_cap_rank', 0),
                'symbol':     coin['symbol'].upper(),
                'name':       coin['name'],
                'image':      coin.get('image', ''),
                'price':      price,
                'chg_pct':    chg_pct,
                'chg_usd':    chg_usd,
                'volume':     _fmt(coin.get('total_volume', 0), 0),
                'market_cap': _fmt(coin.get('market_cap', 0), 0),
                'high':       _fmt(coin.get('high_24h', 0), 8),
                'low':        _fmt(coin.get('low_24h', 0), 8),
                'coingecko_id': coin.get('id', ''),
            })

        # Actualizar Asset en DB para que el ticker y trading tengan precios frescos
        _sync_crypto_assets(data)

        return JsonResponse({'ok': True, 'data': data})

    except requests.exceptions.Timeout:
        return JsonResponse({'ok': False, 'error': 'Tiempo de espera agotado. Reintenta.'}, status=504)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            return JsonResponse({'ok': False, 'error': 'Límite de API alcanzado. Espera 60s.'}, status=429)
        return JsonResponse({'ok': False, 'error': str(e)}, status=502)
    except Exception as e:
        logger.exception('api_crypto error')
        return JsonResponse({'ok': False, 'error': 'Error interno al cargar criptomonedas.'}, status=500)


def _sync_crypto_assets(data):
    try:
        for coin in data[:20]:
            Asset.objects.update_or_create(
                symbol=coin['symbol'],
                defaults={
                    'name': coin['name'], 'asset_type': 'crypto',
                    'current_price': coin['price'],
                    'price_change_24h': coin['chg_usd'],
                    'price_change_pct_24h': coin['chg_pct'],
                    'volume_24h': coin['volume'],
                    'market_cap': coin['market_cap'],
                    'high_24h': coin['high'], 'low_24h': coin['low'],
                    'image_url': coin['image'],
                    'coingecko_id': coin['coingecko_id'],
                    'rank': coin['rank'], 'is_active': True,
                }
            )
    except Exception:
        pass


# ─────────────────────────────────────────────
# API — STOCKS  (Finnhub quote)
# ─────────────────────────────────────────────
@login_required
@require_GET
def api_stocks(request):
    key = _finnhub_key()
    if not key:
        return JsonResponse({'ok': False, 'error': 'API key de Finnhub no configurada. Agrega FINNHUB_API_KEY en las variables de entorno.'}, status=503)

    results = []
    errors = []
    for sym in STOCK_SYMBOLS:
        try:
            # Quote endpoint
            q = requests.get(
                'https://finnhub.io/api/v1/quote',
                params={'symbol': sym, 'token': key},
                timeout=8
            ).json()

            # Basic financials para market cap
            price   = _fmt(q.get('c', 0), 2)
            prev    = _fmt(q.get('pc', 0), 2)
            chg_usd = _fmt(q.get('d', 0), 2)
            chg_pct = _fmt(q.get('dp', 0), 2)
            high    = _fmt(q.get('h', 0), 2)
            low     = _fmt(q.get('l', 0), 2)
            open_   = _fmt(q.get('o', 0), 2)

            if price == 0:
                continue

            results.append({
                'symbol':  sym,
                'name':    STOCK_NAMES.get(sym, sym),
                'logo':    STOCK_LOGOS.get(sym, ''),
                'price':   price,
                'prev':    prev,
                'chg_usd': chg_usd,
                'chg_pct': chg_pct,
                'high':    high,
                'low':     low,
                'open':    open_,
                'volume':  0,
                'market_cap': 0,
            })
        except Exception as e:
            errors.append(sym)
            logger.warning(f'Stock {sym} error: {e}')

    if not results and errors:
        return JsonResponse({'ok': False, 'error': f'No se pudieron cargar acciones: {errors}'}, status=502)

    return JsonResponse({'ok': True, 'data': results})


# ─────────────────────────────────────────────
# API — FOREX  (Finnhub forex)
# ─────────────────────────────────────────────
@login_required
@require_GET
def api_forex(request):
    key = _finnhub_key()
    if not key:
        return JsonResponse({'ok': False, 'error': 'API key de Finnhub no configurada.'}, status=503)

    results = []
    for pair in FOREX_PAIRS:
        base, quote = pair.split('/')
        finnhub_sym = f'OANDA:{base}_{quote}'
        try:
            q = requests.get(
                'https://finnhub.io/api/v1/quote',
                params={'symbol': finnhub_sym, 'token': key},
                timeout=8
            ).json()

            price = _fmt(q.get('c', 0), 5)
            prev  = _fmt(q.get('pc', 0), 5)
            if price == 0:
                continue

            chg_usd = round(price - prev, 5)
            chg_pct = round((chg_usd / prev * 100) if prev else 0, 4)
            spread  = round(abs(_fmt(q.get('h', price), 5) - _fmt(q.get('l', price), 5)) * 10000, 1)

            results.append({
                'pair':    pair,
                'base':    base,
                'quote':   quote,
                'price':   price,
                'buy':     round(price + 0.00002, 5),
                'sell':    round(price - 0.00002, 5),
                'spread':  spread,
                'chg_usd': chg_usd,
                'chg_pct': chg_pct,
                'high':    _fmt(q.get('h', price), 5),
                'low':     _fmt(q.get('l', price), 5),
            })
        except Exception as e:
            logger.warning(f'Forex {pair} error: {e}')

    if not results:
        return JsonResponse({'ok': False, 'error': 'No se pudieron cargar pares Forex.'}, status=502)

    return JsonResponse({'ok': True, 'data': results})


# ─────────────────────────────────────────────
# API — INDICES  (Finnhub)
# ─────────────────────────────────────────────
@login_required
@require_GET
def api_indices(request):
    key = _finnhub_key()
    if not key:
        return JsonResponse({'ok': False, 'error': 'API key de Finnhub no configurada.'}, status=503)

    results = []
    for idx in INDICES_LIST:
        try:
            q = requests.get(
                'https://finnhub.io/api/v1/quote',
                params={'symbol': idx['finnhub'], 'token': key},
                timeout=8
            ).json()

            price = _fmt(q.get('c', 0), 2)
            prev  = _fmt(q.get('pc', 0), 2)
            if price == 0:
                continue

            chg_usd = round(price - prev, 2)
            chg_pct = round((chg_usd / prev * 100) if prev else 0, 2)

            results.append({
                'symbol':  idx['symbol'],
                'name':    idx['name'],
                'price':   price,
                'prev':    prev,
                'chg_usd': chg_usd,
                'chg_pct': chg_pct,
                'high':    _fmt(q.get('h', 0), 2),
                'low':     _fmt(q.get('l', 0), 2),
                'open':    _fmt(q.get('o', 0), 2),
            })
        except Exception as e:
            logger.warning(f'Index {idx["symbol"]} error: {e}')

    if not results:
        return JsonResponse({'ok': False, 'error': 'No se pudieron cargar índices.'}, status=502)

    return JsonResponse({'ok': True, 'data': results})


# ─────────────────────────────────────────────
# API legacy — compatibilidad con ticker
# ─────────────────────────────────────────────
@login_required
@require_GET
def api_prices(request):
    asset_type = request.GET.get('type', 'crypto')
    assets = Asset.objects.filter(asset_type=asset_type, is_active=True).order_by('rank')[:50]
    data = [{
        'symbol': a.symbol, 'name': a.name,
        'price': float(a.current_price),
        'change_pct_24h': float(a.price_change_pct_24h),
        'image_url': a.image_url,
    } for a in assets]
    return JsonResponse({'data': data})


@login_required
def fetch_market_data(request):
    """Legacy — redirige a api_crypto para compatibilidad."""
    return api_crypto(request)
