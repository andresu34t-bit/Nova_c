"""
Nova Capital Group - Seed Script
Generates realistic demo data: users, orders, positions, transactions, snapshots
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from apps.trading.models import Asset, Order, Watchlist
from apps.portfolio.models import Position, PortfolioSnapshot
from apps.finances.models import Transaction
from apps.accounts.models import ActivityLog
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

User = get_user_model()

# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────
def rand_date(days_ago_max=90, days_ago_min=1):
    delta = random.randint(days_ago_min, days_ago_max)
    return timezone.now() - timedelta(days=delta, hours=random.randint(0,23), minutes=random.randint(0,59))

# ─────────────────────────────────────────────
# 1. UPDATE ADMIN USER
# ─────────────────────────────────────────────
admin = User.objects.get(email='admin@novacapital.com')
admin.balance = Decimal('47832.50')
admin.total_deposited = Decimal('75000.00')
admin.total_withdrawn = Decimal('12000.00')
admin.email_verified = True
admin.first_name = 'Johan'
admin.last_name = 'Izquierdo'
admin.country = 'Colombia'
admin.city = 'Bogota'
admin.phone = '+57 300 123 4567'
admin.save()
print("✓ Admin user updated")

# ─────────────────────────────────────────────
# 2. CREATE DEMO USERS
# ─────────────────────────────────────────────
demo_users_data = [
    ('carlos.mendez@novacapital.com', 'Carlos',   'Mendez',   'Colombia',  'Medellin',  '128450.75', 'premium'),
    ('sofia.torres@novacapital.com',  'Sofia',    'Torres',   'Mexico',    'CDMX',      '89320.00',  'premium'),
    ('andres.garcia@novacapital.com', 'Andres',   'Garcia',   'Argentina', 'Buenos Aires','34780.20','standard'),
    ('maria.lopez@novacapital.com',   'Maria',    'Lopez',    'Chile',     'Santiago',  '215600.00', 'institutional'),
    ('luis.ramirez@novacapital.com',  'Luis',     'Ramirez',  'Peru',      'Lima',      '12340.50',  'standard'),
]

demo_users = []
for email, fn, ln, country, city, bal, atype in demo_users_data:
    u, created = User.objects.get_or_create(email=email, defaults={
        'username': email.split('@')[0],
        'first_name': fn, 'last_name': ln,
        'country': country, 'city': city,
        'balance': Decimal(bal),
        'total_deposited': Decimal(bal) * Decimal('1.3'),
        'email_verified': True,
        'account_type': atype,
        'verification_status': 'verified',
    })
    if created:
        u.set_password('Demo2024Nova!')
        u.save()
    demo_users.append(u)
    print(f"  {'Created' if created else 'Exists'}: {email}")

all_users = [admin] + demo_users
print(f"✓ {len(all_users)} users ready")

# ─────────────────────────────────────────────
# 3. GET ASSETS
# ─────────────────────────────────────────────
assets = {a.symbol: a for a in Asset.objects.filter(is_active=True)}
crypto_syms  = ['BTC','ETH','BNB','SOL','XRP','ADA','AVAX','DOT','MATIC','LINK']
stock_syms   = ['AAPL','GOOGL','MSFT','TSLA','AMZN']
all_syms     = crypto_syms + stock_syms

# ─────────────────────────────────────────────
# 4. TRANSACTIONS (deposits + withdrawals)
# ─────────────────────────────────────────────
Transaction.objects.filter(user__in=all_users).delete()

deposit_scenarios = [
    (75000, 'bank_transfer', 90), (25000, 'credit_card', 60),
    (15000, 'bank_transfer', 45), (10000, 'crypto', 30),
    (5000,  'paypal', 15),
]
for user in all_users:
    bal = float(user.total_deposited)
    running = 0.0
    # Deposits
    for i, (base_amt, method, days) in enumerate(deposit_scenarios):
        amt = round(base_amt * random.uniform(0.7, 1.4), 2)
        if running + amt > bal * 1.1:
            break
        running += amt
        dt = timezone.now() - timedelta(days=days + random.randint(0,5))
        Transaction.objects.create(
            user=user, transaction_type='deposit', amount=Decimal(str(amt)),
            status='completed', payment_method=method,
            description=f'Deposito via {method.replace("_"," ").title()}',
            balance_before=Decimal(str(running - amt)),
            balance_after=Decimal(str(running)),
            fee_amount=Decimal('0'), completed_at=dt, created_at=dt,
        )
    # Withdrawal
    if float(user.total_withdrawn) > 0:
        wd = float(user.total_withdrawn)
        dt = timezone.now() - timedelta(days=random.randint(5,20))
        Transaction.objects.create(
            user=user, transaction_type='withdrawal', amount=Decimal(str(wd)),
            status='completed', payment_method='bank_transfer',
            description='Retiro a cuenta bancaria',
            balance_before=Decimal(str(running)),
            balance_after=Decimal(str(running - wd)),
            fee_amount=Decimal('0'), completed_at=dt, created_at=dt,
        )

print("✓ Transactions created")

# ─────────────────────────────────────────────
# 5. ORDERS + POSITIONS (realistic trading history)
# ─────────────────────────────────────────────
Order.objects.filter(user__in=all_users).delete()
Position.objects.filter(user__in=all_users).delete()

# Price history simulation (buy prices slightly lower than current)
buy_price_factor = {
    'BTC': 0.82, 'ETH': 0.78, 'BNB': 0.91, 'SOL': 0.65, 'XRP': 0.88,
    'ADA': 0.72, 'AVAX': 0.80, 'DOT': 0.85, 'MATIC': 0.76, 'LINK': 0.83,
    'AAPL': 0.94, 'GOOGL': 0.96, 'MSFT': 0.92, 'TSLA': 0.88, 'AMZN': 0.95,
}

for user in all_users:
    # Each user trades 6-10 different assets
    user_assets = random.sample(all_syms, random.randint(6, 10))
    
    for sym in user_assets:
        if sym not in assets:
            continue
        asset = assets[sym]
        current_price = float(asset.current_price)
        avg_buy = current_price * buy_price_factor.get(sym, 0.85) * random.uniform(0.95, 1.05)
        
        # Number of buy orders: 2-5
        n_buys = random.randint(2, 5)
        total_qty = 0.0
        
        for i in range(n_buys):
            qty = round(random.uniform(0.01, 0.5) if sym in crypto_syms else random.uniform(1, 15), 6)
            price = avg_buy * random.uniform(0.97, 1.03)
            total_val = qty * price
            fee = total_val * 0.001
            dt = rand_date(days_ago_max=85, days_ago_min=10 + i*5)
            
            Order.objects.create(
                user=user, asset=asset, order_type='market', side='buy',
                quantity=Decimal(str(round(qty,6))),
                price=Decimal(str(round(price,4))),
                filled_price=Decimal(str(round(price,4))),
                filled_quantity=Decimal(str(round(qty,6))),
                total_value=Decimal(str(round(total_val,2))),
                fee=Decimal(str(round(fee,4))),
                status='filled', filled_at=dt, created_at=dt,
            )
            Transaction.objects.create(
                user=user, transaction_type='trade_buy',
                amount=Decimal(str(round(total_val,2))),
                status='completed', payment_method='internal',
                description=f'Compra {round(qty,4)} {sym} @ ${round(price,2)}',
                balance_before=Decimal(str(round(float(user.balance)+total_val,2))),
                balance_after=user.balance,
                fee_amount=Decimal(str(round(fee,4))),
                completed_at=dt, created_at=dt,
            )
            total_qty += qty
        
        # Some assets have partial sells (closed positions)
        if random.random() < 0.35 and total_qty > 0.01:
            sell_qty = round(total_qty * random.uniform(0.3, 0.6), 6)
            sell_price = current_price * random.uniform(0.98, 1.02)
            sell_val = sell_qty * sell_price
            sell_fee = sell_val * 0.001
            dt_sell = rand_date(days_ago_max=5, days_ago_min=1)
            
            Order.objects.create(
                user=user, asset=asset, order_type='market', side='sell',
                quantity=Decimal(str(round(sell_qty,6))),
                price=Decimal(str(round(sell_price,4))),
                filled_price=Decimal(str(round(sell_price,4))),
                filled_quantity=Decimal(str(round(sell_qty,6))),
                total_value=Decimal(str(round(sell_val,2))),
                fee=Decimal(str(round(sell_fee,4))),
                status='filled', filled_at=dt_sell, created_at=dt_sell,
            )
            total_qty -= sell_qty
        
        # Create open position with remaining qty
        if total_qty > 0.001:
            Position.objects.create(
                user=user, asset=asset,
                quantity=Decimal(str(round(total_qty,6))),
                avg_buy_price=Decimal(str(round(avg_buy,4))),
                current_price=Decimal(str(round(current_price,4))),
                is_open=True,
            )

print("✓ Orders and positions created")

# ─────────────────────────────────────────────
# 6. PORTFOLIO SNAPSHOTS (90 days history)
# ─────────────────────────────────────────────
PortfolioSnapshot.objects.filter(user__in=all_users).delete()

for user in all_users:
    # Delete any remaining snapshots for this user explicitly
    PortfolioSnapshot.objects.filter(user=user).delete()
    positions = list(Position.objects.filter(user=user, is_open=True).select_related('asset'))
    if not positions:
        continue
    
    base_val = sum(float(p.quantity) * float(p.avg_buy_price) for p in positions)
    
    for day in range(89, -1, -1):
        snap_date = (timezone.now() - timedelta(days=day)).date()
        # Simulate realistic portfolio growth with volatility
        progress = (89 - day) / 89.0
        trend = 1.0 + (progress * random.uniform(0.08, 0.22))
        noise = random.uniform(-0.03, 0.04)
        total_val = round(base_val * (trend + noise), 2)
        cash = round(float(user.balance) * random.uniform(0.85, 1.0), 2)
        pnl = round(total_val - base_val, 2)
        
        try:
            PortfolioSnapshot.objects.create(
                user=user, snapshot_date=snap_date,
                total_value=Decimal(str(total_val)),
                cash_balance=Decimal(str(cash)),
                total_pnl=Decimal(str(pnl)),
            )
        except Exception:
            pass

print("✓ Portfolio snapshots created (90 days)")

# ─────────────────────────────────────────────
# 7. WATCHLISTS
# ─────────────────────────────────────────────
Watchlist.objects.filter(user__in=all_users).delete()

watchlist_assets = ['BTC','ETH','SOL','AAPL','MSFT','AVAX','LINK','BNB']
for user in all_users:
    user_watch = random.sample(watchlist_assets, random.randint(4, 7))
    for sym in user_watch:
        if sym in assets:
            Watchlist.objects.get_or_create(user=user, asset=assets[sym])

print("✓ Watchlists created")

# ─────────────────────────────────────────────
# 8. ACTIVITY LOGS
# ─────────────────────────────────────────────
ActivityLog.objects.filter(user__in=all_users).delete()

log_events = [
    ('login',           'Inicio de sesion exitoso'),
    ('deposit',         'Deposito procesado exitosamente'),
    ('trade',           'Orden de compra ejecutada'),
    ('trade',           'Orden de venta ejecutada'),
    ('profile_update',  'Perfil actualizado'),
    ('login',           'Inicio de sesion desde nuevo dispositivo'),
    ('deposit',         'Deposito via transferencia bancaria'),
    ('trade',           'Compra de BTC ejecutada'),
    ('trade',           'Compra de ETH ejecutada'),
    ('login',           'Sesion iniciada'),
]

ips = ['190.24.15.88','181.55.102.34','200.118.45.67','186.29.77.12','201.244.88.55']

for user in all_users:
    for i, (action, desc) in enumerate(log_events):
        dt = timezone.now() - timedelta(days=random.randint(0,30), hours=random.randint(0,23))
        ActivityLog.objects.create(
            user=user, action=action, description=desc,
            ip_address=random.choice(ips),
            created_at=dt,
        )

print("✓ Activity logs created")

# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
print("\n" + "="*50)
print("SEED DATA SUMMARY")
print("="*50)
print(f"Users:        {User.objects.count()}")
print(f"Orders:       {Order.objects.count()}")
print(f"Positions:    {Position.objects.count()}")
print(f"Transactions: {Transaction.objects.count()}")
print(f"Snapshots:    {PortfolioSnapshot.objects.count()}")
print(f"Watchlists:   {Watchlist.objects.count()}")
print(f"Activity:     {ActivityLog.objects.count()}")
print("="*50)
print("Admin login: admin@novacapital.com / Admin2024Nova!")
print("Demo login:  carlos.mendez@novacapital.com / Demo2024Nova!")
