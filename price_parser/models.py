from django.db import models
from django.utils import timezone
from furniture.models import Furniture, FurnitureSizeVariant


class GoogleSheetConfig(models.Model):
    """Configuration for Google Sheets to parse prices from."""
    
    name = models.CharField(
        max_length=200,
        verbose_name="Назва конфігурації",
        help_text="Назва для ідентифікації цієї конфігурації"
    )
    sheet_url = models.URLField(
        verbose_name="URL Google таблиці",
        help_text="Посилання на Google таблицю"
    )
    sheet_id = models.CharField(
        max_length=100,
        verbose_name="ID таблиці",
        help_text="ID Google таблиці (автоматично витягується з URL)"
    )
    
    sheet_name = models.CharField(
        max_length=100,
        default='Sheet1',
        verbose_name="Назва сторінки",
        help_text="Назва сторінки/вкладки в Google таблиці (наприклад: 'Sheet1', 'Прайс', 'Ціни')"
    )
    
    sheet_gid = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="GID сторінки",
        help_text="GID сторінки (знаходиться в URL після #gid=). Якщо не вказано, буде використовуватися перша сторінка (gid=0)"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна",
        help_text="Чи використовувати цю конфігурацію"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата створення"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата оновлення"
    )
    
    class Meta:
        db_table = "price_parser_google_sheet_config"
        verbose_name = "Конфігурація Google таблиці"
        verbose_name_plural = "Конфігурації Google таблиць"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Extract sheet ID from URL if not provided."""
        if not self.sheet_id and self.sheet_url:
            import re
            match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', self.sheet_url)
            if match:
                self.sheet_id = match.group(1)
        super().save(*args, **kwargs)


class PriceUpdateLog(models.Model):
    """Log of price updates from Google Sheets."""
    
    STATUS_CHOICES = [
        ('success', 'Успішно'),
        ('error', 'Помилка'),
        ('partial', 'Частково'),
    ]
    
    config = models.ForeignKey(
        GoogleSheetConfig,
        on_delete=models.CASCADE,
        related_name='update_logs',
        verbose_name="Конфігурація"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name="Статус"
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Час початку"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Час завершення"
    )
    items_processed = models.PositiveIntegerField(
        default=0,
        verbose_name="Оброблено товарів"
    )
    items_updated = models.PositiveIntegerField(
        default=0,
        verbose_name="Оновлено товарів"
    )
    errors = models.JSONField(
        default=list,
        verbose_name="Помилки",
        help_text="Список помилок під час оновлення"
    )
    log_details = models.TextField(
        blank=True,
        verbose_name="Деталі логу"
    )
    
    class Meta:
        db_table = "price_parser_update_log"
        verbose_name = "Лог оновлення цін"
        verbose_name_plural = "Логи оновлення цін"
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.config.name} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"





class FurniturePriceCellMapping(models.Model):
    """Direct mapping between furniture and specific price cells in Google Sheets."""
    
    furniture = models.ForeignKey(
        Furniture,
        on_delete=models.CASCADE,
        related_name='price_cell_mappings',
        verbose_name="Меблі"
    )
    config = models.ForeignKey(
        GoogleSheetConfig,
        on_delete=models.CASCADE,
        related_name='price_cell_mappings',
        verbose_name="Конфігурація Google таблиці"
    )
    sheet_row = models.PositiveIntegerField(
        verbose_name="Рядок в таблиці",
        help_text="Номер рядка в Google таблиці (наприклад: 5)"
    )
    sheet_column = models.CharField(
        max_length=10,
        verbose_name="Колонка в таблиці",
        help_text="Колонка в Google таблиці (наприклад: E, F, G)"
    )
    price_type = models.CharField(
        max_length=100,
        verbose_name="Тип ціни",
        help_text="Опис типу ціни (наприклад: 'Стільниця стандарт', 'HPL покриття')"
    )
    size_variant = models.ForeignKey(
        'furniture.FurnitureSizeVariant',
        on_delete=models.CASCADE,
        related_name='price_cell_mappings',
        verbose_name="Розмірний варіант",
        null=True,
        blank=True,
        help_text="Розмірний варіант для цієї ціни (опціонально)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активне"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата створення"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата оновлення"
    )
    
    class Meta:
        db_table = "price_parser_furniture_price_cell_mapping"
        verbose_name = "Зв'язок меблів з коміркою ціни"
        verbose_name_plural = "Зв'язки меблів з комірками цін"
        unique_together = ['furniture', 'config', 'sheet_row', 'sheet_column']
        ordering = ['furniture__name', 'sheet_row', 'sheet_column']
    
    def __str__(self):
        return f"{self.furniture.name} - Рядок {self.sheet_row}, Колонка {self.sheet_column} ({self.price_type})"
    
    @property
    def cell_reference(self):
        """Get Excel-style cell reference."""
        return f"{self.sheet_column}{self.sheet_row}" 