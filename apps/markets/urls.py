from django.urls import path
from . import views

app_name = 'markets'

urlpatterns = [
    path('', views.markets_overview, name='overview'),
    path('asset/<str:symbol>/', views.asset_detail, name='asset_detail'),
    path('api/prices/', views.api_prices, name='api_prices'),
    path('api/fetch/', views.fetch_market_data, name='fetch_data'),
]
