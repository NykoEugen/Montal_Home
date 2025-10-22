from django.conf import settings
from django.db import models
from django.utils import timezone

from furniture.models import Furniture


class Order(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Обробляється"
        AWAITING_PAYMENT = "awaiting_payment", "Очікує оплату"
        CONFIRMED = "confirmed", "Підтверджено"
        SHIPPING = "shipping", "Доставка"
        COMPLETED = "completed", "Завершено"
        CANCELED = "canceled", "Скасовано"

    DELIVERY_CHOICES = [
        ("local", "Локальна доставка"),
        ("nova_poshta", "Нова Пошта"),
    ]

    PAYMENT_CHOICES = [
        ("iban", "IBAN"),
        ("liqupay", "LiquPay"),
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
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PROCESSING,
        verbose_name="Статус замовлення",
    )
    status_changed_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Дата оновлення статусу",
    )
    staff_note = models.TextField(
        blank=True,
        verbose_name="Нотатка менеджера",
        help_text="Внутрішні примітки щодо замовлення",
    )
    customer_message = models.TextField(
        blank=True,
        verbose_name="Повідомлення клієнту",
        help_text="Додається до листа при надсиланні реквізитів",
    )
    payment_instructions_file = models.FileField(
        upload_to="payments/instructions/",
        blank=True,
        null=True,
        verbose_name="Файл з реквізитами для оплати",
    )
    payment_link = models.URLField(
        blank=True,
        verbose_name="Посилання на оплату",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    items = models.ManyToManyField(Furniture, through="OrderItem")

    class Meta:
        verbose_name = "Замовлення"
        verbose_name_plural = "Замовлення"
        ordering = ["-created_at"]

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
    def total_amount(self):
        return sum(item.price * item.quantity for item in self.orderitem_set.all())

    def save(self, *args, **kwargs):
        if self.pk:
            previous_status = (
                Order.objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )
            if previous_status != self.status:
                self.status_changed_at = timezone.now()
        else:
            self.status_changed_at = timezone.now()
        super().save(*args, **kwargs)


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


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name="Замовлення",
    )
    status = models.CharField(
        max_length=30,
        choices=Order.Status.choices,
        verbose_name="Статус",
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Коментар менеджера",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Менеджер",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата зміни",
    )

    class Meta:
        verbose_name = "Історія статусу замовлення"
        verbose_name_plural = "Історії статусів замовлення"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.order_id} -> {self.get_status_display()}"
