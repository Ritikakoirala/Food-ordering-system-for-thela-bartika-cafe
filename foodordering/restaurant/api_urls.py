"""
API URL Configuration for the Food Delivery System
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'categories', api_views.CategoryViewSet)
router.register(r'food-items', api_views.FoodItemViewSet)
router.register(r'cart', api_views.CartViewSet)
router.register(r'orders', api_views.OrderViewSet)
router.register(r'reviews', api_views.ReviewViewSet)
router.register(r'feedback', api_views.FeedbackViewSet)

urlpatterns = [
    # Authentication
    path('auth/register/', api_views.RegisterView.as_view(), name='api_register'),
    path('auth/login/', api_views.LoginView.as_view(), name='api_login'),
    path('auth/otp-verify/', api_views.OTPVerifyView.as_view(), name='api_otp_verify'),
    path('auth/refresh/', api_views.RefreshTokenView.as_view(), name='api_token_refresh'),
    
    # Rider location
    path('rider/location/', api_views.UpdateLocationView.as_view(), name='update_location'),
    
    # Payments
    path('payments/create-intent/', api_views.CreatePaymentIntentView.as_view(), name='create_payment_intent'),
    path('payments/webhook/', api_views.StripeWebhookView.as_view(), name='stripe_webhook'),
    
    # Analytics (Admin)
    path('analytics/dashboard/', api_views.DashboardStatsView.as_view(), name='dashboard_stats'),
    path('analytics/active-deliveries/', api_views.ActiveDeliveriesView.as_view(), name='active_deliveries'),
    
    # Include router URLs
    path('', include(router.urls)),
]
