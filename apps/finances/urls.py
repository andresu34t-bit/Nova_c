from django.urls import path
from . import views

app_name = 'finances'

urlpatterns = [
    path('', views.finances_view, name='finances'),
    path('deposit/', views.deposit_view, name='deposit'),
    path('withdrawal/', views.withdrawal_view, name='withdrawal'),
    path('history/', views.transaction_history, name='history'),
]
