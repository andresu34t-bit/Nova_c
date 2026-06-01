from django.urls import path
from . import views

app_name = 'trading'

urlpatterns = [
    path('', views.trading_view, name='trading'),
    path('order/place/', views.place_order, name='place_order'),
    path('orders/', views.order_history, name='order_history'),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('watchlist/toggle/', views.toggle_watchlist, name='toggle_watchlist'),
    path('watchlist/alert/', views.set_price_alert, name='set_price_alert'),
    path('calculator/', views.profit_calculator, name='profit_calculator'),
]
