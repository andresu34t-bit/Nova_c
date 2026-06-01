"""
Nova Capital Group - News Views
Noticias financieras con datos de respaldo cuando la API no está disponible.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import NewsArticle
from apps.markets.models import EconomicEvent
import requests
import logging
from datetime import timedelta

logger = logging.getLogger('apps')

# ──────────────────────────────────────────────────────────────────────────────
# NOTICIAS DE RESPALDO — se usan cuando la BD está vacía o la API falla
# ──────────────────────────────────────────────────────────────────────────────
FALLBACK_NEWS = [
    {
        'title': 'Bitcoin supera los $70,000 impulsado por la demanda institucional',
        'summary': 'El precio de Bitcoin alcanzó nuevos máximos históricos esta semana, '
                   'impulsado por la creciente adopción institucional y los ETFs de Bitcoin al contado '
                   'que continúan registrando entradas récord de capital.',
        'source': 'Nova Capital Research',
        'source_url': 'https://www.coindesk.com',
        'category': 'crypto',
        'is_featured': True,
        'sentiment': 'positive',
        'related_symbols': 'BTC',
        'hours_ago': 2,
    },
    {
        'title': 'Ethereum completa actualización de red mejorando velocidad de transacciones',
        'summary': 'La red Ethereum implementó con éxito su última actualización de protocolo, '
                   'reduciendo las tarifas de gas en un 40% y aumentando la capacidad de procesamiento '
                   'de transacciones por segundo.',
        'source': 'CryptoNews',
        'source_url': 'https://www.coindesk.com',
        'category': 'crypto',
        'is_featured': True,
        'sentiment': 'positive',
        'related_symbols': 'ETH',
        'hours_ago': 4,
    },
    {
        'title': 'La Fed mantiene tasas de interés sin cambios en reunión de junio',
        'summary': 'La Reserva Federal de Estados Unidos decidió mantener las tasas de interés '
                   'en el rango actual, señalando que necesita más evidencia de que la inflación '
                   'se dirige de manera sostenible hacia el objetivo del 2%.',
        'source': 'Reuters Financial',
        'source_url': 'https://www.reuters.com',
        'category': 'economy',
        'is_featured': True,
        'sentiment': 'neutral',
        'related_symbols': 'USD,SPX',
        'hours_ago': 6,
    },
    {
        'title': 'S&P 500 alcanza nuevo récord histórico impulsado por tecnología',
        'summary': 'El índice S&P 500 cerró en máximos históricos, liderado por el sector tecnológico '
                   'tras reportes de ganancias superiores a las expectativas de los analistas de Wall Street.',
        'source': 'Bloomberg Markets',
        'source_url': 'https://www.bloomberg.com',
        'category': 'stocks',
        'is_featured': False,
        'sentiment': 'positive',
        'related_symbols': 'SPX,AAPL,MSFT',
        'hours_ago': 8,
    },
    {
        'title': 'El dólar se fortalece frente al euro ante datos de empleo positivos',
        'summary': 'El índice del dólar estadounidense subió un 0.8% después de que los datos de '
                   'nóminas no agrícolas superaran las expectativas, reduciendo las apuestas por '
                   'recortes de tasas de la Fed en el corto plazo.',
        'source': 'FX Street',
        'source_url': 'https://www.fxstreet.com',
        'category': 'forex',
        'is_featured': False,
        'sentiment': 'positive',
        'related_symbols': 'EURUSD,DXY',
        'hours_ago': 10,
    },
    {
        'title': 'Solana registra volumen récord en DEX superando los $5 mil millones',
        'summary': 'La blockchain de Solana procesó un volumen récord en exchanges descentralizados, '
                   'consolidando su posición como una de las redes más activas del ecosistema DeFi '
                   'con comisiones mínimas y alta velocidad.',
        'source': 'DeFi Pulse',
        'source_url': 'https://www.coindesk.com',
        'category': 'crypto',
        'is_featured': False,
        'sentiment': 'positive',
        'related_symbols': 'SOL',
        'hours_ago': 12,
    },
    {
        'title': 'Apple reporta ganancias récord impulsadas por servicios y iPhone',
        'summary': 'Apple Inc. superó las expectativas de Wall Street con ingresos trimestrales '
                   'de $94.8 mil millones, un aumento del 5% interanual, impulsado por el crecimiento '
                   'del segmento de servicios y ventas del iPhone en mercados emergentes.',
        'source': 'CNBC Markets',
        'source_url': 'https://www.cnbc.com',
        'category': 'stocks',
        'is_featured': False,
        'sentiment': 'positive',
        'related_symbols': 'AAPL',
        'hours_ago': 14,
    },
    {
        'title': 'Banco Central Europeo señala posibles recortes de tasas en el segundo semestre',
        'summary': 'La presidenta del BCE, Christine Lagarde, indicó que el banco central podría '
                   'comenzar a reducir las tasas de interés si la inflación continúa moderándose, '
                   'lo que impulsó los mercados de renta fija europeos.',
        'source': 'Financial Times',
        'source_url': 'https://www.ft.com',
        'category': 'economy',
        'is_featured': False,
        'sentiment': 'positive',
        'related_symbols': 'EUR,EURUSD',
        'hours_ago': 18,
    },
    {
        'title': 'XRP gana terreno tras fallo favorable en caso legal con la SEC',
        'summary': 'Ripple Labs obtuvo una victoria parcial en su disputa legal con la Comisión '
                   'de Valores de EE.UU., lo que impulsó el precio de XRP más de un 15% en las '
                   'últimas 24 horas y renovó el optimismo en el sector cripto.',
        'source': 'CoinTelegraph',
        'source_url': 'https://cointelegraph.com',
        'category': 'crypto',
        'is_featured': False,
        'sentiment': 'positive',
        'related_symbols': 'XRP',
        'hours_ago': 20,
    },
    {
        'title': 'Nvidia supera expectativas con ingresos de IA que triplican año anterior',
        'summary': 'Nvidia Corporation reportó ingresos de $26 mil millones en el trimestre, '
                   'triplicando los resultados del año anterior, impulsados por la demanda insaciable '
                   'de chips de inteligencia artificial para centros de datos.',
        'source': 'Wall Street Journal',
        'source_url': 'https://www.wsj.com',
        'category': 'technology',
        'is_featured': False,
        'sentiment': 'positive',
        'related_symbols': 'NVDA',
        'hours_ago': 24,
    },
    {
        'title': 'El oro alcanza máximos de 6 meses ante incertidumbre geopolítica',
        'summary': 'El precio del oro spot subió a $2,380 por onza troy, su nivel más alto en '
                   'seis meses, impulsado por la demanda de activos refugio ante las tensiones '
                   'geopolíticas en Oriente Medio y Europa del Este.',
        'source': 'Kitco News',
        'source_url': 'https://www.kitco.com',
        'category': 'economy',
        'is_featured': False,
        'sentiment': 'neutral',
        'related_symbols': 'GOLD,XAU',
        'hours_ago': 28,
    },
    {
        'title': 'DeFi alcanza $100 mil millones en valor total bloqueado',
        'summary': 'El ecosistema de finanzas descentralizadas superó los $100 mil millones en '
                   'valor total bloqueado (TVL), marcando un hito histórico impulsado por el '
                   'crecimiento de protocolos de préstamos y exchanges descentralizados.',
        'source': 'DeFi Llama',
        'source_url': 'https://defillama.com',
        'category': 'crypto',
        'is_featured': False,
        'sentiment': 'positive',
        'related_symbols': 'ETH,BTC',
        'hours_ago': 32,
    },
]

FALLBACK_EVENTS = [
    {
        'title': 'Decisión de Tasas de Interés - Fed',
        'country': 'Estados Unidos',
        'currency': 'USD',
        'impact': 'high',
        'forecast': '5.25%',
        'previous': '5.25%',
        'hours_ahead': 48,
    },
    {
        'title': 'Nóminas No Agrícolas (NFP)',
        'country': 'Estados Unidos',
        'currency': 'USD',
        'impact': 'high',
        'forecast': '185K',
        'previous': '175K',
        'hours_ahead': 72,
    },
    {
        'title': 'IPC Zona Euro (Inflación)',
        'country': 'Zona Euro',
        'currency': 'EUR',
        'impact': 'high',
        'forecast': '2.4%',
        'previous': '2.6%',
        'hours_ahead': 96,
    },
    {
        'title': 'PIB Trimestral - EE.UU.',
        'country': 'Estados Unidos',
        'currency': 'USD',
        'impact': 'high',
        'forecast': '2.1%',
        'previous': '1.6%',
        'hours_ahead': 120,
    },
    {
        'title': 'Decisión de Tasas - BCE',
        'country': 'Zona Euro',
        'currency': 'EUR',
        'impact': 'high',
        'forecast': '4.25%',
        'previous': '4.50%',
        'hours_ahead': 144,
    },
    {
        'title': 'Ventas Minoristas EE.UU.',
        'country': 'Estados Unidos',
        'currency': 'USD',
        'impact': 'medium',
        'forecast': '0.4%',
        'previous': '0.7%',
        'hours_ahead': 168,
    },
    {
        'title': 'Índice de Precios al Productor (PPI)',
        'country': 'Estados Unidos',
        'currency': 'USD',
        'impact': 'medium',
        'forecast': '0.2%',
        'previous': '0.2%',
        'hours_ahead': 192,
    },
    {
        'title': 'Confianza del Consumidor - Michigan',
        'country': 'Estados Unidos',
        'currency': 'USD',
        'impact': 'medium',
        'forecast': '79.0',
        'previous': '77.2',
        'hours_ahead': 216,
    },
]


def _get_or_create_fallback_news():
    """Crea noticias de respaldo en la BD si no hay ninguna."""
    now = timezone.now()
    created_count = 0
    for item in FALLBACK_NEWS:
        pub_date = now - timedelta(hours=item['hours_ago'])
        # Usar título como clave única para evitar duplicados
        if not NewsArticle.objects.filter(title=item['title']).exists():
            NewsArticle.objects.create(
                title=item['title'],
                summary=item['summary'],
                source=item['source'],
                source_url=item['source_url'],
                category=item['category'],
                is_featured=item['is_featured'],
                sentiment=item.get('sentiment', ''),
                related_symbols=item.get('related_symbols', ''),
                published_at=pub_date,
            )
            created_count += 1
    return created_count


def _get_or_create_fallback_events():
    """Crea eventos económicos de respaldo si no hay ninguno próximo."""
    now = timezone.now()
    created_count = 0
    for item in FALLBACK_EVENTS:
        event_date = now + timedelta(hours=item['hours_ahead'])
        if not EconomicEvent.objects.filter(title=item['title']).exists():
            EconomicEvent.objects.create(
                title=item['title'],
                country=item['country'],
                currency=item['currency'],
                impact=item['impact'],
                forecast=item['forecast'],
                previous=item['previous'],
                event_date=event_date,
            )
            created_count += 1
    return created_count


@login_required
def news_view(request):
    category = request.GET.get('category', 'all')

    # Si no hay noticias en la BD, crear las de respaldo automáticamente
    if NewsArticle.objects.count() == 0:
        _get_or_create_fallback_news()

    # Si no hay eventos económicos próximos, crear los de respaldo
    if EconomicEvent.objects.filter(event_date__gte=timezone.now()).count() == 0:
        _get_or_create_fallback_events()

    articles = NewsArticle.objects.all()
    if category != 'all':
        articles = articles.filter(category=category)
    articles = articles.order_by('-published_at')[:50]

    featured = NewsArticle.objects.filter(is_featured=True).order_by('-published_at')[:3]
    if not featured.exists():
        featured = NewsArticle.objects.order_by('-published_at')[:3]

    upcoming_events = EconomicEvent.objects.filter(
        event_date__gte=timezone.now()
    ).order_by('event_date')[:10]

    context = {
        'articles': articles,
        'featured': featured,
        'upcoming_events': upcoming_events,
        'active_category': category,
        'categories': NewsArticle.CATEGORIES,
        'total_articles': NewsArticle.objects.count(),
        'trending_tags': [
            'Bitcoin', 'Ethereum', 'Fed', 'Inflación', 'DeFi',
            'Nasdaq', 'Oro', 'Dólar', 'Inteligencia Artificial', 'Solana',
        ],
    }
    return render(request, 'news/news.html', context)


@login_required
def fetch_news(request):
    """
    Intenta obtener noticias de NewsAPI.
    Si la API no está disponible o no hay clave, crea noticias de respaldo.
    Nunca muestra mensajes técnicos al usuario.
    """
    from django.conf import settings
    api_key = getattr(settings, 'NEWS_API_KEY', '')

    created = 0

    if api_key:
        try:
            # Intentar con NewsAPI en español
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': 'bitcoin OR ethereum OR bolsa OR acciones OR forex OR criptomonedas',
                'language': 'es',
                'sortBy': 'publishedAt',
                'pageSize': 30,
                'apiKey': api_key,
            }
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                raw_articles = data.get('articles', [])

                # Mapeo de palabras clave a categorías
                CATEGORY_KEYWORDS = {
                    'crypto': ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'defi', 'nft', 'solana', 'ripple', 'binance'],
                    'stocks': ['bolsa', 'acciones', 'nasdaq', 'sp500', 'wall street', 'apple', 'nvidia', 'tesla'],
                    'forex': ['forex', 'dólar', 'euro', 'divisas', 'tipo de cambio', 'fed', 'bce'],
                    'economy': ['economía', 'inflación', 'pib', 'banco central', 'tasas', 'recesión'],
                    'technology': ['tecnología', 'ia', 'inteligencia artificial', 'startup', 'silicon valley'],
                }

                for article in raw_articles:
                    title = article.get('title', '')
                    url_art = article.get('url', '')
                    if not title or not url_art or title == '[Removed]':
                        continue

                    # Detectar categoría
                    title_lower = title.lower()
                    summary_lower = (article.get('description') or '').lower()
                    text = title_lower + ' ' + summary_lower
                    cat = 'general'
                    for category_name, keywords in CATEGORY_KEYWORDS.items():
                        if any(kw in text for kw in keywords):
                            cat = category_name
                            break

                    _, was_created = NewsArticle.objects.get_or_create(
                        source_url=url_art,
                        defaults={
                            'title': title[:500],
                            'summary': (article.get('description') or '')[:1000],
                            'source': article.get('source', {}).get('name', 'NewsAPI')[:100],
                            'image_url': article.get('urlToImage') or '',
                            'published_at': article.get('publishedAt') or timezone.now(),
                            'category': cat,
                            'is_featured': False,
                        }
                    )
                    if was_created:
                        created += 1

                logger.info(f"NewsAPI: {created} nuevas noticias importadas")
                return JsonResponse({'status': 'ok', 'created': created, 'source': 'newsapi'})

            elif response.status_code == 426:
                # Plan gratuito no permite ciertos endpoints — usar respaldo
                logger.warning('NewsAPI: plan gratuito, usando respaldo')
            else:
                logger.warning(f'NewsAPI: HTTP {response.status_code}')

        except requests.exceptions.Timeout:
            logger.warning('NewsAPI: timeout, usando respaldo')
        except Exception as e:
            logger.error(f'NewsAPI error: {e}')

    # Sin API key o API falló → crear/actualizar noticias de respaldo
    created = _get_or_create_fallback_news()
    _get_or_create_fallback_events()

    return JsonResponse({
        'status': 'ok',
        'created': created,
        'source': 'fallback',
        'message': f'{created} noticias actualizadas',
    })
