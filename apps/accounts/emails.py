"""
Nova Capital Group - Email Service
Envío de emails transaccionales con templates HTML premium
"""
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger('apps')

BRAND_COLOR = '#0066FF'
SUCCESS_COLOR = '#00C896'
DANGER_COLOR = '#FF3B5C'
WARNING_COLOR = '#FFB800'
BG_DARK = '#050B18'
BG_CARD = '#0A1628'
TEXT_MUTED = '#7A8BA8'


def _base_html(title, content, cta_url=None, cta_text=None, cta_color=None):
    """Base HTML email template."""
    cta_html = ''
    if cta_url and cta_text:
        color = cta_color or BRAND_COLOR
        cta_html = f'''
        <div style="text-align:center;margin:32px 0;">
            <a href="{cta_url}"
               style="background:{color};color:#fff;padding:14px 32px;border-radius:8px;
                      text-decoration:none;font-weight:700;font-size:15px;display:inline-block;">
                {cta_text}
            </a>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:40px 20px;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

      <!-- Header -->
      <tr>
        <td style="background:{BG_DARK};border-radius:12px 12px 0 0;padding:28px 32px;text-align:center;">
          <div style="font-size:20px;font-weight:800;color:#fff;letter-spacing:1px;">NOVA CAPITAL GROUP</div>
          <div style="font-size:11px;color:{TEXT_MUTED};letter-spacing:3px;margin-top:4px;">INVERSIONES GLOBALES</div>
        </td>
      </tr>

      <!-- Content -->
      <tr>
        <td style="background:{BG_CARD};padding:32px;border-left:1px solid rgba(0,102,255,0.15);border-right:1px solid rgba(0,102,255,0.15);">
          {content}
          {cta_html}
        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td style="background:{BG_DARK};border-radius:0 0 12px 12px;padding:20px 32px;text-align:center;border:1px solid rgba(0,102,255,0.15);">
          <div style="font-size:11px;color:{TEXT_MUTED};">
            © {timezone.now().year} Nova Capital Group · Plataforma de simulación financiera<br>
            <span style="color:rgba(122,139,168,0.5);">Este es un email automático, no respondas a este mensaje.</span>
          </div>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>'''


def send_welcome_email(user):
    """Email de bienvenida al registrarse."""
    try:
        subject = f'¡Bienvenido a Nova Capital Group, {user.first_name}!'
        content = f'''
        <h2 style="color:#fff;font-size:22px;margin:0 0 16px;">
            ¡Hola, {user.first_name}! 👋
        </h2>
        <p style="color:{TEXT_MUTED};font-size:14px;line-height:1.7;margin:0 0 20px;">
            Tu cuenta en <strong style="color:#fff;">Nova Capital Group</strong> ha sido creada exitosamente.
            Ya puedes acceder a los mercados financieros globales.
        </p>
        <div style="background:rgba(0,102,255,0.08);border:1px solid rgba(0,102,255,0.2);border-radius:8px;padding:20px;margin:20px 0;">
            <div style="font-size:13px;font-weight:700;color:#fff;margin-bottom:12px;">Tu cuenta incluye:</div>
            <div style="display:flex;flex-direction:column;gap:8px;">
                {"".join([f'<div style="font-size:13px;color:{TEXT_MUTED};padding:4px 0;">✓ <span style="color:#fff;">{item}</span></div>' for item in [
                    'Acceso a 500+ activos: crypto, acciones, forex e índices',
                    'Terminal de trading con gráficos TradingView',
                    'Gestión de portafolio en tiempo real',
                    'Seguridad bancaria con autenticación 2FA',
                    'Noticias financieras en tiempo real',
                ]])}
            </div>
        </div>
        <p style="color:{TEXT_MUTED};font-size:13px;line-height:1.6;">
            <strong style="color:{WARNING_COLOR};">Próximo paso:</strong>
            Verifica tu correo electrónico y activa la autenticación 2FA para mayor seguridad.
        </p>'''

        html = _base_html(
            subject, content,
            cta_url=f'{settings.SITE_URL if hasattr(settings, "SITE_URL") else ""}/dashboard/',
            cta_text='Ir al Dashboard',
            cta_color=BRAND_COLOR
        )
        msg = EmailMultiAlternatives(subject, f'Bienvenido a Nova Capital Group, {user.first_name}!',
                                     settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=True)
        logger.info(f"Welcome email sent to {user.email}")
    except Exception as e:
        logger.error(f"Error sending welcome email to {user.email}: {e}")


