from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Customer URLs
    path('', views.home, name='home'),
    path('menu/', views.menu, name='menu'),
    path('food/<int:pk>/', views.food_detail, name='food_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_history, name='order_history'),
    path('order/<int:pk>/', views.order_detail, name='order_detail'),

    # Smart Features URLs
    path('live-orders/', views.live_orders, name='live_orders'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('feedback/', views.feedback, name='feedback'),
    path('emotional-kit/', views.emotional_kit, name='emotional_kit'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='restaurant/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    
    # Admin URLs
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/orders/', views.admin_orders, name='admin_orders'),
    path('admin-dashboard/order/<int:pk>/', views.admin_order_detail, name='admin_order_detail'),
    path('admin-dashboard/food-items/', views.admin_food_items, name='admin_food_items'),
    path('admin-dashboard/food-items/add/', views.admin_food_add, name='admin_food_add'),
    path('admin-dashboard/food-items/<int:pk>/edit/', views.admin_food_edit, name='admin_food_edit'),
    path('admin-dashboard/food-items/<int:pk>/delete/', views.admin_food_delete, name='admin_food_delete'),
    path('admin-dashboard/reviews/', views.admin_reviews, name='admin_reviews'),
    path('admin-dashboard/reviews/<int:pk>/approve/', views.admin_review_approve, name='admin_review_approve'),
    path('admin-dashboard/feedback/', views.admin_feedback, name='admin_feedback'),
]