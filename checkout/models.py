from django.db import models

from furniture.models import Furniture


class Order(models.Model):
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

    created_at = models.DateTimeField(auto_now_add=True)
    items = models.ManyToManyField(Furniture, through="OrderItem")

    class Meta:
        verbose_name = "Замовлення"
        verbose_name_plural = "Замовлення"

    def __str__(self) -> str:
        return f"Order {self.id} by {self.customer_name} {self.customer_last_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    furniture = models.ForeignKey(Furniture, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна")
    
    # Size variant and fabric information
    size_variant_id = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="ID розмірного варіанту"
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

    class Meta:
        verbose_name = "Елемент замовлення"
        verbose_name_plural = "Елементи замовлення"

    def __str__(self) -> str:
        return f"{self.furniture.name} ({self.quantity})"
