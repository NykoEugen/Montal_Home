from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from fabric_category.models import FabricBrand, FabricCategory
from params.models import Parameter
from sub_categories.models import SubCategory


class Furniture(models.Model):
    """Furniture model representing items in the store."""
    
    STOCK_STATUS_CHOICES = [
        ('in_stock', 'На складі'),
        ('on_order', 'Під замовлення'),
    ]

    name = models.CharField(
        max_length=200, verbose_name="Назва", help_text="Назва меблів"
    )
    article_code = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Код товару", 
        help_text="Унікальний код товару"
    )
    stock_status = models.CharField(
        max_length=20,
        choices=STOCK_STATUS_CHOICES,
        default='in_stock',
        verbose_name="Статус наявності",
        help_text="Чи є товар на складі або під замовлення"
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
    sale_end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата закінчення акції",
        help_text="Коли закінчується акційна пропозиція"
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
    custom_option_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Назва додаткового параметра",
        help_text="Назва параметра для власних варіантів вибору (наприклад, 'Комплектація')."
    )

    @property
    def discount_percentage(self):
        """Calculate discount percentage for promotional items."""
        if self.is_promotional and self.promotional_price and self.price:
            discount = ((self.price - self.promotional_price) / self.price) * 100
            return int(discount)
        return 0

    def get_custom_option_values(self):
        """Return list of active custom option values ordered by position."""
        return list(
            self.custom_options.filter(is_active=True)
            .order_by("position", "id")
            .values_list("value", flat=True)
        )

    @property
    def current_price(self):
        """Get current price (promotional if available, otherwise regular)."""
        return self.promotional_price if self.is_promotional and self.promotional_price else self.price

    @property
    def is_sale_active(self):
        """Check if the sale is still active based on end date."""
        if not self.is_promotional or not self.promotional_price:
            return False
        if not self.sale_end_date:
            return True  # Permanent sale (no end date)
        return timezone.now() < self.sale_end_date

    @property
    def sale_end_date_iso(self):
        """Get sale end date in ISO format for JavaScript."""
        if self.sale_end_date:
            return self.sale_end_date.isoformat()
        return None

    class Meta:
        db_table = "furniture"
        verbose_name = "Меблі"
        verbose_name_plural = "Меблі"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['article_code']),
            models.Index(fields=['stock_status']),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        
        # Check if promotional status changed
        if self.pk:  # Only for existing objects
            try:
                old_instance = Furniture.objects.get(pk=self.pk)
                promotional_changed = old_instance.is_promotional != self.is_promotional
            except Furniture.DoesNotExist:
                promotional_changed = False
        else:
            promotional_changed = False
        
        super().save(*args, **kwargs)
        
        # If promotional status was disabled, clear size variant promotional prices
        if promotional_changed and not self.is_promotional:
            self.size_variants.filter(promotional_price__isnull=False).update(promotional_price=None)

    @property
    def current_price(self) -> float:
        """Get the current price (promotional if available, otherwise regular)."""
        if self.is_promotional and self.promotional_price:
            return float(self.promotional_price)
        return float(self.price)
    
    @property
    def best_promotional_price(self):
        """Get the best promotional price from furniture or size variants."""
        if self.is_promotional and self.promotional_price and self.is_sale_active:
            return self.promotional_price
        
        # Check if any size variants are promotional
        promotional_variants = self.size_variants.filter(
            is_promotional=True,
            promotional_price__isnull=False
        ).filter(
            models.Q(sale_end_date__isnull=True) | models.Q(sale_end_date__gt=timezone.now())
        )
        
        if promotional_variants.exists():
            # Return the lowest promotional price from size variants
            return min(variant.promotional_price for variant in promotional_variants)
        
        return None
    
    @property
    def best_original_price(self):
        """Get the original price for promotional display."""
        if self.is_promotional and self.promotional_price and self.is_sale_active:
            return self.price
        
        # Check if any size variants are promotional
        promotional_variants = self.size_variants.filter(
            is_promotional=True,
            promotional_price__isnull=False
        ).filter(
            models.Q(sale_end_date__isnull=True) | models.Q(sale_end_date__gt=timezone.now())
        )
        
        if promotional_variants.exists():
            # Return the highest original price from promotional size variants
            return max(variant.price for variant in promotional_variants)
        
        return self.price
    
    @property
    def best_discount_percentage(self):
        """Calculate discount percentage for best promotional price."""
        promotional_price = self.best_promotional_price
        original_price = self.best_original_price
        
        if promotional_price and original_price and promotional_price < original_price:
            discount = ((original_price - promotional_price) / original_price) * 100
            return int(discount)
        return 0

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
        return self.size_variants.select_related("parameter").all()

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


