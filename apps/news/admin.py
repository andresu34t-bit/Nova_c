from django.contrib import admin
from .models import NewsArticle


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'source', 'category', 'is_featured', 'published_at']
    list_filter = ['category', 'is_featured']
    search_fields = ['title', 'source', 'related_symbols']
    ordering = ['-published_at']
    list_editable = ['is_featured']