def send_verification_email(user, verify_url):
    """Email de verificación de cuenta."""
    try:
        subject = 'Verifica tu cuenta - Nova Capital Group'
        content = f'''
        <h2 style="color:#fff;font-size:22px;margin:0 0 16px;">Verifica tu correo electrónico</h2>
        <p style="color:{TEXT_MUTED};font-size:14px;line-height:1.7;margin:0 0 20px;">
            Hola <strong style="color:#fff;">{user.first_name}</strong>,
            haz clic en el botón para verificar tu cuenta y activar todas las funcionalidades.
        </p>
        <div style="background:rgba(0,200,150,0.08);border:1px solid rgba(0,200,150,0.2);border-radius:8px;padding:16px;margin:20px 0;">
            <div style="font-size:12px;color:{TEXT_MUTED};">
                <strong style="color:{WARNING_COLOR};">⚠️ Este enlace expira en 24 horas.</strong><br>
                Si no creaste esta cuenta, ignora este email.
            </div>
        </div>'''
        html = _base_html(subject, content, cta_url=verify_url,
                          cta_text='Verificar mi cuenta', cta_color=SUCCESS_COLOR)
        msg = EmailMultiAlternatives(subject, f'Verifica tu cuenta: {verify_url}',
                                     settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=True)
        logger.info(f"Verification email sent to {user.email}")
    except Exception as e:
        logger.error(f"Error sending verification email: {e}")


def send_deposit_approved_email(user, amount, tx_id):
    """Email cuando el admin aprueba un depósito."""
    try:
        subject = f'✓ Depósito aprobado: ${amount:,.2f} USD'
        content = f'''
        <div style="text-align:center;margin-bottom:24px;">
            <div style="width:64px;height:64px;background:rgba(0,200,150,0.15);border-radius:50%;
                        display:inline-flex;align-items:center;justify-content:center;font-size:28px;">✓</div>
        </div>
        <h2 style="color:#fff;font-size:22px;margin:0 0 8px;text-align:center;">¡Depósito Aprobado!</h2>
        <p style="color:{TEXT_MUTED};font-size:14px;text-align:center;margin:0 0 24px;">
            Tu depósito ha sido revisado y aprobado exitosamente.
        </p>
        <div style="background:rgba(0,200,150,0.08);border:1px solid rgba(0,200,150,0.2);border-radius:8px;padding:20px;margin:20px 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Monto acreditado</td>
                    <td style="font-size:18px;font-weight:800;color:{SUCCESS_COLOR};text-align:right;font-family:monospace;">${amount:,.2f} USD</td>
                </tr>
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Referencia</td>
                    <td style="font-size:12px;color:#fff;text-align:right;font-family:monospace;">{str(tx_id)[:8].upper()}</td>
                </tr>
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Estado</td>
                    <td style="font-size:13px;font-weight:700;color:{SUCCESS_COLOR};text-align:right;">Completado</td>
                </tr>
            </table>
        </div>
        <p style="color:{TEXT_MUTED};font-size:13px;text-align:center;">
            El saldo ya está disponible en tu cuenta para operar.
        </p>'''
        html = _base_html(subject, content,
                          cta_url=f'{getattr(settings, "SITE_URL", "")}/finances/',
                          cta_text='Ver mis Finanzas', cta_color=SUCCESS_COLOR)
        msg = EmailMultiAlternatives(subject, f'Tu depósito de ${amount:,.2f} USD ha sido aprobado.',
                                     settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=True)
        logger.info(f"Deposit approved email sent to {user.email} amount={amount}")
    except Exception as e:
        logger.error(f"Error sending deposit approved email: {e}")


