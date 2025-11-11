from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError

from categories.models import Category
from checkout.models import LiqPayReceipt, Order, OrderItem
from furniture.models import (
    Furniture,
    FurnitureCustomOption,
    FurnitureSizeVariant,
    FurnitureImage,
    FurnitureVariantImage,
)
from params.models import FurnitureParameter, Parameter
from sub_categories.models import SubCategory
from store.admin_utils import ResilientModelAdmin, ResilientInlineAdmin


class FurnitureParameterInline(ResilientInlineAdmin):
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


class FurnitureCustomOptionInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if self.instance is None:
            return
        has_values = any(
            form.cleaned_data.get("value") and not form.cleaned_data.get("DELETE", False)
            for form in self.forms
            if hasattr(form, "cleaned_data") and form.cleaned_data
        )
        if has_values and not getattr(self.instance, "custom_option_name", ""):
            raise ValidationError("Вкажіть назву додаткового параметра перед додаванням варіантів.")


class FurnitureCustomOptionInline(ResilientInlineAdmin):
    model = FurnitureCustomOption
    extra = 1
    fields = ("value", "price_delta", "position", "is_active")
    formset = FurnitureCustomOptionInlineFormSet
    verbose_name = "Варіант параметра"
    verbose_name_plural = "Варіанти параметра"

    def get_formset(self, request, obj=None, **kwargs):
        self.parent_object = obj
        return super().get_formset(request, obj, **kwargs)


class FurnitureSizeVariantInline(ResilientInlineAdmin):
    """Inline admin for furniture size variants."""
    model = FurnitureSizeVariant
    extra = 1
    fields = [
        'height',
        'width',
        'length',
        'is_foldable',
        'unfolded_length',
        'price',
        'is_promotional',
        'promotional_price',
        'sale_end_date',
        'parameter',
        'parameter_value',
        'current_price_display',
        'discount_display',
    ]
    readonly_fields = ['current_price_display', 'discount_display']
    
    def current_price_display(self, obj):
        """Display current price with styling."""
        if not obj.pk:  # New object, not saved yet
            return '-'
        try:
            if obj.is_on_sale:
                return format_html(
                    '<span style="color: #dc3545; font-weight: bold;">{} грн</span>',
                    obj.current_price
                )
            return format_html('{} грн', obj.current_price)
        except:
            return '-'
    current_price_display.short_description = "Поточна ціна"
    
    def discount_display(self, obj):
        """Display discount percentage."""
        if not obj.pk:  # New object, not saved yet
            return '-'
        try:
            if obj.discount_percentage > 0:
                return format_html(
                    '<span style="color: #dc3545; font-weight: bold;">-{}%</span>',
                    obj.discount_percentage
                )
            return '-'
        except:
            return '-'
    discount_display.short_description = "Знижка"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parameter":
            parent = getattr(self, "parent_object", None)
            if parent and parent.sub_category_id:
                kwargs["queryset"] = parent.sub_category.allowed_params.all()
            else:
                kwargs["queryset"] = Parameter.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        self.parent_object = obj
        return super().get_formset(request, obj, **kwargs)


class FurnitureImageInline(ResilientInlineAdmin):
    model = FurnitureImage
    extra = 1
    fields = ["image", "alt_text", "position"]


class FurnitureVariantImageInline(ResilientInlineAdmin):
    model = FurnitureVariantImage
    extra = 1
    fields = ('name', 'stock_status', 'image', 'link', 'is_default', 'position')
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
class ParameterAdmin(ResilientModelAdmin):
    list_display = ("key", "label")
    search_fields = ("key", "label")


