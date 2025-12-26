from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.views.decorators.http import require_POST
from decimal import Decimal
from .models import *
from .forms import *

# Helper function
def is_staff(user):
    return user.is_staff

# Customer Views
def home(request):
    featured_categories = Category.objects.all()[:6]
    popular_items = FoodItem.objects.filter(is_available=True)[:8]
    context = {
        'featured_categories': featured_categories,
        'popular_items': popular_items,
    }
    return render(request, 'restaurant/home.html', context)

def menu(request):
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search')
    
    items = FoodItem.objects.filter(is_available=True)
    
    if category_filter:
        items = items.filter(category_id=category_filter)
    
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    categories = Category.objects.all()
    
    context = {
        'items': items,
        'categories': categories,
        'selected_category': category_filter,
        'search_query': search_query,
    }
    return render(request, 'restaurant/menu.html', context)

def food_detail(request, pk):
    item = get_object_or_404(FoodItem, pk=pk)
    reviews = item.reviews.filter(approved=True)
    related_items = FoodItem.objects.filter(category=item.category, is_available=True).exclude(pk=pk)[:4]
    
    context = {
        'item': item,
        'reviews': reviews,
        'related_items': related_items,
    }
    return render(request, 'restaurant/food_detail.html', context)

@login_required
@require_POST
def add_to_cart(request):
    food_id = request.POST.get('food_id')
    quantity = int(request.POST.get('quantity', 1))
    
    food_item = get_object_or_404(FoodItem, pk=food_id, is_available=True)
    
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        food_item=food_item,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    cart_count = Cart.objects.filter(user=request.user).count()
    
    return JsonResponse({
        'success': True,
        'message': f'{food_item.name} added to cart!',
        'cart_count': cart_count
    })

@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('food_item')
    
    subtotal = sum(item.subtotal() for item in cart_items)
    tax = subtotal * Decimal('0.10')  # 10% tax
    total = subtotal + tax
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
    }
    return render(request, 'restaurant/cart.html', context)

@login_required
@require_POST
def update_cart(request):
    cart_id = request.POST.get('cart_id')
    quantity = int(request.POST.get('quantity', 1))
    
    cart_item = get_object_or_404(Cart, pk=cart_id, user=request.user)
    cart_item.quantity = quantity
    cart_item.save()
    
    subtotal = cart_item.subtotal()
    
    return JsonResponse({
        'success': True,
        'subtotal': float(subtotal)
    })

@login_required
@require_POST
def remove_from_cart(request):
    cart_id = request.POST.get('cart_id')
    cart_item = get_object_or_404(Cart, pk=cart_id, user=request.user)
    cart_item.delete()
    
    return JsonResponse({'success': True})

@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('food_item')
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty!')
        return redirect('menu')
    
    subtotal = sum(item.subtotal() for item in cart_items)
    tax = subtotal * Decimal('0.10')
    total = subtotal + tax
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(
                user=request.user,
                total_price=subtotal,
                tax=tax,
                delivery_address=form.cleaned_data['address'],
                phone=form.cleaned_data['phone'],
                notes=form.cleaned_data.get('notes', '')
            )
            
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    food_item=cart_item.food_item,
                    quantity=cart_item.quantity,
                    price=cart_item.food_item.price
                )
                
                # Reduce stock
                food = cart_item.food_item
                food.stock -= cart_item.quantity
                food.save()
            
            cart_items.delete()
            
            messages.success(request, f'Order placed successfully! Order number: {order.order_number}')
            return redirect('order_detail', pk=order.pk)
    else:
        initial_data = {}
        if hasattr(request.user, 'customer_profile'):
            profile = request.user.customer_profile
            initial_data = {
                'phone': profile.phone,
                'address': profile.address
            }
        form = CheckoutForm(initial=initial_data)
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
    }
    return render(request, 'restaurant/checkout.html', context)

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__food_item')
    return render(request, 'restaurant/order_history.html', {'orders': orders})

@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'restaurant/order_detail.html', {'order': order})

def register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Customer.objects.create(
                user=user,
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address']
            )
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'restaurant/register.html', {'form': form})

# Smart Features Views
@login_required
def live_orders(request):
    """Live order tracking view"""
    # Get the most recent active order for tracking
    order = Order.objects.filter(user=request.user).exclude(status='delivered').first()

    if not order:
        # If no active orders, show a message
        context = {
            'no_active_orders': True,
            'page_title': 'Live Order Tracking'
        }
        return render(request, 'restaurant/live_orders.html', context)

    # Define order stages
    stages = [
        {'key': 'pending', 'label': 'Order Placed', 'icon': '📝', 'message': 'Your order has been received'},
        {'key': 'preparing', 'label': 'Preparing Food', 'icon': '🍳', 'message': 'Your food is being prepared'},
        {'key': 'ready', 'label': 'Packed & Ready', 'icon': '📦', 'message': 'Your order is packed and ready'},
        {'key': 'out_for_delivery', 'label': 'Out for Delivery', 'icon': '🚴', 'message': 'Rider is on the way'},
        {'key': 'delivered', 'label': 'Delivered', 'icon': '✅', 'message': 'Enjoy your meal!'},
    ]

    # Map order status to stages
    status_mapping = {
        'pending': 0,
        'preparing': 1,
        'ready': 2,
        'out_for_delivery': 3,
        'delivered': 4,
    }

    current_stage_index = status_mapping.get(order.status, 0)

    # Calculate estimated times (simplified)
    estimated_times = {
        0: "15-20 mins",
        1: "10-15 mins",
        2: "5-10 mins",
        3: "2-5 mins",
        4: "Delivered"
    }

    context = {
        'order': order,
        'stages': stages,
        'current_stage_index': current_stage_index,
        'estimated_time': estimated_times.get(current_stage_index, "Unknown"),
        'page_title': 'Live Order Tracking'
    }
    return render(request, 'restaurant/live_orders.html', context)

