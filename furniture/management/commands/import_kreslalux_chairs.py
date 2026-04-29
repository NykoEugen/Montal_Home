import os
from decimal import Decimal

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Імпорт крісел з kreslalux.ua. "
        "Запускати ЛОКАЛЬНО — сервер отримує 403 від Cloudflare. "
        "Скрейп + завантаження картинок на R2 + запис у БД відбуваються на локальному ПК."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-price",
            type=float,
            default=40000,
            help="Максимальна ціна для фільтрації (грн, за замовч. 40000)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати що буде імпортовано без змін у БД",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Обмежити кількість товарів (для тестів)",
        )
        parser.add_argument(
            "--subcategory",
            default="ortopedichni-krisla",
            help="Slug підкатегорії для імпорту",
        )
        parser.add_argument(
            "--database-url",
            metavar="URL",
            help=(
                "URL продакшн БД (postgres://user:pass@host/db). "
                "Перевизначає DATABASE_URL з .env для цього запуску."
            ),
        )

    def handle(self, *args, **options):
        # Override DB connection if --database-url is provided
        db_url = options.get("database_url")
        if db_url:
            import dj_database_url
            from django.conf import settings
            settings.DATABASES["default"] = dj_database_url.parse(db_url, conn_max_age=600)
            self.stdout.write(f"БД: {db_url.split('@')[-1]}")  # log only host/db, not creds

        from price_parser.kreslalux_scraper import KreslaluxScraper

        max_price = Decimal(str(options["max_price"]))
        dry_run = options["dry_run"]
        limit = options.get("limit")
        subcategory_slug = options["subcategory"]

        self.stdout.write(
            f"Старт імпорту kreslalux.ua → підкатегорія '{subcategory_slug}', "
            f"ціна ≤ {max_price} грн"
            + (" [DRY-RUN]" if dry_run else "")
        )

        scraper = KreslaluxScraper(max_price=max_price)
        scraper.set_progress_callback(lambda msg: self.stdout.write(msg))

        result = scraper.run_import(
            dry_run=dry_run,
            limit=limit,
            subcategory_slug=subcategory_slug,
        )

        if not result.get("success"):
            self.stdout.write(self.style.ERROR(f"Помилка: {result.get('error')}"))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Завершено: створено={result['created']}, "
                f"оновлено={result['updated']}, "
                f"пропущено={result['skipped']}"
            )
        )
        if result["errors"]:
            self.stdout.write(self.style.WARNING(f"Помилки ({len(result['errors'])}):"))
            for err in result["errors"][:10]:
                self.stdout.write(f"  - {err}")
