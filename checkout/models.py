import logging
from functools import cached_property

from django.core.files.storage import default_storage
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from fabric_category.models import FabricCategory
from furniture.models import Furniture, FurnitureSizeVariant, FurnitureVariantImage


class OrderStatus(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва статусу")
    slug = models.SlugField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name="Системна назва",
        help_text="Використовується у внутрішніх інтеграціях",
    )
    salesdrive_status_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        unique=True,
        verbose_name="ID статусу в SalesDrive",
        help_text="Опціонально. Використовується для синхронізації вебхуком",
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name="Статус за замовчуванням",
        help_text="Присвоюється новим замовленням, якщо не вибрано інше значення.",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активний")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Порядок сортування")

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "Статус замовлення"
        verbose_name_plural = "Статуси замовлень"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        if self.is_default:
            type(self).objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)

    @classmethod
    def get_default(cls) -> "OrderStatus | None":
        default_status = cls.objects.filter(is_default=True).first()
        if default_status:
            return default_status
        return cls.objects.order_by("sort_order", "id").first()


class Order(models.Model):
    DELIVERY_CHOICES = [
        ("local", "Доставка по місту"),
        ("nova_poshta", "Нова Пошта"),
    ]

    PAYMENT_CHOICES = [
        ("iban", "IBAN"),
    ]

    customer_name = models.CharField(max_length=200)
    customer_last_name = models.CharField(max_length=200)
    customer_phone_number = models.CharField(
        max_length=10,
        verbose_name="Номер телефону",
    )
    customer_email = models.EmailField(blank=True)

    # Delivery fields
    delivery_type = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        verbose_name="Тип доставки",
    )
    delivery_city = models.CharField(max_length=100, verbose_name="Місто доставки")
    delivery_branch = models.CharField(
        max_length=200,
        verbose_name="Відділення Нової Пошти",
        blank=True,
    )
    delivery_address = models.TextField(
        verbose_name="Адреса доставки",
        blank=True,
    )

    # Payment fields
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        verbose_name="Тип оплати",
    )

    status = models.ForeignKey(
        OrderStatus,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Статус замовлення",
    )

    is_confirmed = models.BooleanField(
        default=False,
        verbose_name="Підтверджено",
        help_text="Після підтвердження автоматично генерується рахунок-фактура.",
    )
    invoice_pdf_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Посилання на рахунок",
    )
    invoice_pdf_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Шлях до файлу рахунку",
    )
    invoice_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата генерації рахунку",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    items = models.ManyToManyField(Furniture, through="OrderItem")

    _logger = logging.getLogger(__name__)

    class Meta:
        verbose_name = "Замовлення"
        verbose_name_plural = "Замовлення"

    def __str__(self) -> str:
        return f"Order {self.id} by {self.customer_name} {self.customer_last_name}"

    @property
    def total_savings(self):
        """Calculate total savings for the entire order."""
        return sum(item.savings_amount for item in self.orderitem_set.all())

    @property
    def total_original_amount(self):
        """Calculate total original amount before any discounts."""
        total = 0
        for item in self.orderitem_set.all():
            if item.is_promotional and item.original_price:
                total += item.original_price * item.quantity
            elif item.size_variant_is_promotional and item.size_variant_original_price:
                total += item.size_variant_original_price * item.quantity
            else:
                total += item.price * item.quantity
        return total

    @property
    def customer_full_name(self) -> str:
        """Convenience accessor for displaying the full customer name."""
        return f"{self.customer_name} {self.customer_last_name}".strip()

    @property
    def total_amount(self):
        """Total payable amount for the order."""
        return sum(item.price * item.quantity for item in self.orderitem_set.all())

    def mark_invoice_generated(self, pdf_path: str, pdf_url: str) -> None:
        """Persist invoice metadata after successful generation."""
        generated_at = timezone.now()
        self.invoice_pdf_path = pdf_path
        self.invoice_pdf_url = pdf_url
        self.invoice_generated_at = generated_at
        type(self).objects.filter(pk=self.pk).update(
            invoice_pdf_path=pdf_path,
            invoice_pdf_url=pdf_url,
            invoice_generated_at=generated_at,
        )

    def save(self, *args, **kwargs):
        if not self.status_id:
            default_status = OrderStatus.get_default()
            if default_status:
                self.status = default_status

        old_invoice_path = None
        clear_invoice = False

        if self.pk:
            previous = (
                type(self)
                .objects.filter(pk=self.pk)
                .only(
                    "is_confirmed",
                    "invoice_pdf_path",
                    "invoice_pdf_url",
                    "invoice_generated_at",
                )
                .first()
            )
            if previous and previous.is_confirmed and not self.is_confirmed:
                clear_invoice = True
                old_invoice_path = previous.invoice_pdf_path

        if clear_invoice:
            self.invoice_pdf_url = ""
            self.invoice_pdf_path = ""
            self.invoice_generated_at = None

        super().save(*args, **kwargs)

        if clear_invoice and old_invoice_path:
            try:
                default_storage.delete(old_invoice_path)
            except Exception:  # pragma: no cover - best effort cleanup
                self._logger.exception(
                    "Unable to delete old invoice file %s", old_invoice_path
                )


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    furniture = models.ForeignKey(Furniture, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна")
    
    # Promotional pricing information
    original_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Оригінальна ціна"
    )
    is_promotional = models.BooleanField(
        default=False, 
        verbose_name="Акційний товар"
    )
    
    # Size variant and fabric information
    size_variant_id = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="ID розмірного варіанту"
    )
    size_variant_original_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Оригінальна ціна розмірного варіанту"
    )
    size_variant_is_promotional = models.BooleanField(
        default=False, 
        verbose_name="Акційний розмірний варіант"
    )
    fabric_category_id = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="ID категорії тканини"
    )
    variant_image_id = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="ID варіанту зображення"
    )
    custom_option = models.ForeignKey(
        "furniture.FurnitureCustomOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
        verbose_name="Обраний варіант параметра",
    )
    custom_option_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Назва додаткового параметра",
    )
    custom_option_value = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Значення додаткового параметра",
    )
    custom_option_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Надбавка за параметр",
    )

    class Meta:
        verbose_name = "Елемент замовлення"
        verbose_name_plural = "Елементи замовлення"

    def __str__(self) -> str:
        return f"{self.furniture.name} ({self.quantity})"
    
    @property
    def price_display(self):
        """Display price with promotional information."""
        if self.is_promotional and self.original_price:
            return f"{self.price} грн (знижка з {self.original_price} грн)"
        return f"{self.price} грн"
    
    @property
    def size_variant_price_display(self):
        """Display size variant price with promotional information."""
        if self.size_variant_is_promotional and self.size_variant_original_price:
            return f"{self.price} грн (знижка з {self.size_variant_original_price} грн)"
        return f"{self.price} грн"
    
    @property
    def savings_amount(self):
        """Calculate total savings for this item."""
        savings = 0
        if self.is_promotional and self.original_price:
            savings += (self.original_price - self.price) * self.quantity
        if self.size_variant_is_promotional and self.size_variant_original_price:
            savings += (self.size_variant_original_price - self.price) * self.quantity
        return savings

    @cached_property
    def size_variant_obj(self):
        """Return the related size variant object if the ID is set."""
        if not self.size_variant_id:
            return None
        try:
            return FurnitureSizeVariant.objects.select_related("parameter").get(pk=self.size_variant_id)
        except FurnitureSizeVariant.DoesNotExist:
            return None

    @cached_property
    def fabric_category_obj(self):
        """Return the related fabric category object if the ID is set."""
        if not self.fabric_category_id:
            return None
        try:
            return FabricCategory.objects.get(pk=self.fabric_category_id)
        except FabricCategory.DoesNotExist:
            return None

    @cached_property
    def variant_image_obj(self):
        """Return the related variant image object if the ID is set."""
        if not self.variant_image_id:
            return None
        try:
            return FurnitureVariantImage.objects.get(pk=self.variant_image_id)
        except FurnitureVariantImage.DoesNotExist:
            return None

    @property
    def size_variant_display(self) -> str:
        """Human-readable representation of the selected size variant."""
        variant = self.size_variant_obj
        if not variant:
            return ""
        if variant.parameter and variant.parameter_value:
            label = variant.parameter.label or variant.parameter.key
            return f"{label}: {variant.parameter_value}"
        return variant.dimensions

    @property
    def fabric_category_display(self) -> str:
        """Human-readable representation of the selected fabric category."""
        category = self.fabric_category_obj
        if not category:
            return ""
        brand = category.brand.name if category.brand_id and category.brand else ""
        if brand:
            return f"{brand} — {category.name}"
        return category.name

    @property
    def variant_image_display(self) -> str:
        """Human-readable representation of the selected variant image."""
        variant_image = self.variant_image_obj
        if not variant_image:
            return ""
        return variant_image.name
