import json

from django.contrib import admin

from categories.models import Category
from furniture.models import Furniture
from params.models import FurnitureParameter, Parameter
from sub_categories.models import SubCategory

from checkout.models import Order, OrderItem

class FurnitureParameterInline(admin.TabularInline):
    model = FurnitureParameter
    extra = 0
    fields = ('parameter', 'value')
    verbose_name = "Параметр"
    verbose_name_plural = "Параметри"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parameter":
            # Якщо об'єкт Furniture існує і має sub_category
            if hasattr(self, 'parent_object') and self.parent_object and self.parent_object.sub_category:
                kwargs["queryset"] = self.parent_object.sub_category.allowed_params.all()
            else:
                # Якщо Furniture ще не створений, дозволяємо всі параметри
                kwargs["queryset"] = Parameter.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        # Зберігаємо об'єкт для доступу до sub_category
        self.parent_object = obj
        return super().get_formset(request, obj, **kwargs)

@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ('key', 'label')
    search_fields = ('key', 'label')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = ((None, {"fields": ("name", "slug", "image")}),)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "category"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ('allowed_params',)


@admin.register(Furniture)
class FurnitureAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "sub_category",
        "price",
        "is_promotional",
        "promotional_price",
        "slug",
    ]
    list_filter = ["sub_category", "is_promotional"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [FurnitureParameterInline]


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
    list_display = ["id", "customer_name", "customer_phone_number", "created_at"]
    search_fields = ["customer_name", "customer_phone_number"]
    inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "furniture", "quantity"]
