"""
Custom user managers for role-based authentication
"""
from django.contrib.auth.models import BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom user manager for handling email-based authentication
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class RiderManager(BaseUserManager):
    """
    Manager for Rider-specific queries
    """
    def get_queryset(self):
        return super().get_queryset().filter(role='rider')
    
    def available(self):
        return self.get_queryset().filter(is_available_for_delivery=True)


class CustomerManager(BaseUserManager):
    """
    Manager for Customer-specific queries
    """
    def get_queryset(self):
        return super().get_queryset().filter(role='customer')


class RestaurantManager(BaseUserManager):
    """
    Manager for Restaurant-specific queries
    """
    def get_queryset(self):
        return super().get_queryset().filter(role='restaurant')
