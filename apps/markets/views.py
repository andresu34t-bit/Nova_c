"""
Nova Capital Group - Markets Views
Fuentes: CoinGecko (crypto) + Stooq CSV (stocks/forex/indices, sin key)
         Finnhub como fuente secundaria si tiene key configurada.
Caché en memoria + fallback a datos guardados — nunca muestra errores de API key.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings
from apps.trading.models import Asset, Watchlist
import requests, time, logging, csv, io

logger = logging.getLogger('apps')

# ─────────────────────────────────────────────
# CACHÉ EN MEMORIA  (sobrevive el proceso, no persiste entre workers)
# ─────────────────────────────────────────────
_CACHE = {}          # {'crypto': {'ts': float, 'data': list}, ...}
_CACHE_TTL = 60      # segundos

def _cache_get(key):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry['ts']) < _CACHE_TTL:
        logger.debug(f'[markets] cache HIT: {key}')
        return entry['data']
    return None

def _cache_set(key, data):
    _CACHE[key] = {'ts': time.time(), 'data': data}
    logger.info(f'[markets] cache SET: {key} ({len(data)} items)')

def _cache_stale(key):
    """Devuelve datos aunque estén expirados (fallback)."""
    entry = _CACHE.get(key)
    return entry['data'] if entry else None


# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
STOCK_SYMBOLS = ['AAPL','MSFT','NVDA','AMZN','GOOGL','META','TSLA','NFLX','KO','JPM']

STOCK_META = {
    'AAPL': ('Apple Inc.',       'https://logo.clearbit.com/apple.com'),
    'MSFT': ('Microsoft',        'https://logo.clearbit.com/microsoft.com'),
    'NVDA': ('Nvidia',           'https://logo.clearbit.com/nvidia.com'),
    'AMZN': ('Amazon',           'https://logo.clearbit.com/amazon.com'),
    'GOOGL': ('Alphabet',        'https://logo.clearbit.com/google.com'),
    'META': ('Meta Platforms',   'https://logo.clearbit.com/meta.com'),
    'TSLA': ('Tesla',            'https://logo.clearbit.com/tesla.com'),
    'NFLX': ('Netflix',          'https://logo.clearbit.com/netflix.com'),
    'KO':   ('Coca-Cola',        'https://logo.clearbit.com/coca-cola.com'),
    'JPM':  ('JPMorgan Chase',   'https://logo.clearbit.com/jpmorganchase.com'),
}

FOREX_PAIRS = [
    ('EUR','USD'),('GBP','USD'),('USD','JPY'),('USD','CHF'),
    ('AUD','USD'),('NZD','USD'),('USD','CAD'),('EUR','JPY'),
    ('GBP','JPY'),('EUR','GBP'),
]

INDICES_META = [
    ('SPX',  'S&P 500',     '^SPX'),
    ('NDX',  'NASDAQ 100',  '^NDX'),
    ('DJI',  'Dow Jones',   '^DJI'),
    ('RUT',  'Russell 2000','^RUT'),
    ('DAX',  'DAX',         '^DAX'),
    ('FTSE', 'FTSE 100',    '^FTS'),
    ('CAC',  'CAC 40',      '^CAC'),
    ('N225', 'Nikkei 225',  '^NKX'),
    ('HSI',  'Hang Seng',   '^HIS'),
    ('IBEX', 'IBEX 35',     '^IBC'),
]

# Datos de referencia estáticos (se usan como fallback de último recurso)
_STATIC_STOCKS = [
    {'symbol':'AAPL','price':213.55,'chg_pct':0.85,'chg_usd':1.80,'open':212.10,'high':214.20,'low':211.50,'prev':211.75},
    {'symbol':'MSFT','price':415.20,'chg_pct':1.15,'chg_usd':4.72,'open':411.80,'high':416.90,'low':410.20,'prev':410.48},
    {'symbol':'NVDA','price':875.40,'chg_pct':2.85,'chg_usd':24.24,'open':855.00,'high':880.10,'low':852.30,'prev':851.16},
    {'symbol':'AMZN','price':192.45,'chg_pct':0.65,'chg_usd':1.24,'open':191.20,'high':193.80,'low':190.50,'prev':191.21},
    {'symbol':'GOOGL','price':175.80,'chg_pct':0.65,'chg_usd':1.14,'open':174.50,'high':176.90,'low':173.80,'prev':174.66},
    {'symbol':'META','price':525.30,'chg_pct':1.20,'chg_usd':6.23,'open':520.10,'high':527.40,'low':518.90,'prev':519.07},
    {'symbol':'TSLA','price':178.20,'chg_pct':-1.45,'chg_usd':-2.62,'open':181.50,'high':182.30,'low':177.10,'prev':180.82},
    {'symbol':'NFLX','price':698.50,'chg_pct':0.92,'chg_usd':6.37,'open':693.20,'high':701.30,'low':692.10,'prev':692.13},
    {'symbol':'KO',  'price':62.85,'chg_pct':0.32,'chg_usd':0.20,'open':62.60,'high':63.10,'low':62.40,'prev':62.65},
    {'symbol':'JPM', 'price':220.40,'chg_pct':0.58,'chg_usd':1.27,'open':219.20,'high':221.50,'low':218.90,'prev':219.13},
]

_STATIC_FOREX = [
    {'pair':'EUR/USD','base':'EUR','quote':'USD','price':1.08520,'chg_pct':0.12,'chg_usd':0.00130},
    {'pair':'GBP/USD','base':'GBP','quote':'USD','price':1.27340,'chg_pct':-0.08,'chg_usd':-0.00102},
    {'pair':'USD/JPY','base':'USD','quote':'JPY','price':149.850,'chg_pct':0.21,'chg_usd':0.31500},
    {'pair':'USD/CHF','base':'USD','quote':'CHF','price':0.89120,'chg_pct':0.05,'chg_usd':0.00045},
    {'pair':'AUD/USD','base':'AUD','quote':'USD','price':0.65480,'chg_pct':-0.15,'chg_usd':-0.00098},
    {'pair':'NZD/USD','base':'NZD','quote':'USD','price':0.60210,'chg_pct':0.08,'chg_usd':0.00048},
    {'pair':'USD/CAD','base':'USD','quote':'CAD','price':1.36850,'chg_pct':0.10,'chg_usd':0.00137},
    {'pair':'EUR/JPY','base':'EUR','quote':'JPY','price':162.540,'chg_pct':0.33,'chg_usd':0.53500},
    {'pair':'GBP/JPY','base':'GBP','quote':'JPY','price':190.820,'chg_pct':0.14,'chg_usd':0.26600},
    {'pair':'EUR/GBP','base':'EUR','quote':'GBP','price':0.85260,'chg_pct':0.20,'chg_usd':0.00170},
]

_STATIC_INDICES = [
    {'symbol':'SPX', 'name':'S&P 500',     'price':5308.13,'chg_usd':42.10,'chg_pct':0.80,'open':5270.00,'high':5315.00,'low':5265.00,'prev':5266.03},
    {'symbol':'NDX', 'name':'NASDAQ 100',  'price':18680.50,'chg_usd':210.30,'chg_pct':1.14,'open':18480.00,'high':18720.00,'low':18460.00,'prev':18470.20},
    {'symbol':'DJI', 'name':'Dow Jones',   'price':39150.20,'chg_usd':185.40,'chg_pct':0.48,'open':38970.00,'high':39200.00,'low':38940.00,'prev':38964.80},
    {'symbol':'RUT', 'name':'Russell 2000','price':2084.30,'chg_usd':-12.50,'chg_pct':-0.60,'open':2098.00,'high':2101.00,'low':2080.00,'prev':2096.80},
    {'symbol':'DAX', 'name':'DAX',         'price':18450.80,'chg_usd':95.20,'chg_pct':0.52,'open':18360.00,'high':18480.00,'low':18340.00,'prev':18355.60},
    {'symbol':'FTSE','name':'FTSE 100',    'price':8280.40,'chg_usd':35.10,'chg_pct':0.43,'open':8248.00,'high':8295.00,'low':8242.00,'prev':8245.30},
    {'symbol':'CAC', 'name':'CAC 40',      'price':7980.20,'chg_usd':28.40,'chg_pct':0.36,'open':7954.00,'high':7990.00,'low':7948.00,'prev':7951.80},
    {'symbol':'N225','name':'Nikkei 225',  'price':38500.60,'chg_usd':320.50,'chg_pct':0.84,'open':38200.00,'high':38560.00,'low':38180.00,'prev':38180.10},
    {'symbol':'HSI', 'name':'Hang Seng',   'price':17850.30,'chg_usd':-120.40,'chg_pct':-0.67,'open':17980.00,'high':18010.00,'low':17820.00,'prev':17970.70},
    {'symbol':'IBEX','name':'IBEX 35',     'price':11240.50,'chg_usd':55.30,'chg_pct':0.49,'open':11188.00,'high':11260.00,'low':11180.00,'prev':11185.20},
]


def _fmt(val, decimals=2):
    try:
        return round(float(val or 0), decimals)
    except Exception:
        return 0.0


def _finnhub_key():
    return getattr(settings, 'FINNHUB_API_KEY', '') or ''


# ─────────────────────────────────────────────
# MAIN VIEW
# ─────────────────────────────────────────────
@login_required
def markets_overview(request):
    active_tab = request.GET.get('tab', 'crypto')
    return render(request, 'markets/overview.html', {'active_tab': active_tab})


@login_required
def asset_detail(request, symbol):
    asset = get_object_or_404(Asset, symbol=symbol.upper())
    in_watchlist = Watchlist.objects.filter(user=request.user, asset=asset).exists()
    return render(request, 'markets/asset_detail.html', {'asset': asset, 'in_watchlist': in_watchlist})


# ─────────────────────────────────────────────
# API — CRYPTO
# Fuente 1: CoinGecko  |  Fallback: DB (Asset)
# ─────────────────────────────────────────────
@login_required
@require_GET
def api_crypto(request):
    cached = _cache_get('crypto')
    if cached:
        return JsonResponse({'ok': True, 'data': cached, 'source': 'cache'})

    data = _fetch_coingecko()
    if data:
        _cache_set('crypto', data)
        _sync_crypto_assets(data)
        return JsonResponse({'ok': True, 'data': data, 'source': 'coingecko'})

    # Fallback: datos de la DB
    data = _crypto_from_db()
    if data:
        logger.warning('[markets] crypto: usando fallback DB')
        _cache_set('crypto', data)
        return JsonResponse({'ok': True, 'data': data, 'source': 'db'})

    # Fallback: caché expirada
    stale = _cache_stale('crypto')
    if stale:
        logger.warning('[markets] crypto: usando caché expirada')
        return JsonResponse({'ok': True, 'data': stale, 'source': 'stale_cache'})

    return JsonResponse({'ok': False, 'error': 'No se pudieron cargar criptomonedas. Reintenta en unos segundos.'}, status=503)


def _fetch_coingecko():
    try:
        url = 'https://api.coingecko.com/api/v3/coins/markets'
        params = {'vs_currency':'usd','order':'market_cap_desc','per_page':50,'page':1,'sparkline':False,'price_change_percentage':'24h'}
        key = getattr(settings, 'COINGECKO_API_KEY', '')
        headers = {'x-cg-demo-api-key': key} if key else {}
        r = requests.get(url, params=params, headers=headers, timeout=12)
        if r.status_code == 429:
            logger.warning('[markets] CoinGecko 429 rate limit')
            return None
        r.raise_for_status()
        coins = r.json()
        data = []
        for c in coins:
            data.append({
                'rank': c.get('market_cap_rank', 0),
                'symbol': c['symbol'].upper(),
                'name': c['name'],
                'image': c.get('image', ''),
                'price': _fmt(c.get('current_price', 0), 8),
                'chg_pct': _fmt(c.get('price_change_percentage_24h', 0), 2),
                'chg_usd': _fmt(c.get('price_change_24h', 0), 6),
                'volume': _fmt(c.get('total_volume', 0), 0),
                'market_cap': _fmt(c.get('market_cap', 0), 0),
                'high': _fmt(c.get('high_24h', 0), 8),
                'low': _fmt(c.get('low_24h', 0), 8),
                'coingecko_id': c.get('id', ''),
            })
        logger.info(f'[markets] CoinGecko OK: {len(data)} coins')
        return data
    except Exception as e:
        logger.error(f'[markets] CoinGecko error: {e}')
        return None


def _crypto_from_db():
    try:
        assets = Asset.objects.filter(asset_type='crypto', is_active=True).order_by('rank')[:50]
        if not assets.exists():
            return None
        return [{
            'rank': a.rank, 'symbol': a.symbol, 'name': a.name,
            'image': a.image_url,
            'price': float(a.current_price),
            'chg_pct': float(a.price_change_pct_24h),
            'chg_usd': float(a.price_change_24h),
            'volume': float(a.volume_24h),
            'market_cap': float(a.market_cap),
            'high': float(a.high_24h),
            'low': float(a.low_24h),
            'coingecko_id': a.coingecko_id,
        } for a in assets]
    except Exception as e:
        logger.error(f'[markets] crypto DB fallback error: {e}')
        return None


def _sync_crypto_assets(data):
    try:
        for c in data[:20]:
            Asset.objects.update_or_create(
                symbol=c['symbol'],
                defaults={
                    'name': c['name'], 'asset_type': 'crypto',
                    'current_price': c['price'], 'price_change_24h': c['chg_usd'],
                    'price_change_pct_24h': c['chg_pct'], 'volume_24h': c['volume'],
                    'market_cap': c['market_cap'], 'high_24h': c['high'],
                    'low_24h': c['low'], 'image_url': c['image'],
                    'coingecko_id': c['coingecko_id'], 'rank': c['rank'], 'is_active': True,
                }
            )
    except Exception:
        pass


# ─────────────────────────────────────────────
# STOOQ CSV FETCHER  (sin API key, gratuito)
# ─────────────────────────────────────────────
def _stooq_quote(symbol):
    """
    Descarga la última cotización de Stooq en formato CSV.
    Ejemplo: https://stooq.com/q/l/?s=aapl.us&f=sd2t2ohlcv&h&e=csv
    Devuelve dict con open/high/low/close/volume o None si falla.
    """
    try:
        url = f'https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv'
        r = requests.get(url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        row = next(reader, None)
        if not row:
            return None
        close = float(row.get('Close') or row.get('close') or 0)
        if close == 0:
            return None
        open_  = float(row.get('Open')   or row.get('open')   or close)
        high   = float(row.get('High')   or row.get('high')   or close)
        low    = float(row.get('Low')    or row.get('low')    or close)
        vol    = float(row.get('Volume') or row.get('volume') or 0)
        return {'close': close, 'open': open_, 'high': high, 'low': low, 'volume': vol}
    except Exception as e:
        logger.debug(f'[markets] stooq {symbol} error: {e}')
        return None


# ─────────────────────────────────────────────
# FINNHUB QUOTE (solo si tiene key)
# ─────────────────────────────────────────────
def _finnhub_quote(symbol):
    key = _finnhub_key()
    if not key:
        return None
    try:
        r = requests.get(
            'https://finnhub.io/api/v1/quote',
            params={'symbol': symbol, 'token': key},
            timeout=8
        )
        r.raise_for_status()
        q = r.json()
        price = float(q.get('c') or 0)
        if price == 0:
            return None
        prev = float(q.get('pc') or price)
        return {
            'close': price,
            'open':  float(q.get('o') or price),
            'high':  float(q.get('h') or price),
            'low':   float(q.get('l') or price),
            'volume': 0,
            'prev': prev,
            'chg_usd': float(q.get('d') or (price - prev)),
            'chg_pct': float(q.get('dp') or 0),
        }
    except Exception as e:
        logger.debug(f'[markets] finnhub {symbol} error: {e}')
        return None


# ─────────────────────────────────────────────
# API — STOCKS
# Fuente 1: Stooq (.us)  |  Fuente 2: Finnhub  |  Fallback: estático
# ─────────────────────────────────────────────
@login_required
@require_GET
def api_stocks(request):
    cached = _cache_get('stocks')
    if cached:
        return JsonResponse({'ok': True, 'data': cached, 'source': 'cache'})

    results = []
    for sym in STOCK_SYMBOLS:
        name, logo = STOCK_META.get(sym, (sym, ''))
        q = _stooq_quote(sym.lower() + '.us') or _finnhub_quote(sym)
        if q:
            close = q['close']
            prev  = q.get('prev', close)
            chg_usd = _fmt(q.get('chg_usd', close - prev), 2)
            chg_pct = _fmt(q.get('chg_pct', ((close-prev)/prev*100) if prev else 0), 2)
            results.append({
                'symbol': sym, 'name': name, 'logo': logo,
                'price':   _fmt(close, 2),
                'prev':    _fmt(prev, 2),
                'chg_usd': chg_usd,
                'chg_pct': chg_pct,
                'open':    _fmt(q['open'], 2),
                'high':    _fmt(q['high'], 2),
                'low':     _fmt(q['low'],  2),
                'volume':  _fmt(q['volume'], 0),
                'market_cap': 0,
            })
        else:
            logger.warning(f'[markets] stocks: {sym} sin datos de API, usando estático')

    if results:
        _cache_set('stocks', results)
        return JsonResponse({'ok': True, 'data': results, 'source': 'stooq'})

    # Fallback estático
    logger.warning('[markets] stocks: usando datos estáticos')
    static = _build_static_stocks()
    _cache_set('stocks', static)
    return JsonResponse({'ok': True, 'data': static, 'source': 'static'})


def _build_static_stocks():
    out = []
    for s in _STATIC_STOCKS:
        name, logo = STOCK_META.get(s['symbol'], (s['symbol'], ''))
        out.append({**s, 'name': name, 'logo': logo,
                    'prev': s['price'] - s['chg_usd'],
                    'volume': 0, 'market_cap': 0})
    return out


# ─────────────────────────────────────────────
# API — FOREX
# Fuente 1: Stooq (eur/usd.fx)  |  Fuente 2: exchangerate-api (libre)
# Fallback: estático
# ─────────────────────────────────────────────
@login_required
@require_GET
def api_forex(request):
    cached = _cache_get('forex')
    if cached:
        return JsonResponse({'ok': True, 'data': cached, 'source': 'cache'})

    results = []
    for base, quote in FOREX_PAIRS:
        stooq_sym = f'{base.lower()}{quote.lower()}.fx'
        q = _stooq_quote(stooq_sym)
        if q:
            price   = q['close']
            prev    = q['open']   # Stooq no da precio previo, usamos open como referencia
            high    = q['high']
            low     = q['low']
            chg_usd = _fmt(price - prev, 5)
            chg_pct = _fmt((chg_usd / prev * 100) if prev else 0, 4)
            spread  = _fmt(abs(high - low) * 10000, 1)
            results.append({
                'pair':    f'{base}/{quote}',
                'base':    base, 'quote': quote,
                'price':   _fmt(price, 5),
                'buy':     _fmt(price + 0.00002, 5),
                'sell':    _fmt(price - 0.00002, 5),
                'spread':  spread,
                'chg_usd': chg_usd,
                'chg_pct': chg_pct,
                'high':    _fmt(high, 5),
                'low':     _fmt(low, 5),
            })
        else:
            logger.warning(f'[markets] forex: {base}/{quote} sin datos de Stooq')

    if results:
        _cache_set('forex', results)
        return JsonResponse({'ok': True, 'data': results, 'source': 'stooq'})

    # Fallback a exchangerate-api (solo precios spot, sin high/low)
    results = _fetch_exchangerate_forex()
    if results:
        _cache_set('forex', results)
        return JsonResponse({'ok': True, 'data': results, 'source': 'exchangerate'})

    # Fallback estático
    logger.warning('[markets] forex: usando datos estáticos')
    static = _build_static_forex()
    _cache_set('forex', static)
    return JsonResponse({'ok': True, 'data': static, 'source': 'static'})


def _fetch_exchangerate_forex():
    """open.er-api.com — gratuito, sin key."""
    try:
        r = requests.get('https://open.er-api.com/v6/latest/USD', timeout=8)
        r.raise_for_status()
        rates = r.json().get('rates', {})
        if not rates:
            return None
        results = []
        for base, quote in FOREX_PAIRS:
            if base == 'USD':
                price = 1.0 / rates.get(quote, 0) if rates.get(quote) else 0
            elif quote == 'USD':
                price = rates.get(base, 0)
            else:
                usd_base  = rates.get(base, 0)
                usd_quote = rates.get(quote, 0)
                price = (usd_base / usd_quote) if usd_quote else 0
            if price == 0:
                continue
            price = _fmt(price, 5)
            results.append({
                'pair': f'{base}/{quote}', 'base': base, 'quote': quote,
                'price': price,
                'buy':   _fmt(price + 0.00002, 5),
                'sell':  _fmt(price - 0.00002, 5),
                'spread': 0.4,
                'chg_usd': 0.0, 'chg_pct': 0.0,
                'high': price, 'low': price,
            })
        logger.info(f'[markets] exchangerate-api OK: {len(results)} pares')
        return results if results else None
    except Exception as e:
        logger.error(f'[markets] exchangerate-api error: {e}')
        return None


def _build_static_forex():
    return [{
        **f,
        'buy':  _fmt(f['price'] + 0.00002, 5),
        'sell': _fmt(f['price'] - 0.00002, 5),
        'spread': 0.4,
        'high': _fmt(f['price'] * 1.002, 5),
        'low':  _fmt(f['price'] * 0.998, 5),
    } for f in _STATIC_FOREX]


# ─────────────────────────────────────────────
# API — INDICES
# Fuente 1: Stooq  |  Fuente 2: Finnhub (si hay key)  |  Fallback: estático
# ─────────────────────────────────────────────
@login_required
@require_GET
def api_indices(request):
    cached = _cache_get('indices')
    if cached:
        return JsonResponse({'ok': True, 'data': cached, 'source': 'cache'})

    results = []
    for symbol, name, stooq_sym in INDICES_META:
        q = _stooq_quote(stooq_sym)
        if q:
            price   = q['close']
            prev    = q['open']
            chg_usd = _fmt(price - prev, 2)
            chg_pct = _fmt((chg_usd / prev * 100) if prev else 0, 2)
            results.append({
                'symbol': symbol, 'name': name,
                'price':   _fmt(price, 2),
                'prev':    _fmt(prev, 2),
                'chg_usd': chg_usd,
                'chg_pct': chg_pct,
                'open':    _fmt(q['open'], 2),
                'high':    _fmt(q['high'], 2),
                'low':     _fmt(q['low'],  2),
            })
        else:
            logger.warning(f'[markets] index: {symbol} sin datos de Stooq')

    if results:
        _cache_set('indices', results)
        return JsonResponse({'ok': True, 'data': results, 'source': 'stooq'})

    # Fallback estático
    logger.warning('[markets] indices: usando datos estáticos')
    _cache_set('indices', _STATIC_INDICES)
    return JsonResponse({'ok': True, 'data': _STATIC_INDICES, 'source': 'static'})


# ─────────────────────────────────────────────
# API LEGACY (compatibilidad ticker / trading)
# ─────────────────────────────────────────────
@login_required
@require_GET
def api_prices(request):
    asset_type = request.GET.get('type', 'crypto')
    assets = Asset.objects.filter(asset_type=asset_type, is_active=True).order_by('rank')[:50]
    return JsonResponse({'data': [{
        'symbol': a.symbol, 'name': a.name,
        'price': float(a.current_price),
        'change_pct_24h': float(a.price_change_pct_24h),
        'image_url': a.image_url,
    } for a in assets]})


@login_required
def fetch_market_data(request):
    return api_crypto(request)
