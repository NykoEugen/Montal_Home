import json

from django.contrib import admin
from django.utils import timezone

from categories.models import Category
from checkout.models import Order, OrderItem
from furniture.models import Furniture, FurnitureSizeVariant
from params.models import FurnitureParameter, Parameter
from sub_categories.models import SubCategory


class FurnitureParameterInline(admin.TabularInline):
    model = FurnitureParameter
    extra = 0
    fields = ("parameter", "value")
    verbose_name = "Параметр"
    verbose_name_plural = "Параметри"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parameter":
            # Якщо об'єкт Furniture існує і має sub_category
            if (
                hasattr(self, "parent_object")
                and self.parent_object
                and self.parent_object.sub_category
            ):
                kwargs["queryset"] = (
                    self.parent_object.sub_category.allowed_params.all()
                )
            else:
                # Якщо Furniture ще не створений, дозволяємо всі параметри
                kwargs["queryset"] = Parameter.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        # Зберігаємо об'єкт для доступу до sub_category
        self.parent_object = obj
        return super().get_formset(request, obj, **kwargs)


class FurnitureSizeVariantInline(admin.TabularInline):
    """Inline admin for furniture size variants."""
    model = FurnitureSizeVariant
    extra = 1
    fields = ['height', 'width', 'length', 'price']


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ("key", "label")
    search_fields = ("key", "label")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = ((None, {"fields": ("name", "slug", "image")}),)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "category"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("allowed_params",)


@admin.register(Furniture)
class FurnitureAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "sub_category",
        "price",
        "is_promotional",
        "promotional_price",
        "available_sizes",
        "slug",
        "selected_fabric_brand",
        "fabric_value",
    ]
    list_filter = ["sub_category", "is_promotional", "selected_fabric_brand"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [FurnitureParameterInline, FurnitureSizeVariantInline]
    
    def available_sizes(self, obj):
        return obj.get_available_sizes()
    available_sizes.short_description = "Доступні розміри"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["furniture", "price", "quantity", "get_parameters"]
    readonly_fields = ["furniture", "price", "quantity", "get_parameters"]

    def get_parameters(self, obj) -> str:
        return json.dumps(obj.parameters, ensure_ascii=False, indent=2)

    get_parameters.short_description = "Параметри"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "customer_name",
        "customer_last_name",
        "customer_phone_number",
        "delivery_type",
        "payment_type",
        "created_at",
    ]
    list_filter = ["delivery_type", "payment_type", "created_at"]
    search_fields = [
        "customer_name",
        "customer_last_name",
        "customer_phone_number",
        "customer_email",
    ]
    readonly_fields = ["created_at"]
    inlines = [OrderItemInline]

    fieldsets = (
        (
            "Контактна інформація",
            {
                "fields": (
                    "customer_name",
                    "customer_last_name",
                    "customer_phone_number",
                    "customer_email",
                )
            },
        ),
        (
            "Доставка",
            {
                "fields": (
                    "delivery_type",
                    "delivery_city",
                    "delivery_branch",
                    "delivery_address",
                )
            },
        ),
        ("Оплата", {"fields": ("payment_type",)}),
        ("Системна інформація", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "furniture", "quantity", "price", "total_price"]
    list_filter = ["order__created_at"]
    search_fields = ["order__customer_name", "furniture__name"]
    readonly_fields = ["price"]

    def total_price(self, obj):
        return obj.price * obj.quantity

    total_price.short_description = "Загальна вартість"


@admin.register(FurnitureSizeVariant)
class FurnitureSizeVariantAdmin(admin.ModelAdmin):
    """Admin configuration for FurnitureSizeVariant model."""
    list_display = [
        'furniture', 'height', 'width', 'length', 'price', 'dimensions'
    ]
    list_filter = ['furniture__sub_category']
    search_fields = ['furniture__name']
    ordering = ['furniture__name', 'height', 'width', 'length']
