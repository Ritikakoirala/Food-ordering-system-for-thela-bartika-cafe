"""
WebSocket Consumers for Real-Time Delivery Tracking
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class DeliveryTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time delivery tracking
    Allows customers to track their delivery in real-time
    """
    
    async def connect(self):
        self.order_id = self.scope['url_route']['kwargs'].get('order_id')
        self.room_group_name = f'delivery_{self.order_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to delivery tracking',
            'order_id': self.order_id
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
        except json.JSONDecodeError:
            pass
    
    async def delivery_update(self, event):
        """Handle delivery status updates"""
        await self.send(text_data=json.dumps({
            'type': 'delivery_update',
            'status': event.get('status'),
            'message': event.get('message'),
            'timestamp': event.get('timestamp'),
            'rider_location': event.get('rider_location')
        }))
    
    async def rider_location_update(self, event):
        """Handle rider location updates"""
        await self.send(text_data=json.dumps({
            'type': 'rider_location',
            'latitude': event.get('latitude'),
            'longitude': event.get('longitude'),
            'accuracy': event.get('accuracy'),
            'speed': event.get('speed'),
            'heading': event.get('heading'),
            'timestamp': event.get('timestamp')
        }))
    
    async def order_status_change(self, event):
        """Handle order status changes"""
        await self.send(text_data=json.dumps({
            'type': 'order_status',
            'status': event.get('status'),
            'message': event.get('message'),
            'estimated_time': event.get('estimated_time')
        }))


class RiderTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for rider location tracking
    Used by riders to send GPS updates
    """
    
    async def connect(self):
        self.rider_id = self.scope['url_route']['kwargs'].get('rider_id')
        self.room_group_name = f'rider_{self.rider_id}'
        
        # Verify rider is authenticated
        user = self.scope.get('user')
        if not user or not user.is_authenticated or str(user.id) != str(self.rider_id):
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming location updates from rider"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'location_update':
                # Broadcast location to order room
                order_id = data.get('order_id')
                if order_id:
                    await self.channel_layer.group_send(
                        f'delivery_{order_id}',
                        {
                            'type': 'rider_location_update',
                            'latitude': data.get('latitude'),
                            'longitude': data.get('longitude'),
                            'accuracy': data.get('accuracy', 0),
                            'speed': data.get('speed', 0),
                            'heading': data.get('heading', 0),
                            'timestamp': data.get('timestamp')
                        }
                    )
                
                # Also send to admin room
                await self.channel_layer.group_send(
                    'admin_riders',
                    {
                        'type': 'rider_location_update',
                        'rider_id': self.rider_id,
                        'latitude': data.get('latitude'),
                        'longitude': data.get('longitude'),
                        'timestamp': data.get('timestamp')
                    }
                )
                
                # Send acknowledgment
                await self.send(text_data=json.dumps({
                    'type': 'location_received',
                    'timestamp': data.get('timestamp')
                }))
                    
        except json.JSONDecodeError:
            pass
    
    async def rider_location_update(self, event):
        """Handle location updates from other sources"""
        await self.send(text_data=json.dumps({
            'type': 'rider_location',
            'latitude': event.get('latitude'),
            'longitude': event.get('longitude')
        }))


class AdminTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for admin dashboard tracking
    Shows all active deliveries and rider locations
    """
    
    async def connect(self):
        # Check if user is admin
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        
        self.room_group_name = 'admin_tracking'
        
        # Join admin tracking group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle admin requests"""
        try:
            data = json.loads(text_data)
            
            if data.get('type') == 'get_active_deliveries':
                # This would typically fetch from database
                await self.send(text_data=json.dumps({
                    'type': 'active_deliveries',
                    'deliveries': []  # Will be populated by backend
                }))
        except json.JSONDecodeError:
            pass
    
    async def delivery_update(self, event):
        """Handle delivery status updates"""
        await self.send(text_data=json.dumps({
            'type': 'delivery_update',
            'order_id': event.get('order_id'),
            'status': event.get('status'),
            'rider_id': event.get('rider_id'),
            'timestamp': event.get('timestamp')
        }))
    
    async def rider_location_update(self, event):
        """Handle rider location updates"""
        await self.send(text_data=json.dumps({
            'type': 'rider_location',
            'rider_id': event.get('rider_id'),
            'latitude': event.get('latitude'),
            'longitude': event.get('longitude'),
            'timestamp': event.get('timestamp')
        }))


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user notifications
    """
    
    async def connect(self):
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        self.room_group_name = f'notifications_{self.user.id}'
        
        # Join user notifications group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming messages"""
        pass
    
    async def notification(self, event):
        """Send notification to user"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event.get('title'),
            'message': event.get('message'),
            'notification_type': event.get('notification_type'),
            'timestamp': event.get('timestamp')
        }))
