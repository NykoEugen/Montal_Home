from django.db import models

from furniture.models import Furniture


class Order(models.Model):
    customer_name = models.CharField(max_length=200)
    customer_last_name = models.CharField(max_length=200)

    customer_phone_number = models.CharField(
        max_length=10,
        verbose_name="Номер телефону",
    )
    customer_email = models.EmailField(blank=True)
    delivery_city = models.CharField(max_length=100, verbose_name="Місто доставки")
    delivery_branch = models.CharField(
        max_length=200, verbose_name="Відділення Нової Пошти"
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

    class Meta:
        verbose_name = "Елемент замовлення"
        verbose_name_plural = "Елементи замовлення"

    def __str__(self) -> str:
        return f"{self.furniture.name} ({self.quantity})"
