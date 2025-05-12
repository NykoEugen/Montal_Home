from django.contrib import admin
from .models import Category, Furniture, Order, OrderItem
from django.utils.text import slugify

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Furniture)
class FurnitureAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_promotional', 'promotional_price', 'slug']
    list_filter = ['category', 'is_promotional']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'category', 'price', 'is_promotional', 'promotional_price', 'description', 'image')}),
        ('Параметри', {'fields': ('parameters',)}),
    )

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'customer_email', 'created_at']
    search_fields = ['customer_name', 'customer_email']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'furniture', 'quantity']