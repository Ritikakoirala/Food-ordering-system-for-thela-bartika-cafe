from .models import Cart

def cart_count(request):
    if request.user.is_authenticated:
        count = Cart.objects.filter(user=request.user).count()
    else:
        count = 0
    print(f"Cart count for user {request.user}: {count}")  # Debug log
    return {'cart_count': count}