@admin.register(Category)
class CategoryAdmin(ResilientModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = ((None, {"fields": ("name", "slug", "image")}),)


@admin.register(SubCategory)
class SubCategoryAdmin(ResilientModelAdmin):
    list_display = ["name", "slug", "category"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("allowed_params",)


@admin.register(Furniture)
class FurnitureAdmin(ResilientModelAdmin):
    list_display = [
        "name",
        "article_code",
        "stock_status",
        "sub_category",
        "price",
        "is_promotional",
        "promotional_price",
        "sale_status",
        "sale_end_date",
        "discount_percentage",
        "available_sizes",
        "slug",
        "selected_fabric_brand",
        "fabric_value",
    ]
    list_filter = [
        "sub_category", 
        "is_promotional", 
        "selected_fabric_brand", 
        "stock_status",
        ("sale_end_date", admin.DateFieldListFilter),
    ]
    search_fields = ["name", "description", "article_code"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [FurnitureParameterInline, FurnitureCustomOptionInline, FurnitureSizeVariantInline, FurnitureVariantImageInline, FurnitureImageInline]
    actions = ['set_sale_end_date', 'clear_sale_end_date', 'make_promotional', 'remove_promotional', 'cleanup_expired_promotions', 'clear_size_variant_promotions']
    
    def available_sizes(self, obj):
        return obj.get_available_sizes()
    available_sizes.short_description = "Доступні розміри"
    
    def sale_status(self, obj):
        """Display sale status with color coding."""
        if not obj.is_promotional:
            return format_html('<span style="color: #666;">Не акційний</span>')
        
        if not obj.sale_end_date:
            return format_html('<span style="color: #28a745; font-weight: bold;">Постійна акція</span>')
        
        if obj.is_sale_active:
            time_left = obj.sale_end_date - timezone.now()
            days_left = time_left.days
            if days_left == 0:
                return format_html('<span style="color: #dc3545; font-weight: bold;">Завершується сьогодні!</span>')
            elif days_left <= 3:
                return format_html('<span style="color: #fd7e14; font-weight: bold;">Закінчується через {} дн.</span>', days_left)
            else:
                return format_html('<span style="color: #28a745;">Активна ({} дн.)</span>', days_left)
        else:
            return format_html('<span style="color: #dc3545;">Акція закінчена</span>')
    sale_status.short_description = "Статус акції"
    
    def discount_percentage(self, obj):
        """Display discount percentage."""
        if obj.is_promotional and obj.discount_percentage > 0:
            return format_html('<span style="color: #dc3545; font-weight: bold;">-{}%</span>', obj.discount_percentage)
        return '-'
    discount_percentage.short_description = "Знижка"
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'article_code', 'stock_status', 'slug', 'sub_category', 'description', 'image')
        }),
        ('Ціни та акції', {
            'fields': ('price', 'is_promotional', 'promotional_price', 'sale_end_date'),
            'description': 'Налаштування цін та акційних пропозицій з таймером'
        }),
        ('Тканина', {
            'fields': ('selected_fabric_brand', 'fabric_value'),
            'classes': ('collapse',)
        }),
        ('Додатковий параметр', {
            'fields': ('custom_option_name',),
            'description': 'Задайте універсальний параметр. Варіанти додаються нижче у списку.',
            'classes': ('collapse',)
        }),
        ('Системна інформація', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at', 'discount_percentage']
    
    # Admin actions for bulk operations
    def set_sale_end_date(self, request, queryset):
        """Set sale end date for selected items."""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        # Store selected IDs in session for the next step
        request.session['sale_items_ids'] = list(queryset.values_list('id', flat=True))
        return HttpResponseRedirect(reverse('admin:sale_end_date_form'))
    set_sale_end_date.short_description = "Встановити дату закінчення акції"
    
    def clear_sale_end_date(self, request, queryset):
        """Clear sale end date for selected items."""
        updated = queryset.update(sale_end_date=None)
        self.message_user(request, f"Дату закінчення акції очищено для {updated} товарів.")
    clear_sale_end_date.short_description = "Очистити дату закінчення акції"
    
    def make_promotional(self, request, queryset):
        """Make selected items promotional."""
        updated = queryset.update(is_promotional=True)
        self.message_user(request, f"{updated} товарів зроблено акційними.")
    make_promotional.short_description = "Зробити акційними"
    
    def remove_promotional(self, request, queryset):
        """Remove promotional status from selected items."""
        updated = queryset.update(is_promotional=False, promotional_price=None, sale_end_date=None)
        self.message_user(request, f"Акційний статус видалено з {updated} товарів.")
    remove_promotional.short_description = "Видалити акційний статус"
    
    def cleanup_expired_promotions(self, request, queryset):
        """Clean up expired promotions for all furniture items."""
        from django.core.management import call_command
        
        try:
            call_command('cleanup_all_expired_promotions', verbosity=0)
            self.message_user(request, "Очищення закінчених акцій виконано успішно.")
        except Exception as e:
            self.message_user(request, f"Помилка при очищенні акцій: {e}", level='ERROR')
    cleanup_expired_promotions.short_description = "Очистити закінчені акції"
    
    def clear_size_variant_promotions(self, request, queryset):
        """Clear promotional prices from size variants of selected furniture."""
        total_cleared = 0
        for furniture in queryset:
            cleared = furniture.size_variants.filter(promotional_price__isnull=False).update(promotional_price=None)
            total_cleared += cleared
        
        self.message_user(request, f"Акційні ціни видалено з {total_cleared} розмірних варіантів.")
    clear_size_variant_promotions.short_description = "Очистити акційні ціни розмірних варіантів"


class OrderItemInline(ResilientInlineAdmin):
    model = OrderItem
    extra = 0
    fields = [
        "furniture",
        "variant_info",
        "size_variant_info",
        "fabric_info",
        "custom_option_info",
        "price",
        "quantity",
        "get_total_price",
    ]
    readonly_fields = [
        "furniture",
        "variant_info",
        "size_variant_info",
        "fabric_info",
        "custom_option_info",
        "price",
        "quantity",
        "get_total_price",
    ]

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
        if obj.size_variant_id and obj.size_variant_id != 'base':
            try:
                from furniture.models import FurnitureSizeVariant
                variant = FurnitureSizeVariant.objects.get(id=obj.size_variant_id)
                return f"{variant.dimensions} - {variant.price} грн"
            except (FurnitureSizeVariant.DoesNotExist, ValueError):
                return f"Розмір ID {obj.size_variant_id} (видалено або недійсний)"
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

    def custom_option_info(self, obj):
        if obj.custom_option_value:
            label = obj.custom_option_name or "Параметр"
            price_part = ""
            if getattr(obj, "custom_option_price", None):
                try:
                    price_value = float(obj.custom_option_price)
                    if price_value:
                        price_part = f" (+{price_value:g} грн)"
                except (TypeError, ValueError):
                    pass
            return f"{label}: {obj.custom_option_value}{price_part}"
        return "Не вибрано"
    custom_option_info.short_description = "Додатковий параметр"

    def get_total_price(self, obj):
        if obj.price is not None:
            return f"{obj.price * obj.quantity:.2f} грн"
        return "Ціна не вказана"
    
    get_total_price.short_description = "Загальна вартість"


@admin.register(Order)
class OrderAdmin(ResilientModelAdmin):
    list_display = [
        "id",
        "customer_name",
        "customer_last_name",
        "customer_phone_number",
        "delivery_type",
        "payment_type",
        "iban_invoice_requested",
        "iban_invoice_generated",
        "iban_invoice_status",
        "created_at",
        "total_items",
        "total_amount",
        "total_savings",
        "iban_invoice_status",
    ]
    list_filter = ["delivery_type", "payment_type", "iban_invoice_requested", "iban_invoice_generated", "created_at"]
    search_fields = [
        "customer_name",
        "customer_last_name",
        "customer_phone_number",
        "customer_email",
    ]
    readonly_fields = [
        "created_at",
        "total_savings",
        "total_original_amount",
        "total_amount",
        "total_items",
        "iban_invoice_generated",
    ]
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
        (
            "Оплата",
            {
                "fields": (
                    "payment_type",
                    "iban_invoice_requested",
                    "iban_invoice_generated",
                )
            },
        ),
        ("Системна інформація", {"fields": ("created_at", "total_savings", "total_original_amount"), "classes": ("collapse",)}),
    )

    actions = ["generate_iban_invoice_action"]

    def total_items(self, obj):
        return sum(item.quantity for item in obj.orderitem_set.all())

    total_items.short_description = "Товарів"

    def total_amount(self, obj):
        total = sum(item.price * item.quantity for item in obj.orderitem_set.all())
        return f"{total:.2f} грн"

    total_amount.short_description = "Сума"

    def iban_invoice_status(self, obj):
        if obj.payment_type != "iban":
            return "—"
        if obj.iban_invoice_generated:
            return "Рахунок згенеровано"
        if obj.iban_invoice_requested:
            return "Очікує генерації"
        return "Не запитано"

    iban_invoice_status.short_description = "Статус рахунку IBAN"

    def generate_iban_invoice_action(self, request, queryset):
        from checkout.invoice import generate_and_upload_invoice
        generated = 0
        for order in queryset:
            if order.payment_type != "iban" or not order.iban_invoice_requested:
                continue
            try:
                pdf_path, pdf_url = generate_and_upload_invoice(order)
                order.mark_invoice_generated(pdf_path, pdf_url)
                order.iban_invoice_generated = True
                order.save(update_fields=["iban_invoice_generated"])
                generated += 1
            except Exception as exc:
                self.message_user(request, f"Не вдалося згенерувати рахунок для замовлення #{order.id}: {exc}", level=messages.ERROR)
        if generated:
            self.message_user(request, f"Рахунок згенеровано для {generated} замовлень.")

    generate_iban_invoice_action.short_description = "Згенерувати рахунок IBAN"