def send_deposit_rejected_email(user, amount, reason, tx_id):
    """Email cuando el admin rechaza un depósito."""
    try:
        subject = f'Depósito no procesado: ${amount:,.2f} USD'
        content = f'''
        <div style="text-align:center;margin-bottom:24px;">
            <div style="width:64px;height:64px;background:rgba(255,59,92,0.15);border-radius:50%;
                        display:inline-flex;align-items:center;justify-content:center;font-size:28px;">✗</div>
        </div>
        <h2 style="color:#fff;font-size:22px;margin:0 0 8px;text-align:center;">Depósito No Procesado</h2>
        <p style="color:{TEXT_MUTED};font-size:14px;text-align:center;margin:0 0 24px;">
            Tu solicitud de depósito no pudo ser procesada.
        </p>
        <div style="background:rgba(255,59,92,0.08);border:1px solid rgba(255,59,92,0.2);border-radius:8px;padding:20px;margin:20px 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Monto</td>
                    <td style="font-size:16px;font-weight:700;color:#fff;text-align:right;font-family:monospace;">${amount:,.2f} USD</td>
                </tr>
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Referencia</td>
                    <td style="font-size:12px;color:#fff;text-align:right;font-family:monospace;">{str(tx_id)[:8].upper()}</td>
                </tr>
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Motivo</td>
                    <td style="font-size:13px;color:{DANGER_COLOR};text-align:right;">{reason}</td>
                </tr>
            </table>
        </div>
        <p style="color:{TEXT_MUTED};font-size:13px;">
            Si crees que esto es un error, contacta a nuestro equipo de soporte con tu número de referencia.
        </p>'''
        html = _base_html(subject, content,
                          cta_url=f'{getattr(settings, "SITE_URL", "")}/finances/deposit/',
                          cta_text='Intentar de nuevo', cta_color=BRAND_COLOR)
        msg = EmailMultiAlternatives(subject, f'Tu depósito de ${amount:,.2f} USD no fue procesado. Motivo: {reason}',
                                     settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=True)
    except Exception as e:
        logger.error(f"Error sending deposit rejected email: {e}")


def send_withdrawal_approved_email(user, amount, tx_id):
    """Email cuando el admin aprueba un retiro."""
    try:
        subject = f'✓ Retiro procesado: ${amount:,.2f} USD'
        content = f'''
        <h2 style="color:#fff;font-size:22px;margin:0 0 16px;text-align:center;">Retiro Procesado</h2>
        <p style="color:{TEXT_MUTED};font-size:14px;text-align:center;margin:0 0 24px;">
            Tu solicitud de retiro ha sido procesada exitosamente.
        </p>
        <div style="background:rgba(255,184,0,0.08);border:1px solid rgba(255,184,0,0.2);border-radius:8px;padding:20px;margin:20px 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Monto retirado</td>
                    <td style="font-size:18px;font-weight:800;color:{WARNING_COLOR};text-align:right;font-family:monospace;">${amount:,.2f} USD</td>
                </tr>
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Referencia</td>
                    <td style="font-size:12px;color:#fff;text-align:right;font-family:monospace;">{str(tx_id)[:8].upper()}</td>
                </tr>
            </table>
        </div>
        <p style="color:{TEXT_MUTED};font-size:13px;">
            Los fondos llegarán a tu cuenta bancaria en 1-3 días hábiles dependiendo de tu banco.
        </p>'''
        html = _base_html(subject, content)
        msg = EmailMultiAlternatives(subject, f'Tu retiro de ${amount:,.2f} USD ha sido procesado.',
                                     settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=True)
    except Exception as e:
        logger.error(f"Error sending withdrawal approved email: {e}")


def send_password_reset_email(user, reset_url):
    """Email de recuperación de contraseña."""
    try:
        subject = 'Recuperar contraseña - Nova Capital Group'
        content = f'''
        <h2 style="color:#fff;font-size:22px;margin:0 0 16px;">Recuperar Contraseña</h2>
        <p style="color:{TEXT_MUTED};font-size:14px;line-height:1.7;margin:0 0 20px;">
            Hola <strong style="color:#fff;">{user.first_name}</strong>,
            recibimos una solicitud para restablecer la contraseña de tu cuenta.
        </p>
        <div style="background:rgba(255,184,0,0.08);border:1px solid rgba(255,184,0,0.2);border-radius:8px;padding:16px;margin:20px 0;">
            <div style="font-size:12px;color:{TEXT_MUTED};">
                <strong style="color:{WARNING_COLOR};">⚠️ Este enlace expira en 1 hora.</strong><br>
                Si no solicitaste este cambio, ignora este email. Tu contraseña no cambiará.
            </div>
        </div>'''
        html = _base_html(subject, content, cta_url=reset_url,
                          cta_text='Restablecer Contraseña', cta_color=WARNING_COLOR)
        msg = EmailMultiAlternatives(subject, f'Restablece tu contraseña: {reset_url}',
                                     settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=True)
        logger.info(f"Password reset email sent to {user.email}")
    except Exception as e:
        logger.error(f"Error sending password reset email: {e}")


