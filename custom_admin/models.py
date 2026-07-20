from django.conf import settings
from django.db import models


class CatalogUpdateJob(models.Model):
    SUPPLIER_CHOICES = [
        ("evrodim", "Evrodim"),
        ("andersen", "Andersen"),
        ("kreslalux", "Kreslalux"),
        ("eurosof", "Eurosof"),
    ]
    ACTION_CHOICES = [
        ("import", "Імпорт нових товарів"),
        ("update_prices", "Оновлення цін"),
        ("update_params", "Оновлення характеристик"),
    ]
    STATUS_CHOICES = [
        ("running", "Виконується"),
        ("success", "Успішно"),
        ("error", "Помилка"),
    ]

    supplier = models.CharField(max_length=20, choices=SUPPLIER_CHOICES)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    catalog_key = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="running")
    detail = models.TextField(blank=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_supplier_display()} · {self.get_action_display()} · {self.status}"
