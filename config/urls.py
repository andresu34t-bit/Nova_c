from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from two_factor.urls import urlpatterns as tf_urls
from apps.core.views import handler404, handler500, health_check

handler404 = handler404
handler500 = handler500

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('', include('apps.core.urls', namespace='core')),
    path('', include(tf_urls)),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('markets/', include('apps.markets.urls', namespace='markets')),
    path('trading/', include('apps.trading.urls', namespace='trading')),
    path('portfolio/', include('apps.portfolio.urls', namespace='portfolio')),
    path('finances/', include('apps.finances.urls', namespace='finances')),
    path('news/', include('apps.news.urls', namespace='news')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
