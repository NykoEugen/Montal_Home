from django.core.management.base import BaseCommand

from price_parser.models import SupplierFeedConfig


DEFAULT_FEED_URL = "https://matroluxe.ua/index.php?route=extension/feed/yandex_yml9"
DEFAULT_NAME = "Matroluxe — матраці"


class Command(BaseCommand):
    help = "Створює/оновлює SupplierFeedConfig для каталогу матраців Matroluxe (yml9)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--feed-url",
            default=DEFAULT_FEED_URL,
            help="Посилання на Matroluxe YML матраців (якщо інше ніж стандартне).",
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
                "category_hint": "Матраці (YML)",
                "price_multiplier": 1,
                "match_by_article": True,
                "match_by_name": True,
                "is_active": True,
                # Кожен матрац має N офферів (розміри), кожен зі своєю ціною.
                # <vendorCode> — чистий артикул, спільний для всіх розмірів.
                "article_tag_name": "vendorCode",
                "article_prefix_parts": 0,
                # Оновлюємо FurnitureSizeVariant за розміром з <param name="Розмір матрацу (ШхД)">.
                "update_size_variants": True,
                "size_param_name": "Розмір матрацу (ШхД)",
            },
        )

        action = "Створено" if created else "Оновлено"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} конфігурацію '{config.name}'. "
                "Запускайте парсер у кастомній адмінці (розділ Supplier Feeds)."
            )
        )
