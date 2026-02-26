"""
Django REST Framework API Views for the Food Delivery System
"""
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
import pyotp
import stripe
from django.conf import settings

from .models import (
    Category, FoodItem, Customer, Rider, RiderLocation,
    Cart, Order, OrderItem, DeliveryStatus, Review, Feedback
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer, OTPSerializer,
    CategorySerializer, FoodItemSerializer, CartSerializer, CartCreateSerializer,
    OrderSerializer, OrderCreateSerializer, RiderLocationSerializer,
    RiderSerializer, CustomerSerializer, ReviewSerializer, ReviewCreateSerializer,
    FeedbackSerializer, StripePaymentSerializer
)

User = get_user_model()


# ============================================================================
# Authentication Views
# ============================================================================

class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate OTP secret
        user.otp_secret = pyotp.random_base32()
        user.save()
        
        # Create tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """User login endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = authenticate(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        
        if user is None:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Generate OTP if not verified
        if not user.otp_verified:
            user.otp_secret = pyotp.random_base32()
            user.save()
            
            # In production, send OTP via SMS/email
            totp = pyotp.TOTP(user.otp_secret)
            otp_code = totp.now()
            print(f"OTP for {user.email}: {otp_code}")  # Debug only!
            
            return Response({
                'requires_otp': True,
                'message': 'OTP required for login',
                'user_id': user.id
            }, status=status.HTTP_200_OK)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class OTPVerifyView(APIView):
    """Verify OTP for login"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = User.objects.get(id=request.data.get('user_id'))
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        totp = pyotp.TOTP(user.otp_secret)
        if not totp.verify(request.data.get('otp_code')):
            return Response(
                {'error': 'Invalid OTP'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.otp_verified = True
        user.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class RefreshTokenView(APIView):
    """Refresh access token"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            refresh = RefreshToken(refresh_token)
            return Response({
                'access': str(refresh.access_token),
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )


# ============================================================================
# Category Views
# ============================================================================

class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Category CRUD operations"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]


# ============================================================================
# Food Item Views
# ============================================================================

class FoodItemViewSet(viewsets.ModelViewSet):
    """ViewSet for FoodItem CRUD operations"""
    queryset = FoodItem.objects.all()
    serializer_class = FoodItemSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = FoodItem.objects.select_related('category').filter(is_available=True)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        return queryset
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]


# ============================================================================
# Cart Views
# ============================================================================

class CartViewSet(viewsets.ModelViewSet):
    """ViewSet for Cart operations"""
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).select_related('food_item', 'food_item__category')
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CartCreateSerializer
        return CartSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """Clear all cart items"""
        Cart.objects.filter(user=request.user).delete()
        return Response({'message': 'Cart cleared'})


# ============================================================================
# Order Views
# ============================================================================

