from typing import Optional

from django.db import models
from django.utils import timezone
from categories.models import Category
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
        help_text="Посилання на Google таблицю (залиште порожнім для XLSX файлів)",
        blank=True,
        null=True
    )
    sheet_id = models.CharField(
        max_length=100,
        verbose_name="ID таблиці",
        help_text="ID Google таблиці (автоматично витягується з URL) або назва XLSX файлу",
        blank=True,
        null=True
    )
    xlsx_file = models.FileField(
        upload_to='price_sheets/',
        verbose_name="XLSX файл",
        help_text="Завантажте XLSX файл з цінами (альтернатива Google таблиці)",
        blank=True,
        null=True
    )
    
    price_multiplier = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=1.0,
        verbose_name="Множник ціни",
        help_text="Множник для конвертації цін (наприклад: 1.0 для UAH, 38.5 для USD->UAH)"
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

    PARSING_MODE_CELL_MAPPING = 'cell_mapping'
    PARSING_MODE_BLOCK_STRUCTURED = 'block_structured'
    PARSING_MODE_CHOICES = [
        (PARSING_MODE_CELL_MAPPING, 'За коміркою (рядок/колонка)'),
        (PARSING_MODE_BLOCK_STRUCTURED, 'Блочна структура (пошук моделі за назвою)'),
    ]
    parsing_mode = models.CharField(
        max_length=20,
        choices=PARSING_MODE_CHOICES,
        default=PARSING_MODE_CELL_MAPPING,
        verbose_name="Режим парсингу",
        help_text=(
            "«За коміркою» — фіксовані рядок/колонка (FurniturePriceCellMapping). "
            "«Блочна структура» — пошук моделі за текстовою назвою в таблиці "
            "(FurnitureModelPriceMapping), для прайсів на кшталт «Джем», де "
            "постачальник групує моделі блоками з локальними заголовками."
        )
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
        """Extract sheet ID from URL if not provided, or set filename for XLSX."""
        if not self.sheet_id:
            if self.sheet_url:
                # Extract sheet ID from Google Sheets URL
                import re
                match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', self.sheet_url)
                if match:
                    self.sheet_id = match.group(1)
            elif self.xlsx_file:
                # Set sheet_id to filename for XLSX files
                self.sheet_id = self.xlsx_file.name
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

    @property
    def duration_seconds(self) -> Optional[int]:
        if self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None






class SupplierFeedConfig(models.Model):
    """Configuration for supplier XML/YML feeds."""

    FETCH_MODE_URL = 'url'
    FETCH_MODE_MANUAL = 'manual'
    FETCH_MODE_CHOICES = [
        (FETCH_MODE_URL, 'Автоматично за посиланням'),
        (FETCH_MODE_MANUAL, 'Вручну (вставити текст фіда)'),
    ]

    name = models.CharField(
        max_length=200,
        verbose_name="Назва конфігурації",
        help_text="Назва для ідентифікації файлу постачальника"
    )
    feed_url = models.URLField(
        verbose_name="URL фіда",
        help_text="Посилання на XML/YML файл (наприклад, YML для Matrolux)"
    )
    fetch_mode = models.CharField(
        max_length=20,
        choices=FETCH_MODE_CHOICES,
        default=FETCH_MODE_URL,
        verbose_name="Спосіб отримання фіда",
        help_text=(
            "'Автоматично' — сервер сам завантажує фід за URL. "
            "'Вручну' — якщо постачальник блокує сервер (403), перейдіть за посиланням "
            "у браузері, скопіюйте вміст і вставте його в поле нижче."
        )
    )
    manual_feed_content = models.TextField(
        blank=True,
        default='',
        verbose_name="Вміст фіда (вручну)",
        help_text=(
            "Використовується лише при 'Вручну'. Покрокова інструкція: "
            "1) Перейдіть за посиланням з поля 'URL фіда' у новій вкладці. "
            "2) Виділіть увесь вміст сторінки (Ctrl+A/Cmd+A) і скопіюйте (Ctrl+C/Cmd+C). "
            "3) Вставте сюди (Ctrl+V/Cmd+V), повністю замінивши попередній текст. "
            "4) Збережіть конфігурацію. "
            "5) У списку 'Фіди постачальників' натисніть 'Тестувати парсер' або 'Оновити ціни'."
        )
    )
    supplier = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Постачальник",
        help_text="Назва виробника"
    )
    category_hint = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Категорія/нотатка",
        help_text="Опишіть, для яких товарів застосовується"
    )
    price_multiplier = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=1.0,
        verbose_name="Множник ціни",
        help_text="Наприклад, 1.0 для гривні або курс валюти"
    )
    article_tag_name = models.CharField(
        max_length=50,
        default='model',
        verbose_name="XML тег артикулу",
        help_text=(
            "Назва XML-тегу, з якого читати артикул товару. "
            "Для більшості фідів: 'model'. Для Vetro: 'article'. Для Matro: 'vendorCode'."
        )
    )
    article_prefix_parts = models.PositiveIntegerField(
        default=0,
        verbose_name="Кількість частин артикулу (prefix)",
        help_text=(
            "Кількість частин артикулу через '-' для зіставлення з базовим кодом товару. "
            "0 = використовувати повний артикул. "
            "Наприклад: для 'S-120-cappuccino-velvet' з значенням 2 отримаємо 'S-120'."
        )
    )
    update_size_variants = models.BooleanField(
        default=False,
        verbose_name="Оновлювати розміри товару",
        help_text=(
            "Якщо увімкнено, парсер оновлює ціни окремих розмірів (FurnitureSizeVariant), "
            "а не базову ціну товару. Потрібно вказати 'Назва XML-параметру розміру'."
        )
    )
    size_param_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Назва XML-параметру розміру",
        help_text=(
            "Атрибут name тегу <param>, який містить розмір у форматі 'ШхД' (напр. '70x190'). "
            "Для матраців Matro: 'Розмір матрацу (ШхД)'."
        )
    )
    match_by_article = models.BooleanField(
        default=True,
        verbose_name="Шукати за артикулом",
        help_text="Використовувати значення з вказаного XML-тегу артикулу"
    )
    match_by_name = models.BooleanField(
        default=True,
        verbose_name="Шукати за назвою",
        help_text="Використовувати значення <name>, якщо артикул не знайдено"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активний"
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
        db_table = "price_parser_supplier_feed_config"
        verbose_name = "XML фід постачальника"
        verbose_name_plural = "XML фіди постачальників"
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class SupplierFeedUpdateLog(models.Model):
    """Log of price updates executed against supplier feeds."""

    STATUS_CHOICES = [
        ('success', 'Успішно'),
        ('error', 'Помилка'),
        ('partial', 'Частково'),
    ]

    config = models.ForeignKey(
        SupplierFeedConfig,
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
    offers_processed = models.PositiveIntegerField(
        default=0,
        verbose_name="Оброблено оферів"
    )
    items_matched = models.PositiveIntegerField(
        default=0,
        verbose_name="Зіставлено товарів"
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
        db_table = "price_parser_supplier_feed_log"
        verbose_name = "Лог фіда постачальника"
        verbose_name_plural = "Логи фідів постачальників"
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.config.name} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def duration_seconds(self) -> Optional[int]:
        if self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None


class SupplierWebConfig(models.Model):
    """Configuration for scraping supplier prices from web pages."""

    name = models.CharField(
        max_length=200,
        verbose_name="Назва конфігурації",
        help_text="Назва для ідентифікації веб-парсера постачальника",
    )
    base_url = models.URLField(
        verbose_name="Базовий URL магазину",
        help_text="Головна сторінка сайту постачальника",
    )
    supplier = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Постачальник",
        help_text="Назва постачальника",
    )
    category_hint = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Категорія/нотатка",
        help_text="Пояснення для яких товарів застосовується",
    )
    target_categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="supplier_web_configs",
        verbose_name="Категорії товарів для оновлення",
        help_text="Якщо не вибрано жодної категорії, парсер оновлює всі товари.",
    )
    search_path_template = models.CharField(
        max_length=255,
        default="/?s={query}",
        verbose_name="Шаблон пошуку",
        help_text=(
            "Відносний шлях для пошуку (наприклад '/?s={query}' або '/search?q={query}'). "
            "Використовується як fallback, якщо через sitemap не знайдено збіг."
        ),
    )
    crawl_from_robots = models.BooleanField(
        default=True,
        verbose_name="Брати URL з robots/sitemap",
        help_text="Спробувати отримати перелік сторінок із robots.txt та sitemap.xml",
    )
    price_block_selector = models.CharField(
        max_length=255,
        blank=True,
        default="div.price.hp_price",
        verbose_name="CSS селектор блоку ціни",
        help_text=(
            "CSS-селектор контейнера, в якому шукати ціну (наприклад: 'div.price.hp_price'). "
            "Усередині блоку застосовується правило: del=базова, ins=акційна; якщо del немає — ins як базова."
        ),
    )
    max_urls_to_scan = models.PositiveIntegerField(
        default=500,
        verbose_name="Ліміт URL для аналізу",
        help_text="Максимальна кількість URL зі sitemap, які будуть використані для пошуку товарів.",
    )
    match_by_article = models.BooleanField(
        default=True,
        verbose_name="Шукати за артикулом",
        help_text="Спочатку шукати відповідність за article_code",
    )
    match_by_name = models.BooleanField(
        default=True,
        verbose_name="Шукати за назвою",
        help_text="Якщо артикул не знайдено, шукати за назвою товару",
    )
    request_timeout = models.PositiveIntegerField(
        default=20,
        verbose_name="Таймаут запиту (сек)",
    )
    use_selenium = models.BooleanField(
        default=False,
        verbose_name="Використовувати Selenium",
        help_text="Увімкніть, якщо ціна підвантажується JavaScript-ом і не видно в HTML відповіді.",
    )
    selenium_wait_seconds = models.PositiveIntegerField(
        default=4,
        verbose_name="Очікування Selenium (сек)",
    )
    price_multiplier = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=1.0,
        verbose_name="Множник ціни",
        help_text="Додатковий множник для конвертації валют",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активний",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата створення",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата оновлення",
    )

    class Meta:
        db_table = "price_parser_supplier_web_config"
        verbose_name = "Веб-парсер постачальника"
        verbose_name_plural = "Веб-парсери постачальників"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class SupplierWebUpdateLog(models.Model):
    """Log of web-scraping based supplier updates."""

    STATUS_CHOICES = [
        ("success", "Успішно"),
        ("error", "Помилка"),
        ("partial", "Частково"),
    ]

    config = models.ForeignKey(
        SupplierWebConfig,
        on_delete=models.CASCADE,
        related_name="update_logs",
        verbose_name="Конфігурація",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name="Статус",
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Час початку",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Час завершення",
    )
    items_processed = models.PositiveIntegerField(
        default=0,
        verbose_name="Перевірено товарів",
    )
    items_matched = models.PositiveIntegerField(
        default=0,
        verbose_name="Знайдено на сайті",
    )
    items_updated = models.PositiveIntegerField(
        default=0,
        verbose_name="Оновлено товарів",
    )
    errors = models.JSONField(
        default=list,
        verbose_name="Помилки",
    )
    log_details = models.TextField(
        blank=True,
        verbose_name="Деталі логу",
    )

    class Meta:
        db_table = "price_parser_supplier_web_log"
        verbose_name = "Лог веб-парсера постачальника"
        verbose_name_plural = "Логи веб-парсерів постачальників"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.config.name} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def duration_seconds(self) -> Optional[int]:
        if self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None


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