class FurnitureCustomOption(models.Model):
    """Custom selectable option for furniture."""

    furniture = models.ForeignKey(
        Furniture,
        on_delete=models.CASCADE,
        related_name="custom_options",
        verbose_name="Меблі",
    )
    value = models.CharField(
        max_length=200,
        verbose_name="Значення",
        help_text="Варіант вибору для додаткового параметра.",
    )
    position = models.PositiveIntegerField(
        default=0,
        verbose_name="Позиція",
        help_text="Порядок відображення варіантів.",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активний",
        help_text="Приховати варіант без видалення.",
    )

    class Meta:
        db_table = "furniture_custom_options"
        verbose_name = "Варіант додаткового параметра"
        verbose_name_plural = "Варіанти додаткового параметра"
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"{self.furniture.name}: {self.value}"


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
        decimal_places=0,
        validators=[MinValueValidator(0)],
        verbose_name="Висота (см)",
        help_text="Висота меблів у сантиметрах"
    )
    width = models.DecimalField(
        max_digits=6,
        decimal_places=0,
        validators=[MinValueValidator(0)],
        verbose_name="Ширина (см)",
        help_text="Ширина меблів у сантиметрах"
    )
    length = models.DecimalField(
        max_digits=6,
        decimal_places=0,
        validators=[MinValueValidator(0)],
        verbose_name="Довжина (см)",
        help_text="Довжина меблів у сантиметрах (складена)"
    )
    is_foldable = models.BooleanField(
        default=False,
        verbose_name="Складні меблі",
        help_text="Чи можуть меблі складатися"
    )
    unfolded_length = models.DecimalField(
        max_digits=6,
        decimal_places=0,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
        verbose_name="Довжина розгорнута (см)",
        help_text="Довжина меблів у розгорнутому стані"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Ціна",
        help_text="Ціна для цього розміру"
    )
    promotional_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Акційна ціна",
        help_text="Акційна ціна для цього розміру (залиште порожнім для використання основної акційної ціни)"
    )
    is_promotional = models.BooleanField(
        default=False,
        verbose_name="Акційний розмір",
        help_text="Чи є цей розмір акційним незалежно від основного товару"
    )
    sale_end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата закінчення акції розміру",
        help_text="Коли закінчується акційна пропозиція для цього розміру"
    )
    parameter = models.ForeignKey(
        Parameter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Параметр",
        help_text="Параметр підкатегорії, який змінюється для цього розміру",
        related_name="size_variants",
    )
    parameter_value = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Значення параметра",
        help_text="Відображатиметься замість основного значення параметра при виборі цього розміру",
    )

    class Meta:
        db_table = "furniture_size_variants"
        verbose_name = "Розмірний варіант меблів"
        verbose_name_plural = "Розмірні варіанти меблів"
        ordering = ["height", "width", "length"]

    def __str__(self) -> str:
        return f"{self.furniture.name} - {int(self.height)}x{int(self.width)}x{int(self.length)} см"

    def clean(self):
        """Validate foldable furniture requirements."""
        from django.core.exceptions import ValidationError
        if self.is_foldable and not self.unfolded_length:
            raise ValidationError({
                'unfolded_length': 'Для складних меблів потрібно вказати розгорнуту довжину.'
            })
        if self.is_foldable and self.unfolded_length and self.unfolded_length <= self.length:
            raise ValidationError({
                'unfolded_length': 'Розгорнута довжина повинна бути більшою за згорнуту довжину.'
            })

        if self.parameter:
            allowed_params = self.furniture.sub_category.allowed_params
            if not allowed_params.filter(pk=self.parameter.pk).exists():
                raise ValidationError({
                    'parameter': 'Цей параметр не дозволений для обраної підкатегорії.'
                })
            if not self.parameter_value:
                raise ValidationError({
                    'parameter_value': 'Для обраного параметра потрібно вказати значення.'
                })
        elif self.parameter_value:
            raise ValidationError({
                'parameter': 'Оберіть параметр або приберіть значення параметра.'
            })

    @property
    def dimensions(self) -> str:
        """Get formatted dimensions string."""
        if self.is_foldable and self.unfolded_length:
            return f"{int(self.height)}x{int(self.width)}x{int(self.length)}-{int(self.unfolded_length)} см"
        else:
            return f"{int(self.height)}x{int(self.width)}x{int(self.length)} см"

    @property
    def current_price(self):
        """Get current price (promotional if available, otherwise regular)."""
        if self.is_promotional and self.promotional_price and self.is_sale_active:
            return self.promotional_price
        elif (self.furniture.is_promotional and 
              self.furniture.promotional_price and 
              self.furniture.is_sale_active):
            return self.furniture.promotional_price
        return self.price or 0

    @property
    def discount_percentage(self):
        """Calculate discount percentage for this size variant."""
        if self.price and self.current_price and self.current_price < self.price:
            discount = ((self.price - self.current_price) / self.price) * 100
            return int(discount)
        return 0

    @property
    def is_on_sale(self):
        """Check if this size variant is on sale."""
        if self.price and self.current_price:
            return self.current_price < self.price
        return False
    
    @property
    def is_sale_active(self):
        """Check if the size variant sale is still active based on end date."""
        if not self.is_promotional or not self.promotional_price:
            return False
        if not self.sale_end_date:
            return True  # Permanent sale (no end date)
        return timezone.now() < self.sale_end_date