class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for Order operations"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_admin_user:
            return Order.objects.all().select_related('user', 'rider').prefetch_related('items')
        return Order.objects.filter(user=user).select_related('user', 'rider').prefetch_related('items')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def perform_create(self, serializer):
        # Calculate totals from cart
        cart_items = Cart.objects.filter(user=self.request.user).select_related('food_item')
        if not cart_items:
            raise serializers.ValidationError("Cart is empty")
        
        total_price = sum(item.subtotal() for item in cart_items)
        tax = total_price * 0.10  # 10% tax
        delivery_fee = 2.00  # Fixed delivery fee
        
        order = serializer.save(
            user=self.request.user,
            total_price=total_price,
            tax=tax,
            delivery_fee=delivery_fee
        )
        
        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                food_item=cart_item.food_item,
                quantity=cart_item.quantity,
                price=cart_item.food_item.price
            )
        
        # Clear cart
        cart_items.delete()
        
        # Create initial delivery status
        DeliveryStatus.objects.create(
            order=order,
            status='pending',
            description='Order placed successfully',
            updated_by=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel order"""
        order = self.get_object()
        if not order.can_cancel:
            return Response(
                {'error': 'Order cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        
        DeliveryStatus.objects.create(
            order=order,
            status='cancelled',
            description='Order cancelled by user',
            updated_by=request.user
        )
        
        return Response({'message': 'Order cancelled'})
    
    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        """Track order delivery"""
        order = self.get_object()
        statuses = DeliveryStatusSerializer(order.delivery_statuses.all(), many=True).data
        
        # Get latest rider location if out for delivery
        rider_location = None
        if order.rider and order.status == 'out_for_delivery':
            latest_location = RiderLocation.objects.filter(
                rider=order.rider,
                order=order
            ).first()
            if latest_location:
                rider_location = RiderLocationSerializer(latest_location).data
        
        return Response({
            'order': OrderSerializer(order).data,
            'delivery_statuses': statuses,
            'rider_location': rider_location
        })


# ============================================================================
# Rider Location Views
# ============================================================================

class RiderLocationViewSet(viewsets.ModelViewSet):
    """ViewSet for Rider location tracking"""
    serializer_class = RiderLocationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_rider:
            return RiderLocation.objects.filter(rider=user)
        if user.is_admin_user:
            return RiderLocation.objects.all()
        return RiderLocation.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(rider=self.request.user)


class UpdateLocationView(APIView):
    """API endpoint for riders to update their location"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_rider:
            return Response(
                {'error': 'Only riders can update location'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        accuracy = request.data.get('accuracy', 0)
        speed = request.data.get('speed', 0)
        heading = request.data.get('heading', 0)
        order_id = request.data.get('order_id')
        
        if not latitude or not longitude:
            return Response(
                {'error': 'Latitude and longitude required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create location record
        location = RiderLocation.objects.create(
            rider=request.user,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            speed=speed,
            heading=heading,
            order_id=order_id
        )
        
        # Update rider's current location
        try:
            rider_profile = request.user.rider_profile
            rider_profile.current_latitude = latitude
            rider_profile.current_longitude = longitude
            rider_profile.save()
        except Rider.DoesNotExist:
            pass
        
        return Response(
            RiderLocationSerializer(location).data,
            status=status.HTTP_201_CREATED
        )


# ============================================================================
# Review & Feedback Views
# ============================================================================

class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for Reviews"""
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Review.objects.filter(
            food_item_id=self.request.query_params.get('food_item')
        ).select_related('user', 'food_item')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FeedbackViewSet(viewsets.ModelViewSet):
    """ViewSet for Feedback"""
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_admin_user:
            return Feedback.objects.all().select_related('user', 'order')
        return Feedback.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ============================================================================
# Stripe Payment Views
# ============================================================================

class CreatePaymentIntentView(APIView):
    """Create Stripe payment intent"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        order_id = request.data.get('order_id')
        
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=int(order.grand_total() * 100),  # Convert to cents
                currency='usd',
                metadata={'order_id': order.id}
            )
            
            order.stripe_payment_intent_id = payment_intent.id
            order.save()
            
            return Response({
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id
            })
        except stripe.error.StripeError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class StripeWebhookView(APIView):
    """Handle Stripe webhooks"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            order_id = payment_intent['metadata'].get('order_id')
            
            if order_id:
                try:
                    order = Order.objects.get(id=order_id)
                    order.payment_status = 'paid'
                    order.save()
                except Order.DoesNotExist:
                    pass
        
        return Response({'status': 'success'})


# ============================================================================
# Analytics Views (Admin)
# ============================================================================

class DashboardStatsView(APIView):
    """Get dashboard statistics"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Time range
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Orders
        total_orders = Order.objects.filter(created_at__gte=start_date).count()
        pending_orders = Order.objects.filter(status='pending').count()
        
        # Revenue
        total_revenue = Order.objects.filter(
            created_at__gte=start_date,
            payment_status='paid'
        ).aggregate(Sum('grand_total'))['grand_total__sum'] or 0
        
        # Users
        total_customers = User.objects.filter(role='customer').count()
        total_riders = User.objects.filter(role='rider').count()
        
        # Recent orders
        recent_orders = OrderSerializer(
            Order.objects.all()[:10],
            many=True
        ).data
        
        return Response({
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'total_revenue': float(total_revenue),
            'total_customers': total_customers,
            'total_riders': total_riders,
            'recent_orders': recent_orders
        })


class ActiveDeliveriesView(APIView):
    """Get all active deliveries for admin tracking"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        active_orders = Order.objects.exclude(
            status__in=['delivered', 'cancelled']
        ).select_related('user', 'rider')
        
        deliveries = []
        for order in active_orders:
            rider_location = None
            if order.rider:
                latest = RiderLocation.objects.filter(rider=order.rider).first()
                if latest:
                    rider_location = RiderLocationSerializer(latest).data
            
            deliveries.append({
                'order': OrderSerializer(order).data,
                'rider_location': rider_location
            })
        
        return Response(deliveries)
