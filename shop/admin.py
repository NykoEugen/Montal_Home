import json

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from categories.models import Category
from checkout.models import Order, OrderItem
from furniture.models import Furniture, FurnitureSizeVariant, FurnitureImage, FurnitureVariantImage
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


class FurnitureImageInline(admin.TabularInline):
    model = FurnitureImage
    extra = 1
    fields = ["image", "alt_text", "position"]


class FurnitureVariantImageInline(admin.TabularInline):
    model = FurnitureVariantImage
    extra = 1
    fields = ('name', 'image', 'link', 'is_default', 'position')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px; object-fit: cover;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Превью'


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
        "article_code",
        "stock_status",
        "sub_category",
        "price",
        "is_promotional",
        "promotional_price",
        "available_sizes",
        "slug",
        "selected_fabric_brand",
        "fabric_value",
    ]
    list_filter = ["sub_category", "is_promotional", "selected_fabric_brand", "stock_status"]
    search_fields = ["name", "description", "article_code"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [FurnitureParameterInline, FurnitureSizeVariantInline, FurnitureVariantImageInline, FurnitureImageInline]
    
    def available_sizes(self, obj):
        return obj.get_available_sizes()
    available_sizes.short_description = "Доступні розміри"
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'article_code', 'stock_status', 'slug', 'sub_category', 'description', 'image')
        }),
        ('Ціни', {
            'fields': ('price', 'is_promotional', 'promotional_price')
        }),
        ('Тканина', {
            'fields': ('selected_fabric_brand', 'fabric_value'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["furniture", "variant_info", "size_variant_info", "fabric_info", "price", "quantity", "get_total_price"]
    readonly_fields = ["furniture", "variant_info", "size_variant_info", "fabric_info", "price", "quantity", "get_total_price"]

    def variant_info(self, obj):
        if obj.variant_image_id:
            try:
                from furniture.models import FurnitureVariantImage
                variant = FurnitureVariantImage.objects.get(id=obj.variant_image_id)
                return f"{variant.name}"
            except FurnitureVariantImage.DoesNotExist:
                return f"Варіант ID {obj.variant_image_id} (видалено)"
        return "Стандартний варіант"
    
    variant_info.short_description = "Колір"

    def size_variant_info(self, obj):
        if obj.size_variant_id:
            try:
                from furniture.models import FurnitureSizeVariant
                variant = FurnitureSizeVariant.objects.get(id=obj.size_variant_id)
                return f"{variant.dimensions} - {variant.price} грн"
            except FurnitureSizeVariant.DoesNotExist:
                return f"Розмір ID {obj.size_variant_id} (видалено)"
        return "Стандартний розмір"
    
    size_variant_info.short_description = "Розмір (ВхШхД)"

    def fabric_info(self, obj):
        if obj.fabric_category_id:
            try:
                from fabric_category.models import FabricCategory
                fabric = FabricCategory.objects.get(id=obj.fabric_category_id)
                return f"{fabric.name} - {fabric.price} грн"
            except FabricCategory.DoesNotExist:
                return f"Тканина ID {obj.fabric_category_id} (видалено)"
        return "Стандартна тканина"
    
    fabric_info.short_description = "Тканина"

    def get_total_price(self, obj):
        if obj.price is not None:
            return f"{obj.price * obj.quantity:.2f} грн"
        return "Ціна не вказана"
    
    get_total_price.short_description = "Загальна вартість"


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
    list_display = ["order", "furniture", "quantity", "price", "variant_info", "size_variant_info", "fabric_info", "total_price"]
    list_filter = ["order__created_at"]
    search_fields = ["order__customer_name", "furniture__name"]
    readonly_fields = ["price"]

    def total_price(self, obj):
        if obj.price is not None:
            return obj.price * obj.quantity
        return 0

    total_price.short_description = "Загальна вартість"
    
    def variant_info(self, obj):
        if obj.variant_image_id:
            try:
                from furniture.models import FurnitureVariantImage
                variant = FurnitureVariantImage.objects.get(id=obj.variant_image_id)
                return f"{variant.name}"
            except FurnitureVariantImage.DoesNotExist:
                return f"Варіант ID {obj.variant_image_id} (видалено)"
        return "Стандартний варіант"
    
    variant_info.short_description = "Колір"
    
    def size_variant_info(self, obj):
        if obj.size_variant_id:
            try:
                from furniture.models import FurnitureSizeVariant
                variant = FurnitureSizeVariant.objects.get(id=obj.size_variant_id)
                return f"{variant.dimensions} - {variant.price} грн"
            except FurnitureSizeVariant.DoesNotExist:
                return f"Розмір ID {obj.size_variant_id} (видалено)"
        return "Стандартний розмір"
    
    size_variant_info.short_description = "Розмір та ціна"
    
    def fabric_info(self, obj):
        if obj.fabric_category_id:
            try:
                from fabric_category.models import FabricCategory
                fabric = FabricCategory.objects.get(id=obj.fabric_category_id)
                return f"{fabric.name} - {fabric.price} грн"
            except FabricCategory.DoesNotExist:
                return f"Тканина ID {obj.fabric_category_id} (видалено)"
        return "Стандартна тканина"
    
    fabric_info.short_description = "Тканина та ціна"


@admin.register(FurnitureSizeVariant)
class FurnitureSizeVariantAdmin(admin.ModelAdmin):
    """Admin configuration for FurnitureSizeVariant model."""
    list_display = [
        'furniture', 'height', 'width', 'length', 'price', 'dimensions'
    ]
    list_filter = ['furniture__sub_category']
    search_fields = ['furniture__name']
    ordering = ['furniture__name', 'height', 'width', 'length']
