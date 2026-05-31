from django.urls import path
from . import views

app_name = 'finances'

urlpatterns = [
    path('', views.finances_view, name='finances'),
    path('deposit/', views.deposit_view, name='deposit'),
    path('withdrawal/', views.withdrawal_view, name='withdrawal'),
    path('history/', views.transaction_history, name='history'),

    # Admin — gestión de transacciones
    path('admin/transactions/', views.admin_transactions_view, name='admin_transactions'),
    path('admin/transactions/<uuid:tx_id>/approve/', views.approve_transaction, name='approve_transaction'),
    path('admin/transactions/<uuid:tx_id>/reject/', views.reject_transaction, name='reject_transaction'),
]
