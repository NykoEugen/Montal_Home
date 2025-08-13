from django.db import models
from django.conf import settings
from checkout.models import Order


class Payment(models.Model):
    """Model to track Liqpay payment status and details."""
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Очікує оплати'),
        ('success', 'Успішно оплачено'),
        ('failed', 'Помилка оплати'),
        ('cancelled', 'Скасовано'),
    ]
    
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='payments',
        verbose_name="Замовлення"
    )
    
    # Liqpay specific fields
    liqpay_order_id = models.CharField(
        max_length=255, 
        unique=True,
        verbose_name="ID замовлення Liqpay"
    )
    liqpay_payment_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="ID платежу Liqpay"
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Сума платежу"
    )
    currency = models.CharField(
        max_length=3, 
        default='UAH',
        verbose_name="Валюта"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name="Статус платежу"
    )
    
    # Additional data
    description = models.TextField(
        blank=True,
        verbose_name="Опис платежу"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Оновлено")
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name="Оплачено")
    
    # Liqpay response data
    liqpay_response = models.JSONField(
        blank=True, 
        null=True,
        verbose_name="Відповідь від Liqpay"
    )
    
    class Meta:
        verbose_name = "Платіж"
        verbose_name_plural = "Платежі"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Платіж {self.liqpay_order_id} - {self.get_status_display()}"
    
    @property
    def is_paid(self):
        """Check if payment is successfully paid."""
        return self.status == 'success'
    
    @property
    def is_pending(self):
        """Check if payment is pending."""
        return self.status == 'pending'
    
    @property
    def is_failed(self):
        """Check if payment failed."""
        return self.status in ['failed', 'cancelled']
