"""
Models for the Food Delivery System
Including Custom User with roles, OTP, Rider tracking, and Delivery status
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
import uuid
from phonenumber_field.modelfields import PhoneNumberField

from .managers import UserManager


class User(AbstractUser):
    """
    Custom User model with role-based authentication
    Roles: admin, customer, rider, restaurant
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('customer', 'Customer'),
        ('rider', 'Rider'),
        ('restaurant', 'Restaurant'),
    ]
    
    username = models.CharField(max_length=150, unique=False, null=True, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    
    # OTP fields
    otp_secret = models.CharField(max_length=32, blank=True)
    otp_verified = models.BooleanField(default=False)
    phone = PhoneNumberField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Encryption for sensitive fields
    encrypted_phone = models.TextField(blank=True)
    encrypted_address = models.TextField(blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} ({self.role})"
    
    @property
    def is_customer(self):
        return self.role == 'customer' or self.is_superuser
    
    @property
    def is_rider(self):
        return self.role == 'rider'
    
    @property
    def is_restaurant(self):
        return self.role == 'restaurant'
    
    @property
    def is_admin_user(self):
        return self.role == 'admin' or self.is_superuser
    
    def get_decrypted_phone(self):
        """Decrypt phone number using Fernet"""
        if not self.encrypted_phone:
            return None
        from cryptography.fernet import Fernet
        import os
        key = os.getenv('FERNET_ENCRYPTION_KEY', '').encode()
        if not key:
            return self.phone
        try:
            f = Fernet(key)
            return f.decrypt(self.encrypted_phone.encode()).decode()
        except:
            return self.phone
    
    def get_decrypted_address(self):
        """Decrypt address using Fernet"""
        if not self.encrypted_address:
            return None
        from cryptography.fernet import Fernet
        import os
        key = os.getenv('FERNET_ENCRYPTION_KEY', '').encode()
        if not key:
            return None
        try:
            f = Fernet(key)
            return f.decrypt(self.encrypted_address.encode()).decode()
        except:
            return None


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class FoodItem(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='food_items/')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    restaurant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='food_items', 
                                    limit_choices_to={'role': 'restaurant'}, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    stock = models.IntegerField(default=100, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def average_rating(self):
        reviews = self.reviews.filter(approved=True)
        if reviews.exists():
            return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0
    
    def review_count(self):
        return self.reviews.filter(approved=True).count()


class Customer(models.Model):
    """Extended profile for customer users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=15)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.phone}"


class Rider(models.Model):
    """Extended profile for rider users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rider_profile')
    vehicle_type = models.CharField(max_length=50, choices=[
        ('bicycle', 'Bicycle'),
        ('motorcycle', 'Motorcycle'),
        ('car', 'Car'),
    ], default='motorcycle')
    vehicle_number = models.CharField(max_length=20, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    is_available_for_delivery = models.BooleanField(default=True)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Rider: {self.user.get_full_name() or self.user.email}"


class RiderLocation(models.Model):
    """Live GPS tracking for riders"""
    rider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='locations',
                              limit_choices_to={'role': 'rider'})
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(default=0.0)
    speed = models.FloatField(default=0.0, help_text="Speed in km/h")
    heading = models.FloatField(default=0.0, help_text="Direction in degrees")
    timestamp = models.DateTimeField(default=timezone.now)
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='rider_locations')
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['rider', '-timestamp']),
        ]
    
    def __str__(self):
        return f"Rider {self.rider.email} - {self.timestamp}"


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'food_item')
    
    def __str__(self):
        return f"{self.user.email} - {self.food_item.name} x{self.quantity}"
    
    def subtotal(self):
        return self.quantity * self.food_item.price


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=100, unique=True, editable=False)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_address = models.TextField()
    phone = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, default='cash')
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    # Rider assignment
    rider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='delivery_orders', limit_choices_to={'role': 'rider'})
    
    # Location tracking
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    
    # Soft delete fields
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def grand_total(self):
        return self.total_price + self.tax + self.delivery_fee
    
    @property
    def is_active(self):
        return self.status in ['pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery']
    
    @property
    def can_cancel(self):
        return self.status in ['pending', 'confirmed']
    
    def soft_delete(self):
        """Soft delete the order"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        """Restore a soft-deleted order"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.food_item.name} x{self.quantity}"
    
    def subtotal(self):
        return self.quantity * self.price


class DeliveryStatus(models.Model):
    """Real-time delivery status tracking"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='delivery_statuses')
    status = models.CharField(max_length=50)
    description = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.status}"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'food_item')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.food_item.name} ({self.rating}★)"


class Feedback(models.Model):
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='feedbacks', null=True, blank=True)
    name = models.CharField(max_length=100, blank=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback_text = models.TextField()
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, default='neutral')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback from {self.user.email} - {self.sentiment}"

    def save(self, *args, **kwargs):
        # Simple sentiment analysis based on keywords
        text = self.feedback_text.lower()
        positive_words = ['great', 'excellent', 'amazing', 'love', 'fantastic', 'delicious', 'perfect', 'awesome', 'good', 'best', 'wonderful']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'worst', 'disgusting', 'slow', 'cold', 'rude', 'disappointed']

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)

        if positive_count > negative_count:
            self.sentiment = 'positive'
        elif negative_count > positive_count:
            self.sentiment = 'negative'
        else:
            self.sentiment = 'neutral'

        super().save(*args, **kwargs)
