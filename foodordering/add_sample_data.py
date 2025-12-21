import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodordering.settings')
django.setup()

from restaurant.models import Category, FoodItem

# Create categories
categories = ['Pizza', 'Burger', 'Pasta', 'Dessert', 'Drinks']
for cat_name in categories:
    Category.objects.get_or_create(name=cat_name)

# Get categories
pizza = Category.objects.get(name='Pizza')
burger = Category.objects.get(name='Burger')
pasta = Category.objects.get(name='Pasta')
dessert = Category.objects.get(name='Dessert')
drinks = Category.objects.get(name='Drinks')

# Create food items
food_items = [
    {'name': 'Margherita Pizza', 'description': 'Fresh tomato sauce, mozzarella cheese, basil', 'price': 12.99, 'category': pizza},
    {'name': 'Pepperoni Pizza', 'description': 'Pepperoni, cheese, tomato sauce', 'price': 14.99, 'category': pizza},
    {'name': 'Cheese Burger', 'description': 'Beef patty, cheese, lettuce, tomato', 'price': 9.99, 'category': burger},
    {'name': 'Spaghetti Carbonara', 'description': 'Pasta with bacon, eggs, cheese', 'price': 11.99, 'category': pasta},
    {'name': 'Chocolate Cake', 'description': 'Rich chocolate cake', 'price': 6.99, 'category': dessert},
    {'name': 'Coca Cola', 'description': 'Refreshing soft drink', 'price': 2.99, 'category': drinks},
]

for item_data in food_items:
    FoodItem.objects.get_or_create(
        name=item_data['name'],
        defaults={
            'description': item_data['description'],
            'price': item_data['price'],
            'category': item_data['category'],
            'image': 'food_items/default.jpg'  # Placeholder image
        }
    )

print("Sample data added successfully!")