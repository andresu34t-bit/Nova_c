from django.urls import path
from . import views

app_name = 'markets'

urlpatterns = [
    path('',                    views.markets_overview,  name='overview'),
    path('asset/<str:symbol>/', views.asset_detail,      name='asset_detail'),
    # API endpoints
    path('api/crypto/',         views.api_crypto,        name='api_crypto'),
    path('api/stocks/',         views.api_stocks,        name='api_stocks'),
    path('api/forex/',          views.api_forex,         name='api_forex'),
    path('api/indices/',        views.api_indices,       name='api_indices'),
    # Legacy
    path('api/prices/',         views.api_prices,        name='api_prices'),
    path('api/fetch/',          views.fetch_market_data, name='fetch_data'),
]
