from django.db import models
from django.db.models import JSONField
from typing import Any

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True, verbose_name="Зображення")

    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"

    def __str__(self) -> str:
        return self.name

class Furniture(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="furniture")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_promotional = models.BooleanField(default=False, verbose_name="Акційний")
    promotional_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                            verbose_name="Акційна ціна")
    description = models.TextField()
    image = models.ImageField(upload_to='furniture/', null=True, blank=True)
    parameters = JSONField(default=dict, blank=True)  # Гнучкі параметри для розширення

    class Meta:
        verbose_name = "Меблі"
        verbose_name_plural = "Меблі"

    def __str__(self) -> str:
        return self.name

class Order(models.Model):
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    items = models.ManyToManyField(Furniture, through='OrderItem')

    class Meta:
        verbose_name = "Замовлення"
        verbose_name_plural = "Замовлення"

    def __str__(self) -> str:
        return f"Order {self.id} by {self.customer_name}"

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