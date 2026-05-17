from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Імпорт столів Generic з evrodim-company.com.ua/yevrodim. "
        "Фільтрує тільки товари з назвою 'Стіл*' та Виробник=Generic."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--subcategory",
            default="stoly-evrodim",
            help="Slug підкатегорії куди імпортувати (default: stoly-evrodim)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати що буде імпортовано без змін у БД",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Обмежити кількість URL з каталогу (для тестів)",
        )
        parser.add_argument(
            "--update-prices",
            action="store_true",
            help="Тільки оновити ціни існуючих товарів",
        )
        parser.add_argument(
            "--update-params",
            action="store_true",
            help="Тільки оновити характеристики (Розміри тощо) існуючих товарів",
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

        from price_parser.evrodim_scraper import EvrodimScraper

        subcategory_slug = options["subcategory"]
        dry_run = options["dry_run"]
        limit = options.get("limit")
        update_only = options["update_prices"]
        update_params = options["update_params"]

        scraper = EvrodimScraper()
        scraper.set_progress_callback(lambda msg: self.stdout.write(msg))

        if update_params:
            result = scraper.update_params(subcategory_slug)
        elif update_only:
            result = scraper.update_prices(subcategory_slug)
        else:
            self.stdout.write(
                self.style.HTTP_INFO(
                    f"=== Evrodim: столи Generic ==="
                    + (" [DRY-RUN]" if dry_run else "")
                )
            )
            result = scraper.run_import(
                subcategory_slug=subcategory_slug,
                dry_run=dry_run,
                limit=limit,
            )

        if not result.get("success"):
            self.stdout.write(self.style.ERROR(f"Помилка: {result.get('error')}"))
            return

        if update_params:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Характеристики оновлено: перевірено={result['checked']}, "
                    f"оновлено={result['updated']}, не знайдено={result['not_found']}"
                )
            )
        elif update_only:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Ціни оновлено: перевірено={result['checked']}, "
                    f"оновлено={result['updated']}, не знайдено={result['not_found']}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Завершено: створено={result['created']}, "
                    f"оновлено={result['updated']}, "
                    f"пропущено={result['skipped']}, "
                    f"не столи/не Generic={result['not_table']}"
                )
            )

        if result.get("errors"):
            self.stdout.write(self.style.WARNING(f"Помилки ({len(result['errors'])}):"))
            for err in result["errors"][:10]:
                self.stdout.write(f"  - {err}")
