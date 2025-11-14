from django.core.management.base import BaseCommand

from price_parser.models import SupplierFeedConfig


DEFAULT_FEED_URL = "https://matroluxe.ua/index.php?route=extension/feed/yandex_yml8"
DEFAULT_NAME = "Matroluxe — корпусні меблі"


class Command(BaseCommand):
    help = "Створює/оновлює SupplierFeedConfig для каталогу Matroluxe."

    def add_arguments(self, parser):
        parser.add_argument(
            "--feed-url",
            default=DEFAULT_FEED_URL,
            help="Посилання на Matroluxe YML (якщо інше ніж стандартне).",
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
                "category_hint": "Корпусні меблі (YML)",
                "price_multiplier": 1,
                "match_by_article": True,
                "match_by_name": True,
                "is_active": True,
            },
        )

        action = "Створено" if created else "Оновлено"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} конфігурацію '{config.name}'. "
                "Можна запускати парсер у кастомній адмінці (розділ Supplier Feeds)."
            )
        )
