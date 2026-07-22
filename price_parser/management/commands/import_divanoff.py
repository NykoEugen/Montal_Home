import os

from django.core.management.base import BaseCommand

SUBCATEGORY_SLUG = "divany-divanoff"

DEFAULT_XLSX = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "divanoff_price.xlsx",
)


class Command(BaseCommand):
    help = (
        "Імпорт диванів Divanoff: опис/фото/характеристики з divanoff.ua, "
        "ціни з Excel-прайсу. Запускати ЛОКАЛЬНО."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--xlsx",
            default=DEFAULT_XLSX,
            help="Шлях до Excel-прайсу (за замовчуванням: divanoff_price.xlsx у корені проекту)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати що буде імпортовано без змін у БД",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Обмежити кількість URL (для тесту)",
        )
        parser.add_argument(
            "--update-prices",
            action="store_true",
            help="Тільки оновити ціни для існуючих товарів",
        )
        parser.add_argument(
            "--price-col",
            type=int,
            default=2,
            help="0-індекс колонки ціни в Excel (2=категорія 0, найдешевша; 3=кат.I; ...9=кат.VII)",
        )
        parser.add_argument(
            "--subcategory",
            default=SUBCATEGORY_SLUG,
            help="Slug підкатегорії",
        )
        parser.add_argument(
            "--database-url",
            metavar="URL",
            help="URL продакшн БД (postgres://user:pass@host/db)",
        )

    def handle(self, *args, **options):
        db_url = options.get("database_url")
        if db_url:
            import dj_database_url
            from django.conf import settings
            settings.DATABASES["default"] = dj_database_url.parse(db_url, conn_max_age=600)
            self.stdout.write(f"БД: {db_url.split('@')[-1]}")

        from price_parser.divanoff_scraper import DivanoffScraper

        xlsx = options["xlsx"]
        if not os.path.exists(xlsx):
            self.stderr.write(
                f"✗ Excel-файл не знайдено: {xlsx}\n"
                "  Завантажте прайс з Google Sheets (File → Download → .xlsx) "
                "і збережіть як divanoff_price.xlsx у корені проекту."
            )
            return

        scraper = DivanoffScraper()
        scraper.set_progress_callback(lambda msg: self.stdout.write(msg))

        subcategory = options["subcategory"]
        dry_run = options["dry_run"]
        price_col = options["price_col"]
        limit = options["limit"]

        if options["update_prices"]:
            result = scraper.update_prices(
                subcategory_slug=subcategory,
                xlsx_path=xlsx,
                price_col=price_col,
            )
        else:
            result = scraper.run_import(
                subcategory_slug=subcategory,
                xlsx_path=xlsx,
                dry_run=dry_run,
                limit=limit,
                price_col=price_col,
            )

        self.stdout.write(f"\n{'='*60}")
        if result.get("success"):
            if options["update_prices"]:
                self.stdout.write(
                    f"Ціни оновлено: перевірено={result.get('checked', 0)}, "
                    f"оновлено={result.get('updated', 0)}, "
                    f"не знайдено в БД={result.get('not_found', 0)}, "
                    f"не знайдено в прайсі={result.get('unmatched', 0)}"
                )
            else:
                self.stdout.write(
                    f"Результат: створено={result.get('created', 0)}, "
                    f"оновлено={result.get('updated', 0)}, "
                    f"пропущено={result.get('skipped', 0)}, "
                    f"не знайдено в прайсі={result.get('unmatched', 0)}"
                )
            if dry_run:
                self.stdout.write("(DRY-RUN — жодних змін у БД)")
        else:
            self.stderr.write(f"✗ Помилка: {result.get('error')}")