class FurnitureVariantImage(models.Model):
    """Variant images for furniture items with optional links."""
    
    furniture = models.ForeignKey(
        Furniture,
        on_delete=models.CASCADE,
        related_name="variant_images",
        verbose_name="Меблі"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Назва варіанту",
        help_text="Назва варіанту (наприклад: 'Білий', 'Дуб світлий')"
    )
    stock_status = models.CharField(
        max_length=20,
        choices=Furniture.STOCK_STATUS_CHOICES,
        default='in_stock',
        verbose_name="Статус наявності",
        help_text="Використовується для відображення статусу при виборі цього варіанту",
    )
    image = models.ImageField(
        upload_to="furniture/variants/",
        verbose_name="Зображення варіанту",
        help_text="Зображення меблів у цьому варіанті"
    )
    link = models.URLField(
        blank=True,
        verbose_name="Посилання",
        help_text="Посилання на варіант (опціонально)"
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name="Варіант за замовчуванням",
        help_text="Цей варіант буде показаний першим"
    )
    position = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок відображення"
    )

    class Meta:
        db_table = "furniture_variant_images"
        verbose_name = "Варіант зображення меблів"
        verbose_name_plural = "Варіанти зображень меблів"
        ordering = ["position", "name"]
        unique_together = ["furniture", "name"]

    def __str__(self) -> str:
        return f"{self.furniture.name} - {self.name}"

    def save(self, *args, **kwargs):
        """Ensure only one default variant per furniture."""
        if self.is_default:
            # Set all other variants for this furniture to non-default
            FurnitureVariantImage.objects.filter(
                furniture=self.furniture
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class FurnitureImage(models.Model):
    """Additional images for a furniture item."""
    furniture = models.ForeignKey(
        Furniture,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Меблі",
    )
    image = models.ImageField(
        upload_to="furniture/",
        verbose_name="Зображення",
    )
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Альтернативний текст",
    )
    position = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок відображення",
    )

    class Meta:
        db_table = "furniture_images"
        verbose_name = "Зображення меблів"
        verbose_name_plural = "Зображення меблів"
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"{self.furniture.name} — image #{self.id}"
