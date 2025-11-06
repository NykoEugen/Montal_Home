from django.db import models
from django.utils import timezone

from furniture.models import Furniture


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
