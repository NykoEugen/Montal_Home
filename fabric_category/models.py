from django.core.validators import RegexValidator
from django.db import models

from utils.media_paths import fabric_color_image_upload_to


class FabricBrand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class FabricCategory(models.Model):
    brand = models.ForeignKey(
        FabricBrand, on_delete=models.CASCADE, related_name="quality_categories"
    )
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("brand", "name")
        verbose_name = "Fabric Category"
        verbose_name_plural = "Fabric Categories"

    def __str__(self):
        return f"{self.brand.name} - {self.name} ({self.price} грн)"


class FabricColorPalette(models.Model):
    """Reusable palette describing a set of upholstery colors."""

    name = models.CharField(max_length=120, unique=True)
    brand = models.ForeignKey(
        FabricBrand,
        on_delete=models.SET_NULL,
        related_name="color_palettes",
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Палітра покриттів"
        verbose_name_plural = "Палітри покриттів"

    def __str__(self) -> str:
        return self.name


class FabricColor(models.Model):
    """Concrete color that belongs to a palette."""

    HEX_COLOR_VALIDATOR = RegexValidator(
        regex=r"^#[0-9A-Fa-f]{6}$",
        message="Вкажіть колір у форматі #RRGGBB.",
    )

    palette = models.ForeignKey(
        FabricColorPalette, on_delete=models.CASCADE, related_name="colors"
    )
    name = models.CharField(max_length=120)
    hex_code = models.CharField(
        max_length=7,
        validators=[HEX_COLOR_VALIDATOR],
        blank=True,
        help_text="Колір у форматі #RRGGBB",
    )
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(
        upload_to=fabric_color_image_upload_to,
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Зразок покриття",
        help_text="Зображення зразка тканини/покриття.",
    )

    class Meta:
        ordering = ("palette", "position", "id")
        unique_together = ("palette", "name")
        verbose_name = "Колір палітри"
        verbose_name_plural = "Кольори палітр"

    def __str__(self) -> str:
        return f"{self.palette.name}: {self.name}"
