from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils import timezone

from sub_categories.models import SubCategory


class Furniture(models.Model):
    """Furniture model representing items in the store."""

    name = models.CharField(
        max_length=200, verbose_name="Назва", help_text="Назва меблів"
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        blank=True,
        verbose_name="URL",
        help_text="Автоматично генерується з назви",
    )
    sub_category = models.ForeignKey(
        SubCategory,
        on_delete=models.CASCADE,
        related_name="furniture",
        verbose_name="Підкатегорія",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Ціна",
    )
    is_promotional = models.BooleanField(default=False, verbose_name="Акційний")
    promotional_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Акційна ціна",
        help_text="Ціна зі знижкою",
    )
    description = models.TextField(
        verbose_name="Опис", help_text="Детальний опис меблів"
    )
    image = models.ImageField(
        upload_to="furniture/", null=True, blank=True, verbose_name="Зображення"
    )
    created_at = models.DateTimeField(
        verbose_name="Дата створення",
        default=timezone.now
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="Дата оновлення"
    )

    class Meta:
        db_table = "furniture"
        verbose_name = "Меблі"
        verbose_name_plural = "Меблі"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def current_price(self) -> float:
        """Get the current price (promotional if available, otherwise regular)."""
        if self.is_promotional and self.promotional_price:
            return float(self.promotional_price)
        return float(self.price)

    @property
    def discount_percentage(self) -> int:
        """Calculate discount percentage if promotional."""
        if self.is_promotional and self.promotional_price and self.price > 0:
            return int(((self.price - self.promotional_price) / self.price) * 100)
        return 0

    def get_parameters(self):
        """Get all parameters for this furniture item."""
        return self.parameters.select_related("parameter").all()
