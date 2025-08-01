from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from fabric_category.models import FabricBrand, FabricCategory
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
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата оновлення")
    selected_fabric_brand = models.ForeignKey(
        FabricBrand,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="furnitures",
        verbose_name="Обраний бренд тканини"
    )
    fabric_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        validators=[MinValueValidator(0)],
        verbose_name="Коефіцієнт тканини",
        help_text="Множник для розрахунку вартості тканини"
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
        if self.is_promotional and self.promotional_price and float(self.price) > 0:
            return int(
                (
                    (float(self.price) - float(self.promotional_price))
                    / float(self.price)
                )
                * 100
            )
        return 0

    def get_parameters(self):
        """Get all parameters for this furniture item."""
        return self.parameters.select_related("parameter").all()

    def get_size_variants(self):
        """Get all size variants for this furniture item."""
        return self.size_variants.all()

    def get_available_sizes(self):
        """Get formatted list of available sizes."""
        variants = self.get_size_variants()
        if not variants:
            return "Розміри не вказані"
        return ", ".join([variant.dimensions for variant in variants])

    def get_price_range(self):
        """Get price range from size variants."""
        variants = self.get_size_variants()
        if not variants:
            return self.current_price, self.current_price
        
        prices = [float(variant.price) for variant in variants]
        return min(prices), max(prices)


class FurnitureSizeVariant(models.Model):
    """Size variant model for furniture items."""
    
    furniture = models.ForeignKey(
        Furniture,
        on_delete=models.CASCADE,
        related_name="size_variants",
        verbose_name="Меблі"
    )
    height = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Висота (см)",
        help_text="Висота меблів у сантиметрах"
    )
    width = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Ширина (см)",
        help_text="Ширина меблів у сантиметрах"
    )
    length = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Довжина (см)",
        help_text="Довжина меблів у сантиметрах"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Ціна",
        help_text="Ціна для цього розміру"
    )

    class Meta:
        db_table = "furniture_size_variants"
        verbose_name = "Розмірний варіант меблів"
        verbose_name_plural = "Розмірні варіанти меблів"
        ordering = ["height", "width", "length"]

    def __str__(self) -> str:
        return f"{self.furniture.name} - {self.height}×{self.width}×{self.length}см"

    @property
    def dimensions(self) -> str:
        """Get formatted dimensions string."""
        return f"{self.height}×{self.width}×{self.length}см"
