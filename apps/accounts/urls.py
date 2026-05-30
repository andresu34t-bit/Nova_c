from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update_view, name='profile_update'),
    path('security/', views.security_view, name='security'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('kyc/upload/', views.upload_kyc_view, name='upload_kyc'),
]