def send_trade_confirmation_email(user, side, symbol, quantity, price, total, fee):
    """Email de confirmación de operación de trading."""
    try:
        side_text = 'Compra' if side == 'buy' else 'Venta'
        side_color = SUCCESS_COLOR if side == 'buy' else DANGER_COLOR
        subject = f'Orden ejecutada: {side_text} {quantity:.4f} {symbol}'
        content = f'''
        <h2 style="color:#fff;font-size:22px;margin:0 0 16px;text-align:center;">
            Orden Ejecutada
        </h2>
        <div style="background:rgba(0,102,255,0.08);border:1px solid rgba(0,102,255,0.2);border-radius:8px;padding:20px;margin:20px 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Tipo</td>
                    <td style="font-size:14px;font-weight:700;color:{side_color};text-align:right;">▲ {side_text}</td>
                </tr>
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Activo</td>
                    <td style="font-size:14px;font-weight:700;color:#fff;text-align:right;">{symbol}/USD</td>
                </tr>
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Cantidad</td>
                    <td style="font-size:14px;color:#fff;text-align:right;font-family:monospace;">{quantity:.6f}</td>
                </tr>
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Precio</td>
                    <td style="font-size:14px;color:#fff;text-align:right;font-family:monospace;">${price:,.4f}</td>
                </tr>
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Total</td>
                    <td style="font-size:18px;font-weight:800;color:#fff;text-align:right;font-family:monospace;">${total:,.2f}</td>
                </tr>
                <tr>
                    <td style="font-size:13px;color:{TEXT_MUTED};padding:6px 0;">Comisión</td>
                    <td style="font-size:13px;color:{TEXT_MUTED};text-align:right;font-family:monospace;">${fee:,.4f}</td>
                </tr>
            </table>
        </div>'''
        html = _base_html(subject, content,
                          cta_url=f'{getattr(settings, "SITE_URL", "")}/trading/?symbol={symbol}',
                          cta_text='Ver en Trading', cta_color=BRAND_COLOR)
        msg = EmailMultiAlternatives(subject, f'Orden ejecutada: {side_text} {quantity:.4f} {symbol} @ ${price:,.4f}',
                                     settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=True)
    except Exception as e:
        logger.error(f"Error sending trade confirmation email: {e}")


def send_price_alert_email(user, symbol, alert_type, target_price, current_price):
    """Email de alerta de precio."""
    try:
        direction = 'subió a' if alert_type == 'high' else 'bajó a'
        subject = f'🔔 Alerta de precio: {symbol} {direction} ${current_price:,.4f}'
        content = f'''
        <h2 style="color:#fff;font-size:22px;margin:0 0 16px;text-align:center;">
            Alerta de Precio Activada
        </h2>
        <div style="background:rgba(255,184,0,0.08);border:1px solid rgba(255,184,0,0.2);border-radius:8px;padding:20px;margin:20px 0;text-align:center;">
            <div style="font-size:32px;font-weight:800;color:#fff;font-family:monospace;">{symbol}</div>
            <div style="font-size:14px;color:{TEXT_MUTED};margin:8px 0;">ha {direction}</div>
            <div style="font-size:28px;font-weight:800;color:{WARNING_COLOR};font-family:monospace;">${current_price:,.4f}</div>
            <div style="font-size:12px;color:{TEXT_MUTED};margin-top:8px;">Tu alerta era: ${target_price:,.4f}</div>
        </div>'''
        html = _base_html(subject, content,
                          cta_url=f'{getattr(settings, "SITE_URL", "")}/trading/?symbol={symbol}',
                          cta_text=f'Operar {symbol}', cta_color=WARNING_COLOR)
        msg = EmailMultiAlternatives(subject, f'Alerta: {symbol} {direction} ${current_price:,.4f}',
                                     settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=True)
    except Exception as e:
        logger.error(f"Error sending price alert email: {e}")
