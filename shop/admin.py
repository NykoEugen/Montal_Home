import json

from django.contrib import admin
from .models import Category, Furniture, Order, OrderItem
from django.utils.text import slugify

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'image')}),
    )

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

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['furniture', 'price', 'quantity', 'get_parameters']
    readonly_fields = ['furniture', 'price', 'quantity', 'get_parameters']

    def get_parameters(self, obj):
        return json.dumps(obj.parameters, ensure_ascii=False, indent=2)

    get_parameters.short_description = 'Параметри'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'customer_email', 'created_at']
    search_fields = ['customer_name', 'customer_email']
    inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'furniture', 'quantity']