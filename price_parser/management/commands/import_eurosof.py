import os

from django.core.management.base import BaseCommand

CATALOG_CONFIGS = {
    "pryami-evroknizhka": {
        "url": "https://eurosof.com.ua/catalog/pryami-evroknizhka",
        "subcategory_name": "Прямі євро-книжки",
        "subcategory_slug": "pryami-evroknizhka-eurosof",
        "category_name": "М'які меблі",
        "corner": False,
        "bed": False,
    },
    "kutovij-divan": {
        "url": "https://eurosof.com.ua/catalog/kutovij-divan",
        "subcategory_name": "Кутові дивани",
        "subcategory_slug": "kutovi-divany-eurosof",
        "category_name": "М'які меблі",
        "corner": True,
        "bed": False,
    },
    "pryami-vikatni": {
        "url": "https://eurosof.com.ua/catalog/pryami-vikatni",
        "subcategory_name": "Прямі викатні",
        "subcategory_slug": "pryami-vikatni-eurosof",
        "category_name": "М'які меблі",
        "corner": False,
        "bed": False,
    },
    "lizhka": {
        "url": "https://eurosof.com.ua/catalog/lizhka",
        "subcategory_name": "Ліжка з м'яким узголів'ям",
        "subcategory_slug": "lizhka-z-myakim-uzgolivyam",
        "category_name": "Ліжка",
        "corner": False,
        "bed": True,
    },
    "dityachi-lizhka": {
        "url": "https://eurosof.com.ua/catalog/dityachi-lizhka",
        "subcategory_name": "Дитячі ліжка",
        "subcategory_slug": "dityachi-lizhka",
        "category_name": "Ліжка",
        "corner": False,
        "bed": True,
    },
}

DEFAULT_XLSX = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "Прайс Eurosof Б.Церква 05.05.26р.xlsx",
)


class Command(BaseCommand):
    help = (
        "Імпорт диванів Eurosof: опис/фото/характеристики з сайту, "
        "ціни з Excel-каталогу. Запускати ЛОКАЛЬНО."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog",
            choices=list(CATALOG_CONFIGS.keys()) + ["all"],
            default="pryami-evroknizhka",
            help="Який каталог імпортувати",
        )
        parser.add_argument(
            "--xlsx",
            default=DEFAULT_XLSX,
            help="Шлях до Excel-прайсу (за замовчуванням: корінь проекту)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати що буде імпортовано без змін у БД",
        )
        parser.add_argument(
            "--update-prices",
            action="store_true",
            help="Тільки оновити ціни для існуючих товарів",
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

        from price_parser.eurosof_scraper import EurosofImporter

        xlsx = options["xlsx"]
        if not os.path.exists(xlsx):
            self.stderr.write(f"✗ Excel-файл не знайдено: {xlsx}")
            return

        catalog_arg = options["catalog"]
        dry_run = options["dry_run"]
        update_prices = options["update_prices"]

        configs = (
            list(CATALOG_CONFIGS.values())
            if catalog_arg == "all"
            else [CATALOG_CONFIGS[catalog_arg]]
        )

        importer = EurosofImporter(xlsx_path=xlsx)
        importer.set_progress_callback(lambda msg: self.stdout.write(msg))

        all_stats = {"created": 0, "updated": 0, "skipped": 0, "unmatched": 0, "errors": []}

        for cfg in configs:
            self.stdout.write(f"\n{'─'*60}")
            self.stdout.write(f"Каталог: {cfg['subcategory_name']}")
            self.stdout.write(f"{'─'*60}")

            stats = importer.run(
                catalog_urls=[cfg["url"]],
                subcategory_name=cfg["subcategory_name"],
                subcategory_slug=cfg["subcategory_slug"],
                category_name=cfg["category_name"],
                corner=cfg.get("corner", False),
                bed=cfg.get("bed", False),
                dry_run=dry_run,
                update_prices=update_prices,
            )
            for key in ("created", "updated", "skipped", "unmatched"):
                all_stats[key] += stats.get(key, 0)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(
            f"Результат: створено={all_stats['created']}, "
            f"оновлено={all_stats['updated']}, "
            f"пропущено={all_stats['skipped']}, "
            f"не знайдено={all_stats['unmatched']}"
        )
        if dry_run:
            self.stdout.write("(DRY-RUN — жодних змін у БД)")
