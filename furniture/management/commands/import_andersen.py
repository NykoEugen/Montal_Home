import os

from django.core.management.base import BaseCommand

from price_parser.andersen_scraper import CATALOG_CONFIGS


class Command(BaseCommand):
    help = (
        "Імпорт матраців/подушок/наматрацників з andersen.ua. "
        "Запускати ЛОКАЛЬНО. Парсить розмірні варіанти з цінами (regular + sale)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog",
            choices=list(CATALOG_CONFIGS.keys()) + ["all"],
            default="all",
            help="Який каталог імпортувати (matratsy / podushky / namatratsnyky / all)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати що буде імпортовано без змін у БД",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Обмежити кількість товарів на каталог (для тестів)",
        )
        parser.add_argument(
            "--update-prices",
            action="store_true",
            help="Тільки оновити ціни для існуючих товарів (без створення нових)",
        )
        parser.add_argument(
            "--fix-promo",
            action="store_true",
            help=(
                "Виправити is_promotional / promotional_price на вже імпортованих товарах "
                "без повного re-scrape (читає з БД, не звертається до сайту)"
            ),
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
        db_url = options.get("database_url")
        if db_url:
            import dj_database_url
            from django.conf import settings
            settings.DATABASES["default"] = dj_database_url.parse(db_url, conn_max_age=600)
            self.stdout.write(f"БД: {db_url.split('@')[-1]}")

        from price_parser.andersen_scraper import AndersenScraper

        catalog_arg = options["catalog"]
        dry_run = options["dry_run"]
        limit = options.get("limit")
        update_only = options["update_prices"]
        fix_promo = options["fix_promo"]

        catalogs = list(CATALOG_CONFIGS.keys()) if catalog_arg == "all" else [catalog_arg]

        scraper = AndersenScraper()
        scraper.set_progress_callback(lambda msg: self.stdout.write(msg))

        if fix_promo:
            self._fix_promo(catalogs)
            return

        for catalog_key in catalogs:
            cfg = CATALOG_CONFIGS[catalog_key]
            self.stdout.write(
                self.style.HTTP_INFO(
                    f"\n=== {cfg['subcategory_name']} ({catalog_key}) ==="
                    + (" [DRY-RUN]" if dry_run else "")
                    + (" [UPDATE-PRICES]" if update_only else "")
                )
            )

            if update_only:
                result = scraper.update_prices(catalog_key)
            else:
                result = scraper.run_import(
                    catalog_key=catalog_key,
                    dry_run=dry_run,
                    limit=limit,
                )

            if not result.get("success"):
                self.stdout.write(self.style.ERROR(f"Помилка: {result.get('error')}"))
                continue

            if update_only:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Ціни оновлено: перевірено={result['checked']}, "
                        f"оновлено={result['updated']}, "
                        f"не знайдено={result['not_found']}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Завершено: створено={result['created']}, "
                        f"оновлено={result['updated']}, "
                        f"пропущено={result['skipped']}"
                    )
                )

            if result.get("errors"):
                self.stdout.write(self.style.WARNING(f"Помилки ({len(result['errors'])}):"))
                for err in result["errors"][:10]:
                    self.stdout.write(f"  - {err}")

    def _fix_promo(self, catalogs):
        """
        Читає вже збережені FurnitureSizeVariant і синхронізує
        is_promotional / promotional_price на батьківській Furniture.
        Не звертається до сайту.
        """
        from furniture.models import Furniture, FurnitureSizeVariant
        from price_parser.andersen_scraper import CATALOG_CONFIGS

        total_fixed = 0
        for catalog_key in catalogs:
            slug = CATALOG_CONFIGS[catalog_key]["subcategory_slug"]
            furnitures = Furniture.objects.filter(sub_category__slug=slug).prefetch_related("size_variants")
            fixed = 0

            for furniture in furnitures:
                variants = list(furniture.size_variants.all())
                if variants:
                    # Варіант з мінімальною regular ціною
                    cheapest = min(variants, key=lambda v: v.price)
                    is_promo = cheapest.is_promotional and cheapest.promotional_price is not None
                    promo_price = cheapest.promotional_price if is_promo else None
                else:
                    # Flat-price товар — is_promotional вже має бути встановлено
                    continue

                fields = []
                if furniture.is_promotional != is_promo:
                    furniture.is_promotional = is_promo
                    fields.append("is_promotional")
                if furniture.promotional_price != promo_price:
                    furniture.promotional_price = promo_price
                    fields.append("promotional_price")
                if fields:
                    furniture.save(update_fields=fields)
                    fixed += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"{CATALOG_CONFIGS[catalog_key]['subcategory_name']}: виправлено {fixed} записів"
                )
            )
            total_fixed += fixed

        self.stdout.write(self.style.SUCCESS(f"Разом виправлено: {total_fixed}"))
