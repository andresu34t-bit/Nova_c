"""
Nova Capital Group - Security Middleware
"""
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses."""

    def process_response(self, request, response):
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com https://s3.tradingview.com https://charting_library.tradingview.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://api.coingecko.com https://finnhub.io https://newsapi.org wss: https://s3.tradingview.com; "
            "frame-src 'self' https://s3.tradingview.com https://www.tradingview.com;"
        )
        return response


class ActivityLogMiddleware(MiddlewareMixin):
    """Track user last activity and log logins."""

    def process_request(self, request):
        if request.user.is_authenticated:
            try:
                ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                request.user.last_activity = timezone.now()
                request.user.last_login_ip = ip or None
                request.user.save(update_fields=['last_activity', 'last_login_ip'])
            except Exception:
                pass
