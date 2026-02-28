from categories.models import Category
from checkout.models import Order, OrderItem, OrderStatus
from fabric_category.models import FabricBrand, FabricCategory, FabricColor, FabricColorPalette
from furniture.models import Furniture
from params.models import Parameter
from price_parser.models import (
    FurniturePriceCellMapping,
    GoogleSheetConfig,
    PriceUpdateLog,
    SupplierFeedConfig,
    SupplierFeedUpdateLog,
)
from sub_categories.models import SubCategory
from shop.models import SeasonalSettings

from .forms import (
    CategoryForm,
    FurnitureForm,
    FurniturePriceCellMappingForm,
    FabricBrandForm,
    FabricCategoryForm,
    FabricColorForm,
    FabricColorPaletteForm,
    GoogleSheetConfigForm,
    PriceUpdateLogForm,
    SupplierFeedConfigForm,
    SupplierFeedUpdateLogForm,
    OrderForm,
    OrderStatusForm,
    OrderItemForm,
    ParameterForm,
    SubCategoryForm,
    SeasonalSettingsForm,
)
from .registry import AdminSection, registry


def register_default_sections() -> None:
    registry.register(
        AdminSection(
            slug="categories",
            model=Category,
            form_class=CategoryForm,
            list_display=("name", "slug"),
            search_fields=("name", "slug"),
            ordering=("name",),
            title="Категорії",
            description="Керування основними категоріями каталогу.",
            icon="fa-layer-group",
        )
    )
    registry.register(
        AdminSection(
            slug="sub-categories",
            model=SubCategory,
            form_class=SubCategoryForm,
            list_display=("name", "category", "slug"),
            search_fields=("name", "category__name"),
            ordering=("category__name", "name"),
            title="Підкатегорії",
            description="Обʼєднуйте товари в підкатегорії та задавайте параметри.",
            icon="fa-diagram-project",
        )
    )
    registry.register(
        AdminSection(
            slug="parameters",
            model=Parameter,
            form_class=ParameterForm,
            list_display=("key", "label"),
            search_fields=("key", "label"),
            ordering=("key",),
            title="Параметри",
            description="Довідник характеристик для товарів.",
            icon="fa-list-check",
        )
    )
    registry.register(
        AdminSection(
            slug="fabric-brands",
            model=FabricBrand,
            form_class=FabricBrandForm,
            list_display=("name",),
            search_fields=("name",),
            ordering=("name",),
            title="Тканини — бренди",
            description="Бренди тканин, доступних для меблів.",
            icon="fa-tag",
        )
    )
    registry.register(
        AdminSection(
            slug="fabric-categories",
            model=FabricCategory,
            form_class=FabricCategoryForm,
            list_display=("brand", "name", "price"),
            search_fields=("name", "brand__name"),
            ordering=("brand__name", "name"),
            title="Тканини — категорії",
            description="Цінові категорії тканин в межах обраних брендів.",
            icon="fa-palette",
        )
    )
    registry.register(
        AdminSection(
            slug="fabric-color-palettes",
            model=FabricColorPalette,
            form_class=FabricColorPaletteForm,
            list_display=("name", "brand", "is_active", "updated_at"),
            search_fields=("name", "brand__name"),
            ordering=("name",),
            title="Палітри покриттів",
            description="Групуйте кольори оббивки у палітри та привʼязуйте їх до меблів.",
            icon="fa-swatchbook",
        )
    )
    registry.register(
        AdminSection(
            slug="fabric-colors",
            model=FabricColor,
            form_class=FabricColorForm,
            list_display=("name", "palette", "hex_code", "position", "is_active"),
            search_fields=("name", "palette__name"),
            ordering=("palette__name", "position"),
            title="Кольори покриттів",
            description="Додавайте конкретні кольори (з HEX кодом) до палітр.",
            icon="fa-fill-drip",
        )
    )
    registry.register(
        AdminSection(
            slug="furniture",
            model=Furniture,
            form_class=FurnitureForm,
            list_display=(
                "name",
                "article_code",
                "sub_category",
                "stock_status",
                "price",
                "is_promotional",
                "updated_at",
            ),
            list_display_labels=(
                "Назва",
                "Артикул",
                "Підкатегорія",
                "Наявність",
                "Ціна",
                "Акція",
                "Оновлено",
            ),
            search_fields=("name", "article_code", "sub_category__name"),
            ordering=("-updated_at",),
            title="Меблі",
            description="Повний CRUD по товарах каталогу.",
            icon="fa-couch",
        )
    )
    registry.register(
        AdminSection(
            slug="orders",
            model=Order,
            form_class=OrderForm,
            list_display=(
                "id",
                "customer_full_name",
                "customer_phone_number",
                "created_at",
                "delivery_type",
                "payment_type",
                "status",
                "is_confirmed",
            ),
            list_display_labels=(
                "ID",
                "Клієнт",
                "Телефон",
                "Створено",
                "Доставка",
                "Оплата",
                "Статус",
                "Підтверджено",
            ),
            search_fields=(
                "customer_name",
                "customer_last_name",
                "customer_phone_number",
                "customer_email",
            ),
            ordering=("-created_at",),
            title="Замовлення",
            description="Перегляд і редагування замовлень клієнтів.",
            icon="fa-box",
        )
    )
    registry.register(
        AdminSection(
            slug="order-items",
            model=OrderItem,
            form_class=OrderItemForm,
            list_display=(
                "order",
                "furniture",
                "quantity",
                "price",
                "is_promotional",
            ),
            list_display_labels=(
                "Замовлення",
                "Товар",
                "Кількість",
                "Ціна",
                "Акційний",
            ),
            search_fields=("order__id", "furniture__name", "custom_option_name"),
            ordering=("-id",),
            title="Позиції замовлень",
            description="Редагуйте склад та ціни в замовленнях.",
            icon="fa-cart-shopping",
        )
    )
    registry.register(
        AdminSection(
            slug="order-statuses",
            model=OrderStatus,
            form_class=OrderStatusForm,
            list_display=("name", "slug", "salesdrive_status_id", "is_default", "is_active", "sort_order"),
            search_fields=("name", "slug"),
            ordering=("sort_order", "name"),
            title="Статуси замовлень",
            description="Створюйте та синхронізуйте статуси з SalesDrive.",
            icon="fa-signal",
        )
    )
    registry.register(
        AdminSection(
            slug="price-configs",
            model=GoogleSheetConfig,
            form_class=GoogleSheetConfigForm,
            list_display=(
                "name",
                "sheet_id",
                "sheet_name",
                "price_multiplier",
                "is_active",
                "updated_at",
            ),
            list_display_labels=(
                "Назва",
                "Sheet ID",
                "Сторінка",
                "Множник",
                "Активна",
                "Оновлено",
            ),
            search_fields=("name", "sheet_id", "sheet_name"),
            ordering=("-updated_at",),
            title="Парсер цін — джерела",
            description="Налаштування Google Sheets/XLSX для оновлення цін.",
            icon="fa-table",
        )
    )
    registry.register(
        AdminSection(
            slug="supplier-feeds",
            model=SupplierFeedConfig,
            form_class=SupplierFeedConfigForm,
            list_display=(
                "name",
                "supplier",
                "category_hint",
                "price_multiplier",
                "is_active",
                "updated_at",
            ),
            list_display_labels=(
                "Назва",
                "Постачальник",
                "Категорія",
                "Множник",
                "Активний",
                "Оновлено",
            ),
            search_fields=("name", "supplier", "category_hint"),
            ordering=("-updated_at",),
            title="Фіди постачальників",
            description="XML/YML джерела (наприклад, Matrolux) для автоматичного оновлення цін.",
            icon="fa-cloud-arrow-down",
        )
    )
    registry.register(
        AdminSection(
            slug="price-mappings",
            model=FurniturePriceCellMapping,
            form_class=FurniturePriceCellMappingForm,
            list_display=(
                "furniture",
                "config",
                "price_type",
                "sheet_row",
                "sheet_column",
                "is_active",
            ),
            list_display_labels=(
                "Меблі",
                "Конфігурація",
                "Тип ціни",
                "Рядок",
                "Колонка",
                "Активна",
            ),
            search_fields=("furniture__name", "config__name", "price_type"),
            ordering=("furniture__name", "price_type"),
            title="Парсер цін — мапінги",
            description="Привʼязка товарів до конкретних комірок прайсів.",
            icon="fa-table-cells",
        )
    )
    registry.register(
        AdminSection(
            slug="supplier-feed-logs",
            model=SupplierFeedUpdateLog,
            form_class=SupplierFeedUpdateLogForm,
            list_display=(
                "config",
                "status",
                "offers_processed",
                "items_matched",
                "items_updated",
                "started_at",
            ),
            list_display_labels=(
                "Конфігурація",
                "Статус",
                "Оферів",
                "Збігів",
                "Оновлено",
                "Початок",
            ),
            search_fields=("config__name",),
            ordering=("-started_at",),
            title="Логи фідів постачальників",
            description="Історія запусків XML/YML парсерів.",
            icon="fa-clipboard-list",
            allow_create=False,
            allow_edit=False,
            allow_delete=False,
            read_only=True,
        )
    )
    registry.register(
        AdminSection(
            slug="seasonal-settings",
            model=SeasonalSettings,
            form_class=SeasonalSettingsForm,
            list_display=("name", "is_enabled", "updated_at"),
            list_display_labels=("Назва", "Увімкнено", "Оновлено"),
            ordering=("-updated_at",),
            title="Сезонне оформлення",
            description="Керуйте відображенням гірлянд та снігу на сайті.",
            icon="fa-lightbulb",
            allow_create=False,
            allow_delete=False,
        )
    )
    registry.register(
        AdminSection(
            slug="price-logs",
            model=PriceUpdateLog,
            form_class=PriceUpdateLogForm,
            list_display=(
                "config",
                "status",
                "started_at",
                "completed_at",
                "items_updated",
                "items_processed",
            ),
            list_display_labels=(
                "Конфігурація",
                "Статус",
                "Початок",
                "Завершення",
                "Оновлено",
                "Оброблено",
            ),
            search_fields=("config__name", "status"),
            ordering=("-started_at",),
            title="Парсер цін — логи",
            description="Журнал запусків оновлення цін.",
            icon="fa-clock-rotate-left",
            allow_create=False,
            allow_delete=False,
            read_only=True,
        )
    )


# Register sections at import time.
register_default_sections()