class FurnitureModelPriceMapping(models.Model):
    """Block-structured mapping: locate furniture price by matching the model's
    name and price-type text within the sheet, instead of a fixed row/column.

    Used for suppliers (e.g. "Джем") whose Google Sheet groups models into
    blocks with their own local headers, so a fixed cell reference breaks
    whenever the supplier edits the sheet layout.
    """

    furniture = models.ForeignKey(
        Furniture,
        on_delete=models.CASCADE,
        related_name='model_price_mappings',
        verbose_name="Меблі"
    )
    config = models.ForeignKey(
        GoogleSheetConfig,
        on_delete=models.CASCADE,
        related_name='model_price_mappings',
        verbose_name="Конфігурація Google таблиці"
    )
    model_label = models.CharField(
        max_length=200,
        verbose_name="Назва моделі в таблиці",
        help_text="Текст точно як у таблиці постачальника, наприклад 'Slim', 'Boston А'."
    )
    price_type = models.CharField(
        max_length=150,
        verbose_name="Тип ціни",
        help_text="Текст заголовка цінової колонки в блоці, наприклад 'HPL покриття'."
    )
    size_variant = models.ForeignKey(
        'furniture.FurnitureSizeVariant',
        on_delete=models.CASCADE,
        related_name='model_price_mappings',
        verbose_name="Розмірний варіант",
        null=True,
        blank=True,
        help_text=(
            "Вкажіть, якщо у моделі в таблиці декілька рядків розміру. "
            "Парсер зіставляє рядок таблиці з варіантом за шириною/довжиною/висотою."
        )
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
        db_table = "price_parser_furniture_model_price_mapping"
        verbose_name = "Зв'язок меблів з моделлю (блочний прайс)"
        verbose_name_plural = "Зв'язки меблів з моделями (блочний прайс)"
        unique_together = ['furniture', 'config', 'model_label', 'price_type', 'size_variant']
        ordering = ['config', 'model_label', 'price_type']

    def __str__(self):
        return f"{self.furniture.name} — {self.model_label} / {self.price_type}"


class EurosofPriceConfig(models.Model):
    """Singleton config for Eurosof price calculation."""
    price_multiplier = models.DecimalField(
        max_digits=6, decimal_places=4, default="1.4000",
        verbose_name="Коефіцієнт множення",
        help_text="На цей коефіцієнт множиться ціна з каталогу (зараз 1.4)",
    )
    price_addon = models.DecimalField(
        max_digits=10, decimal_places=2, default="2000.00",
        verbose_name="Надбавка (грн)",
        help_text="Фіксована надбавка до ціни після множення (зараз 2000)",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Останнє оновлення")

    class Meta:
        verbose_name = "Конфігурація цін Eurosof"

    def __str__(self):
        return f"Eurosof: ×{self.price_multiplier} + {self.price_addon}"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class DivanoffPriceConfig(models.Model):
    """Singleton config for Divanoff base price calculation.

    Застосовується лише до базової ціни (категорія тканини "Стандарт").
    Крок за категорію тканини (Furniture.fabric_value) рахується окремо
    від сирих цін прайсу і формулою не множиться — лишається як є.
    """
    price_multiplier = models.DecimalField(
        max_digits=6, decimal_places=4, default="1.4500",
        verbose_name="Коефіцієнт множення",
        help_text="На цей коефіцієнт множиться базова ціна з прайсу (зараз 1.45)",
    )
    price_addon = models.DecimalField(
        max_digits=10, decimal_places=2, default="2000.00",
        verbose_name="Надбавка (грн)",
        help_text="Фіксована надбавка до базової ціни після множення (зараз 2000)",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Останнє оновлення")

    class Meta:
        verbose_name = "Конфігурація цін Divanoff"

    def __str__(self):
        return f"Divanoff: ×{self.price_multiplier} + {self.price_addon}"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