@admin.register(OrderItem)
class OrderItemAdmin(ResilientModelAdmin):
    list_display = [
        "order",
        "furniture",
        "quantity",
        "price_display",
        "is_promotional",
        "size_variant_column",
        "fabric_column",
        "custom_option_column",
        "total_price_column",
        "savings_amount",
    ]
    list_filter = ["is_promotional", "size_variant_is_promotional", "order__created_at"]
    search_fields = ["order__customer_name", "furniture__name"]
    readonly_fields = [
        "price",
        "original_price",
        "is_promotional",
        "price_display",
        "savings_amount",
        "size_variant_id",
        "size_variant_original_price",
        "size_variant_is_promotional",
        "fabric_category_id",
        "variant_image_id",
        "custom_option",
        "custom_option_name",
        "custom_option_value",
        "custom_option_price",
    ]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order', 'furniture', 'quantity')
        }),
        ('Pricing Information', {
            'fields': ('price', 'original_price', 'is_promotional', 'price_display', 'savings_amount')
        }),
        ('Size Variant Information', {
            'fields': ('size_variant_id', 'size_variant_original_price', 'size_variant_is_promotional')
        }),
        (
            'Additional Information',
            {
                'fields': (
                    'fabric_category_id',
                    'variant_image_id',
                    'custom_option_name',
                    'custom_option_value',
                    'custom_option_price',
                    'custom_option',
                )
            },
        ),
    )

    def size_variant_column(self, obj):
        return obj.size_variant_display or "—"

    size_variant_column.short_description = "Розмір"

    def fabric_column(self, obj):
        return obj.fabric_category_display or "—"

    fabric_column.short_description = "Тканина"

    def custom_option_column(self, obj):
        if obj.custom_option_value:
            label = obj.custom_option_name or "Опція"
            price_part = ""
            if obj.custom_option_price:
                try:
                    price_part = f" (+{float(obj.custom_option_price):g} грн)"
                except (TypeError, ValueError):
                    price_part = ""
            return f"{label}: {obj.custom_option_value}{price_part}"
        return "—"

    custom_option_column.short_description = "Додатковий параметр"

    def total_price_column(self, obj):
        return f"{obj.price * obj.quantity:.2f} грн" if obj.price is not None else "—"

    total_price_column.short_description = "Сума"


