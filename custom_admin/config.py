from categories.models import Category
from checkout.models import Order, OrderItem
from fabric_category.models import FabricBrand, FabricCategory
from furniture.models import Furniture
from params.models import Parameter
from price_parser.models import (
    FurniturePriceCellMapping,
    GoogleSheetConfig,
    PriceUpdateLog,
)
from sub_categories.models import SubCategory

from .forms import (
    CategoryForm,
    FurnitureForm,
    FurniturePriceCellMappingForm,
    FabricBrandForm,
    FabricCategoryForm,
    GoogleSheetConfigForm,
    OrderForm,
    OrderItemForm,
    ParameterForm,
    SubCategoryForm,
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
            ),
            list_display_labels=(
                "ID",
                "Клієнт",
                "Телефон",
                "Створено",
                "Доставка",
                "Оплата",
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
            slug="price-logs",
            model=PriceUpdateLog,
            form_class=None,
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
            allow_edit=False,
            allow_delete=False,
        )
    )


# Register sections at import time.
register_default_sections()
