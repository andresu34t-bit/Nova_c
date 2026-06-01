"""
Nova Capital Group - Security Middleware
"""
from django.utils.deprecation import MiddlewareMixin

# Rutas que contienen el widget de TradingView (necesitan frame-src amplio)
TRADINGVIEW_PATHS = ('/trading', '/markets')


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses.

    TradingView widget (tv.js) crea iframes internos hacia múltiples
    subdominios de tradingview.com. Por eso:
      - X-Frame-Options se omite en páginas de trading/markets
        (el header DENY bloquea los iframes del propio widget).
      - La CSP frame-src incluye *.tradingview.com para esas páginas.
    """

    def process_response(self, request, response):
        path = request.path

        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        # ── X-Frame-Options ──────────────────────────────────────────
        # En páginas con TradingView NO ponemos DENY porque el widget
        # crea iframes internos que serían bloqueados.
        # En el resto de páginas sí lo ponemos para protección clickjacking.
        is_tv_page = any(path.startswith(p) for p in TRADINGVIEW_PATHS)
        if not is_tv_page:
            response['X-Frame-Options'] = 'SAMEORIGIN'
        else:
            # Eliminar cualquier valor previo que Django haya puesto
            if 'X-Frame-Options' in response:
                del response['X-Frame-Options']

        # ── Content-Security-Policy ──────────────────────────────────
        # TradingView necesita:
        #   script-src  → s3.tradingview.com + *.tradingview.com
        #   frame-src   → *.tradingview.com (el widget abre iframes)
        #   connect-src → *.tradingview.com (WebSocket de precios)
        #   worker-src  → blob: (web workers del widget)
        if is_tv_page:
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                "  https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
                "  https://s3.tradingview.com https://*.tradingview.com; "
                "style-src 'self' 'unsafe-inline' "
                "  https://cdn.jsdelivr.net https://fonts.googleapis.com "
                "  https://*.tradingview.com; "
                "font-src 'self' https://fonts.gstatic.com "
                "  https://cdn.jsdelivr.net https://*.tradingview.com; "
                "img-src 'self' data: https: blob:; "
                "connect-src 'self' https: wss: "
                "  https://*.tradingview.com wss://*.tradingview.com "
                "  https://api.coingecko.com; "
                "frame-src 'self' https://*.tradingview.com https://www.tradingview.com; "
                "worker-src blob: 'self'; "
                "child-src blob: 'self' https://*.tradingview.com;"
            )
        else:
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                "  https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' "
                "  https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com "
                "  https://cdn.jsdelivr.net; "
                "img-src 'self' data: https: blob:; "
                "connect-src 'self' https: wss:; "
                "frame-src 'none';"
            )

        response['Content-Security-Policy'] = csp
        return response


class ActivityLogMiddleware(MiddlewareMixin):
    """Track user last activity — throttled to avoid DB writes on every request."""

    def process_request(self, request):
        if request.user.is_authenticated:
            try:
                from django.utils import timezone as tz
                now = tz.now()
                last = getattr(request.user, 'last_activity', None)
                # Solo actualizar si han pasado más de 5 minutos desde la última actualización
                if last is None or (now - last).total_seconds() > 300:
                    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
                    if ',' in ip:
                        ip = ip.split(',')[0].strip()
                    request.user.last_activity = now
                    request.user.last_login_ip = ip or None
                    request.user.save(update_fields=['last_activity', 'last_login_ip'])
            except Exception:
                pass
