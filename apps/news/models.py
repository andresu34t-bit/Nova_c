"""
Nova Capital Group - News Models
"""
from django.db import models


class NewsArticle(models.Model):
    """Financial news article."""
    
    CATEGORIES = [
        ('crypto', 'Criptomonedas'),
        ('stocks', 'Acciones'),
        ('forex', 'Forex'),
        ('economy', 'Economía'),
        ('technology', 'Tecnología'),
        ('general', 'General'),
    ]

    title = models.CharField(max_length=500)
    summary = models.TextField()
    content = models.TextField(blank=True)
    source = models.CharField(max_length=100)
    source_url = models.URLField()
    image_url = models.URLField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='general')
    published_at = models.DateTimeField()
    is_featured = models.BooleanField(default=False)
    sentiment = models.CharField(max_length=20, blank=True)
    related_symbols = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Noticia'
        verbose_name_plural = 'Noticias'
        ordering = ['-published_at']

    def __str__(self):
        return self.title