@admin.register(LiqPayReceipt)
class LiqPayReceiptAdmin(ResilientModelAdmin):
    list_display = ["order", "payment_id", "status", "amount", "currency", "created_at"]
    search_fields = ["order__id", "order__customer_name", "order__customer_phone_number", "payment_id"]
    list_filter = ["status", "currency", "created_at"]
    readonly_fields = [
        "order",
        "payment_id",
        "status",
        "amount",
        "currency",
        "receipt_url",
        "items_snapshot",
        "raw_response",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        ("Загальна інформація", {"fields": ("order", "payment_id", "status", "amount", "currency", "receipt_url")}),
        ("Деталі чека", {"fields": ("items_snapshot", "raw_response")}),
        ("Службова інформація", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(FurnitureSizeVariant)
class FurnitureSizeVariantAdmin(ResilientModelAdmin):
    """Admin configuration for FurnitureSizeVariant model."""
    list_display = [
        'furniture', 'dimensions', 'price', 'is_promotional', 'promotional_price', 'sale_end_date', 'current_price', 'discount_percentage', 'is_on_sale', 'is_foldable'
    ]
    list_filter = ['furniture__sub_category', 'is_foldable', 'furniture__is_promotional', 'is_promotional']
    search_fields = ['furniture__name']
    ordering = ['furniture__name', 'height', 'width', 'length']
    actions = ['set_promotional_price', 'clear_promotional_price', 'apply_parent_promotion', 'make_promotional', 'remove_promotional', 'set_sale_end_date', 'clear_sale_end_date']
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('furniture', 'height', 'width', 'length', 'is_foldable', 'unfolded_length')
        }),
        ('Ціни та акції', {
            'fields': ('price', 'is_promotional', 'promotional_price', 'sale_end_date'),
            'description': 'Встановіть акційну ціну для цього розміру. Залиште порожнім для використання основної акційної ціни меблів.'
        }),
        ('Інформація про ціни', {
            'fields': ('current_price_display', 'discount_display'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['current_price_display', 'discount_display']
    
    def current_price(self, obj):
        """Display current price with styling."""
        try:
            if obj.is_on_sale:
                return format_html(
                    '<span style="color: #dc3545; font-weight: bold;">{} грн</span>',
                    obj.current_price
                )
            return format_html('{} грн', obj.current_price)
        except:
            return '-'
    current_price.short_description = "Поточна ціна"
    
    def discount_percentage(self, obj):
        """Display discount percentage."""
        try:
            if obj.discount_percentage > 0:
                return format_html(
                    '<span style="color: #dc3545; font-weight: bold;">-{}%</span>',
                    obj.discount_percentage
                )
            return '-'
        except:
            return '-'
    discount_percentage.short_description = "Знижка"
    
    def is_on_sale(self, obj):
        """Display sale status."""
        try:
            if obj.is_on_sale:
                return format_html('<span style="color: #28a745;">✓ Акція</span>')
            return format_html('<span style="color: #666;">-</span>')
        except:
            return format_html('<span style="color: #666;">-</span>')
    is_on_sale.short_description = "Акція"
    
    def current_price_display(self, obj):
        """Display current price for readonly field."""
        try:
            return f"{obj.current_price} грн"
        except:
            return "Помилка"
    current_price_display.short_description = "Поточна ціна"
    
    def discount_display(self, obj):
        """Display discount for readonly field."""
        try:
            if obj.discount_percentage > 0:
                return f"-{obj.discount_percentage}%"
            return "Немає знижки"
        except:
            return "Помилка"
    discount_display.short_description = "Знижка"
    
    # Admin actions
    def set_promotional_price(self, request, queryset):
        """Set promotional price for selected size variants."""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        # Store selected IDs in session for the next step
        request.session['size_variant_ids'] = list(queryset.values_list('id', flat=True))
        return HttpResponseRedirect(reverse('admin:size_variant_promotional_price_form'))
    set_promotional_price.short_description = "Встановити акційну ціну"
    
    def clear_promotional_price(self, request, queryset):
        """Clear promotional price for selected size variants."""
        updated = queryset.update(promotional_price=None)
        self.message_user(request, f"Акційну ціну очищено для {updated} розмірних варіантів.")
    clear_promotional_price.short_description = "Очистити акційну ціну"
    
    def apply_parent_promotion(self, request, queryset):
        """Apply parent furniture promotional price to size variants."""
        updated = 0
        for variant in queryset:
            if variant.furniture.is_promotional and variant.furniture.promotional_price:
                variant.promotional_price = variant.furniture.promotional_price
                variant.save()
                updated += 1
        self.message_user(request, f"Акційну ціну батьківських меблів застосовано до {updated} розмірних варіантів.")
    apply_parent_promotion.short_description = "Застосувати акцію батьківських меблів"
    
    def make_promotional(self, request, queryset):
        """Make selected size variants promotional."""
        updated = queryset.update(is_promotional=True)
        self.message_user(request, f"{updated} розмірних варіантів зроблено акційними.")
    make_promotional.short_description = "Зробити акційними"
    
    def remove_promotional(self, request, queryset):
        """Remove promotional status from selected size variants."""
        updated = queryset.update(is_promotional=False, promotional_price=None, sale_end_date=None)
        self.message_user(request, f"Акційний статус видалено з {updated} розмірних варіантів.")
    remove_promotional.short_description = "Видалити акційний статус"
    
    def set_sale_end_date(self, request, queryset):
        """Set sale end date for selected size variants."""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        # Store selected IDs in session for the next step
        request.session['size_variant_sale_items_ids'] = list(queryset.values_list('id', flat=True))
        return HttpResponseRedirect(reverse('admin:size_variant_sale_end_date_form'))
    set_sale_end_date.short_description = "Встановити дату закінчення акції"
    
    def clear_sale_end_date(self, request, queryset):
        """Clear sale end date for selected size variants."""
        updated = queryset.update(sale_end_date=None)
        self.message_user(request, f"Дату закінчення акції очищено для {updated} розмірних варіантів.")
    clear_sale_end_date.short_description = "Очистити дату закінчення акції"
