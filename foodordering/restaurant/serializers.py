"""
Django REST Framework Serializers for the Food Delivery System
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import (
    Category, FoodItem, Customer, Rider, RiderLocation,
    Cart, Order, OrderItem, DeliveryStatus, Review, Feedback
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'role', 'first_name', 'last_name', 
                  'phone', 'otp_verified', 'created_at']
        read_only_fields = ['id', 'otp_verified', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm', 'role', 
                  'first_name', 'last_name', 'phone']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class OTPSerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6, min_length=6)


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class FoodItemSerializer(serializers.ModelSerializer):
    """Serializer for FoodItem"""
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = FoodItem
        fields = ['id', 'name', 'description', 'price', 'image', 'category', 
                  'category_name', 'restaurant', 'is_available', 'stock', 
                  'average_rating', 'review_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CartSerializer(serializers.ModelSerializer):
    """Serializer for Cart"""
    food_item = FoodItemSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'food_item', 'quantity', 'subtotal', 'created_at']
        read_only_fields = ['id', 'created_at']


class CartCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating cart items"""
    class Meta:
        model = Cart
        fields = ['food_item', 'quantity']


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem"""
    food_item_name = serializers.CharField(source='food_item.name', read_only=True)
    food_item_image = serializers.ImageField(source='food_item.image', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'food_item', 'food_item_name', 'food_item_image', 
                  'quantity', 'price', 'subtotal']


class DeliveryStatusSerializer(serializers.ModelSerializer):
    """Serializer for DeliveryStatus"""
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    
    class Meta:
        model = DeliveryStatus
        fields = ['id', 'order', 'status', 'description', 'latitude', 
                  'longitude', 'timestamp', 'updated_by', 'updated_by_name']
        read_only_fields = ['id', 'timestamp']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order"""
    items = OrderItemSerializer(many=True, read_only=True)
    rider_name = serializers.CharField(source='rider.get_full_name', read_only=True)
    delivery_statuses = DeliveryStatusSerializer(many=True, read_only=True)
    grand_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'user', 'total_price', 'tax', 'delivery_fee',
                  'grand_total', 'delivery_address', 'phone', 'status', 'payment_status',
                  'payment_method', 'notes', 'rider', 'rider_name', 
                  'delivery_latitude', 'delivery_longitude',
                  'estimated_delivery_time', 'items', 'delivery_statuses',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders"""
    class Meta:
        model = Order
        fields = ['delivery_address', 'phone', 'notes', 'payment_method']


class RiderLocationSerializer(serializers.ModelSerializer):
    """Serializer for RiderLocation"""
    rider_name = serializers.CharField(source='rider.get_full_name', read_only=True)
    
    class Meta:
        model = RiderLocation
        fields = ['id', 'rider', 'rider_name', 'latitude', 'longitude', 
                  'accuracy', 'speed', 'heading', 'timestamp', 'order']
        read_only_fields = ['id', 'timestamp']


class RiderSerializer(serializers.ModelSerializer):
    """Serializer for Rider profile"""
    user = UserSerializer(read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Rider
        fields = ['id', 'user', 'email', 'vehicle_type', 'vehicle_number', 
                  'license_number', 'is_available_for_delivery', 
                  'current_latitude', 'current_longitude', 'created_at']
        read_only_fields = ['id', 'created_at']


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer profile"""
    user = UserSerializer(read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Customer
        fields = ['id', 'user', 'email', 'phone', 'address', 'created_at']
        read_only_fields = ['id', 'created_at']


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for Review"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    food_item_name = serializers.CharField(source='food_item.name', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'user', 'user_name', 'food_item', 'food_item_name', 
                  'rating', 'comment', 'approved', 'created_at']
        read_only_fields = ['id', 'user', 'approved', 'created_at']


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reviews"""
    class Meta:
        model = Review
        fields = ['food_item', 'rating', 'comment']


class FeedbackSerializer(serializers.ModelSerializer):
    """Serializer for Feedback"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Feedback
        fields = ['id', 'user', 'user_name', 'order', 'order_number', 'name',
                  'rating', 'feedback_text', 'sentiment', 'created_at']
        read_only_fields = ['id', 'user', 'sentiment', 'created_at']


class StripePaymentSerializer(serializers.Serializer):
    """Serializer for Stripe payment"""
    order_id = serializers.IntegerField()
    payment_method_id = serializers.CharField()
