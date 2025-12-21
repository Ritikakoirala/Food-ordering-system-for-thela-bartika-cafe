from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import FoodItem, Category

class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=15)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

class CheckoutForm(forms.Form):
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Delivery Address'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Special instructions (optional)'}))

class FoodItemForm(forms.ModelForm):
    class Meta:
        model = FoodItem
        fields = ['name', 'description', 'price', 'image', 'category', 'is_available', 'stock']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
