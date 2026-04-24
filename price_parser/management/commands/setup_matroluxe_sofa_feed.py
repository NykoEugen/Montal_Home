from django.core.management.base import BaseCommand

from price_parser.models import SupplierFeedConfig


DEFAULT_FEED_URL = "https://matroluxe.ua/index.php?route=extension/feed/yandex_yml7"
DEFAULT_NAME = "Matroluxe — дивани"


class Command(BaseCommand):
    help = "Створює/оновлює SupplierFeedConfig для каталогу диванів Matroluxe (yml7)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--feed-url",
            default=DEFAULT_FEED_URL,
            help="Посилання на Matroluxe YML диванів (якщо інше ніж стандартне).",
        )
        parser.add_argument(
            "--name",
            default=DEFAULT_NAME,
            help="Назва конфігурації у довіднику фідів.",
        )

    def handle(self, *args, **options):
        name = options["name"]
        feed_url = options["feed_url"]

        config, created = SupplierFeedConfig.objects.update_or_create(
            name=name,
            defaults={
                "feed_url": feed_url,
                "supplier": "Matroluxe",
                "category_hint": "Дивани та ліжка (YML7)",
                "price_multiplier": 1,
                "match_by_article": True,
                "match_by_name": True,
                "is_active": True,
                # Кожен офер відповідає одному товару (без варіантів розміру).
                # <vendorCode> містить артикул товару (напр. "43271", "6508-21").
                # <model> може містити суфікси кольору — тому читаємо vendorCode.
                "article_tag_name": "vendorCode",
                "article_prefix_parts": 0,
                # Дивани не мають варіантів за розміром — ціна на Furniture.
                # Ліжка з різними розмірами мають vendor_code на FurnitureSizeVariant —
                # прайс-парсер знаходить варіант напряму через _get_variant_vendor_index().
                "update_size_variants": True,
                "size_param_name": "",
            },
        )

        action = "Створено" if created else "Оновлено"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} конфігурацію '{config.name}'. "
                "Запускайте парсер у кастомній адмінці (розділ Supplier Feeds)."
            )
        )
