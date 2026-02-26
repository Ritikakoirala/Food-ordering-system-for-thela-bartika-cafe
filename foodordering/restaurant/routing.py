"""
WebSocket URL routing for the Food Delivery System
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Customer tracking their delivery
    re_path(r'ws/delivery/(?P<order_id>\w+)/$', consumers.DeliveryTrackingConsumer.as_asgi()),
    
    # Rider sending location updates
    re_path(r'ws/rider/(?P<rider_id>\w+)/$', consumers.RiderTrackingConsumer.as_asgi()),
    
    # Admin tracking all deliveries
    re_path(r'ws/admin/tracking/$', consumers.AdminTrackingConsumer.as_asgi()),
    
    # User notifications
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
