#!/usr/bin/env bash
# Nova Capital Group - Render Build Script
set -o errexit

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running migrations..."
python manage.py migrate --no-input

echo "==> Creating superuser admin..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
email = 'admin@novacapital.com'
password = 'Admin2024Nova!'
if not User.objects.filter(email=email).exists():
    u = User.objects.create_superuser(
        username='admin', email=email, password=password,
        first_name='Admin', last_name='Nova Capital',
    )
    u.balance = 50000
    u.email_verified = True
    u.account_type = 'institutional'
    u.save()
    print('Admin creado: ' + email)
else:
    u = User.objects.get(email=email)
    u.is_staff = True
    u.is_superuser = True
    u.set_password(password)
    u.save()
    print('Admin actualizado: ' + email)
"

echo "==> Seeding market assets (crypto prices)..."
python manage.py shell -c "
from apps.trading.models import Asset
ASSETS = [
    ('BTC','Bitcoin','crypto',67500,2.45,1450000000,1300000000000,68200,66800,'https://assets.coingecko.com/coins/images/1/large/bitcoin.png','bitcoin',1),
    ('ETH','Ethereum','crypto',3850,1.82,620000000,462000000000,3920,3780,'https://assets.coingecko.com/coins/images/279/large/ethereum.png','ethereum',2),
    ('BNB','BNB','crypto',605,-0.54,1800000000,88000000000,615,598,'https://assets.coingecko.com/coins/images/825/large/bnb-icon2_2x.png','binancecoin',3),
    ('SOL','Solana','crypto',185,3.21,3200000000,80000000000,188,179,'https://assets.coingecko.com/coins/images/4128/large/solana.png','solana',4),
    ('XRP','XRP','crypto',0.62,1.15,2100000000,34000000000,0.635,0.608,'https://assets.coingecko.com/coins/images/44/large/xrp-symbol-white-128.png','ripple',5),
    ('ADA','Cardano','crypto',0.48,-0.32,420000000,17000000000,0.492,0.471,'https://assets.coingecko.com/coins/images/975/large/cardano.png','cardano',6),
    ('AVAX','Avalanche','crypto',38.5,2.10,380000000,15700000000,39.2,37.6,'https://assets.coingecko.com/coins/images/12559/large/Avalanche_Circle_RedWhite_Trans.png','avalanche-2',7),
    ('DOGE','Dogecoin','crypto',0.165,4.20,1800000000,23800000000,0.172,0.158,'https://assets.coingecko.com/coins/images/5/large/dogecoin.png','dogecoin',8),
    ('DOT','Polkadot','crypto',8.20,-1.05,280000000,10500000000,8.45,8.05,'https://assets.coingecko.com/coins/images/12171/large/polkadot.png','polkadot',9),
    ('LINK','Chainlink','crypto',18.50,0.85,520000000,10800000000,18.90,18.10,'https://assets.coingecko.com/coins/images/877/large/chainlink-new-logo.png','chainlink',10),
    ('MATIC','Polygon','crypto',0.92,1.45,380000000,9200000000,0.945,0.905,'https://assets.coingecko.com/coins/images/4713/large/matic-token-icon.png','matic-network',11),
    ('LTC','Litecoin','crypto',88.50,-0.72,420000000,6600000000,90.20,87.30,'https://assets.coingecko.com/coins/images/2/large/litecoin.png','litecoin',12),
    ('UNI','Uniswap','crypto',12.80,2.35,180000000,7700000000,13.10,12.50,'https://assets.coingecko.com/coins/images/12504/large/uniswap-uni.png','uniswap',13),
    ('ATOM','Cosmos','crypto',9.85,0.95,220000000,3800000000,10.05,9.65,'https://assets.coingecko.com/coins/images/1481/large/cosmos_hub.png','cosmos',14),
    ('XLM','Stellar','crypto',0.128,1.20,180000000,3600000000,0.132,0.125,'https://assets.coingecko.com/coins/images/100/large/Stellar_symbol_black_RGB.png','stellar',15),
    ('AAPL','Apple Inc.','stock',189.50,0.82,65000000,2950000000000,191.20,187.80,'','AAPL',16),
    ('MSFT','Microsoft','stock',415.20,1.15,28000000,3080000000000,417.50,412.10,'','MSFT',17),
    ('GOOGL','Alphabet','stock',175.80,0.65,22000000,2180000000000,177.20,174.30,'','GOOGL',18),
    ('TSLA','Tesla','stock',178.20,-1.45,95000000,568000000000,182.50,176.40,'','TSLA',19),
    ('NVDA','Nvidia','stock',875.40,2.85,45000000,2160000000000,882.10,851.20,'','NVDA',20),
]
created = 0
for sym,name,atype,price,chg_pct,vol,mcap,high,low,img,cgid,rank in ASSETS:
    chg = round(price * chg_pct / 100, 4)
    obj, c = Asset.objects.update_or_create(
        symbol=sym,
        defaults=dict(name=name, asset_type=atype, current_price=price,
            price_change_24h=chg, price_change_pct_24h=chg_pct,
            volume_24h=vol, market_cap=mcap, high_24h=high, low_24h=low,
            image_url=img, coingecko_id=cgid, rank=rank, is_active=True)
    )
    if c: created += 1
print(f'Assets: {Asset.objects.count()} total ({created} nuevos)')
"

echo "==> Seeding fallback news and economic events..."
python manage.py shell -c "
from apps.news.views import _get_or_create_fallback_news, _get_or_create_fallback_events
from apps.news.models import NewsArticle
from apps.markets.models import EconomicEvent
n = _get_or_create_fallback_news()
e = _get_or_create_fallback_events()
print(f'Noticias: {NewsArticle.objects.count()} total ({n} nuevas)')
print(f'Eventos: {EconomicEvent.objects.count()} total ({e} nuevos)')
"

echo "==> Build complete!"
