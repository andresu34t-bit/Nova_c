"""
Nova Capital Group - WebSocket Consumers
Notificaciones en tiempo real para el usuario
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer para notificaciones personalizadas por usuario."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Enviar estado inicial
        balance = await self.get_balance()
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Conectado a notificaciones en tiempo real',
            'balance': str(balance),
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Recibir mensajes del cliente (ping/pong)."""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except Exception:
            pass

    # ── Handlers de mensajes del grupo ──

    async def notification(self, event):
        """Enviar notificación genérica al cliente."""
        await self.send(text_data=json.dumps({
            'type':    event.get('notification_type', 'info'),
            'title':   event.get('title', ''),
            'message': event.get('message', ''),
            'data':    event.get('data', {}),
        }))

    async def balance_update(self, event):
        """Notificar actualización de saldo."""
        await self.send(text_data=json.dumps({
            'type':        'balance_update',
            'new_balance': event.get('new_balance', '0'),
            'message':     event.get('message', ''),
        }))

    async def deposit_approved(self, event):
        """Notificar depósito aprobado."""
        await self.send(text_data=json.dumps({
            'type':        'deposit_approved',
            'amount':      event.get('amount', '0'),
            'new_balance': event.get('new_balance', '0'),
            'message':     event.get('message', ''),
        }))

    async def deposit_rejected(self, event):
        """Notificar depósito rechazado."""
        await self.send(text_data=json.dumps({
            'type':    'deposit_rejected',
            'amount':  event.get('amount', '0'),
            'reason':  event.get('reason', ''),
            'message': event.get('message', ''),
        }))

    @database_sync_to_async
    def get_balance(self):
        return self.user.balance


class PriceConsumer(AsyncWebsocketConsumer):
    """Consumer para precios en tiempo real (broadcast a todos)."""

    async def connect(self):
        self.group_name = 'prices'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def price_update(self, event):
        """Enviar actualización de precios."""
        await self.send(text_data=json.dumps({
            'type':   'price_update',
            'prices': event.get('prices', []),
        }))