@login_required
def recommendations(request):
    """AI-based recommendations view"""
    # Get user's past orders and recommend similar items
    user_orders = Order.objects.filter(user=request.user)
    ordered_items = FoodItem.objects.filter(
        orderitem__order__in=user_orders
    ).distinct()[:8]

    context = {
        'items': ordered_items,
        'page_title': 'AI Recommendations'
    }
    return render(request, 'restaurant/menu.html', context)  # Reuse menu template

@login_required
def feedback(request):
    """Sentiment-based feedback view"""
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        name = request.POST.get('name', '')
        rating = request.POST.get('rating')
        feedback_text = request.POST.get('feedback_text')

        order = None
        if order_id:
            try:
                order = Order.objects.get(pk=order_id, user=request.user)
            except Order.DoesNotExist:
                pass

        feedback_obj = Feedback.objects.create(
            user=request.user,
            order=order,
            name=name,
            rating=int(rating),
            feedback_text=feedback_text
        )

        messages.success(request, 'Thank you for your feedback! Your sentiment has been analyzed.')
        return redirect('feedback')

    # Show recent orders for feedback
    recent_orders = Order.objects.filter(user=request.user)[:10]
    context = {
        'orders': recent_orders,
        'page_title': 'Provide Feedback'
    }
    return render(request, 'restaurant/feedback.html', context)

@login_required
def emotional_kit(request):
    """Auto-gift emotional kit view"""
    # Show available rewards/gifts
    context = {
        'page_title': 'Your Emotional Kit',
        'message': 'Coming soon! Exclusive rewards based on your loyalty.'
    }
    return render(request, 'restaurant/home.html', context)  # Basic placeholder


# Admin Dashboard Views
@user_passes_test(is_staff)
def admin_dashboard(request):
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    total_revenue = Order.objects.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_customers = Customer.objects.count()
    
    recent_orders = Order.objects.all()[:10]
    
    context = {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'total_revenue': total_revenue,
        'total_customers': total_customers,
        'recent_orders': recent_orders,
    }
    return render(request, 'restaurant/admin/dashboard.html', context)

@user_passes_test(is_staff)
def admin_orders(request):
    status_filter = request.GET.get('status')
    orders = Order.objects.all().prefetch_related('items__food_item')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    context = {
        'orders': orders,
        'selected_status': status_filter,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'restaurant/admin/orders.html', context)

@user_passes_test(is_staff)
def admin_order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        order.status = new_status
        order.save()
        messages.success(request, 'Order status updated!')
        return redirect('admin_order_detail', pk=pk)
    
    return render(request, 'restaurant/admin/order_detail.html', {'order': order})

@user_passes_test(is_staff)
def admin_food_items(request):
    items = FoodItem.objects.all().select_related('category')
    return render(request, 'restaurant/admin/food_items.html', {'items': items})

@user_passes_test(is_staff)
def admin_food_add(request):
    if request.method == 'POST':
        form = FoodItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Food item added successfully!')
            return redirect('admin_food_items')
    else:
        form = FoodItemForm()
    return render(request, 'restaurant/admin/food_form.html', {'form': form, 'action': 'Add'})

@user_passes_test(is_staff)
def admin_food_edit(request, pk):
    item = get_object_or_404(FoodItem, pk=pk)
    if request.method == 'POST':
        form = FoodItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Food item updated successfully!')
            return redirect('admin_food_items')
    else:
        form = FoodItemForm(instance=item)
    return render(request, 'restaurant/admin/food_form.html', {'form': form, 'action': 'Edit'})

@user_passes_test(is_staff)
@require_POST
def admin_food_delete(request, pk):
    item = get_object_or_404(FoodItem, pk=pk)
    item.delete()
    messages.success(request, 'Food item deleted!')
    return redirect('admin_food_items')

@user_passes_test(is_staff)
def admin_reviews(request):
    reviews = Review.objects.all().select_related('user', 'food_item')
    return render(request, 'restaurant/admin/reviews.html', {'reviews': reviews})

@user_passes_test(is_staff)
@require_POST
def admin_review_approve(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.approved = not review.approved
    review.save()
    return JsonResponse({'success': True, 'approved': review.approved})

@user_passes_test(is_staff)
def admin_feedback(request):
    """Admin view for managing feedback"""
    sentiment_filter = request.GET.get('sentiment')
    feedbacks = Feedback.objects.all().select_related('user', 'order')

    if sentiment_filter:
        feedbacks = feedbacks.filter(sentiment=sentiment_filter)

    context = {
        'feedbacks': feedbacks,
        'selected_sentiment': sentiment_filter,
        'sentiment_choices': Feedback.SENTIMENT_CHOICES,
    }
    return render(request, 'restaurant/admin/feedback.html', context)
