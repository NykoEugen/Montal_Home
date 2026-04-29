import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from price_parser.kreslalux_scraper import KreslaluxScraper


class Command(BaseCommand):
    help = "Імпорт крісел з kreslalux.ua. --export-json: зберегти дані в файл (для запуску локально)."

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
            "--export-json",
            metavar="FILE",
            help="Зберегти зібрані дані у JSON-файл (без імпорту в БД). "
                 "Потім завантажте файл через custom_admin → Kreslalux → Імпорт з файлу.",
        )

    def handle(self, *args, **options):
        max_price = Decimal(str(options["max_price"]))
        dry_run = options["dry_run"]
        limit = options.get("limit")
        subcategory_slug = options["subcategory"]
        export_path = options.get("export_json")

        scraper = KreslaluxScraper(max_price=max_price)
        scraper.set_progress_callback(lambda msg: self.stdout.write(msg))

        # ── Export mode ───────────────────────────────────────────────────────
        if export_path:
            self.stdout.write(
                f"Збираємо дані з kreslalux.ua (ціна ≤ {max_price} грн)"
                + (f", ліміт {limit}" if limit else "")
            )
            products = scraper.export_to_json(limit=limit)
            out = Path(export_path)
            out.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nГотово! Зібрано {len(products)} товарів → {out.resolve()}\n"
                    f"Завантажте цей файл через custom_admin → Kreslalux → «Імпорт з файлу»."
                )
            )
            return

        # ── Direct import mode ────────────────────────────────────────────────
        self.stdout.write(
            f"Старт імпорту kreslalux.ua → підкатегорія '{subcategory_slug}', "
            f"ціна ≤ {max_price} грн"
            + (" [DRY-RUN]" if dry_run else "")
        )

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
