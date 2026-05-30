from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('', views.news_view, name='news'),
    path('fetch/', views.fetch_news, name='fetch_news'),
]
