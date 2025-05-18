from django.db import models
from django.db.models import JSONField

from sub_categories.models import SubCategory


class Furniture(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    sub_category = models.ForeignKey(
        SubCategory, on_delete=models.CASCADE, related_name="furniture"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_promotional = models.BooleanField(default=False, verbose_name="Акційний")
    promotional_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Акційна ціна",
    )
    description = models.TextField()
    image = models.ImageField(upload_to="furniture/", null=True, blank=True)
    parameters = JSONField(default=dict, blank=True)  # Гнучкі параметри для розширення

    class Meta:
        db_table = "furniture"
        verbose_name = "Меблі"
        verbose_name_plural = "Меблі"

    def __str__(self) -> str:
        return self.name
