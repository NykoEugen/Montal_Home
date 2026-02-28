from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from categories.models import Category
from fabric_category.models import FabricColorPalette
from furniture.models import Furniture, FurnitureVariantImage


@dataclass(slots=True)
class PaletteTargets:
    thickness_label: str
    search_phrase: str
    palette: FabricColorPalette | None
    added_count: int = 0


class Command(BaseCommand):
    help = (
        "Очищає варіанти кольорів для корпусних меблів та підʼєднує палітри "
        "покриттів на основі тексту опису (ДСП 16/18 мм)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            default="Корпусні меблі",
            help="Назва категорії, для якої застосовуються зміни. Використайте 'all' для всього каталогу.",
        )
        parser.add_argument(
            "--sub-categories",
            nargs="+",
            default=None,
            help="Додатково обмежити перелік меблів підкатегоріями (наприклад: \"Комп'ютерні столи\" \"Журнальні столи\").",
        )
        parser.add_argument(
            "--palette-16",
            default="16 мм",
            help="Ідентифікатор або частина назви палітри для 16 мм (за замовчуванням шукає за підрядком '16 мм').",
        )
        parser.add_argument(
            "--palette-18",
            default="18 мм",
            help="Ідентифікатор або частина назви палітри для 18 мм (за замовчуванням шукає за підрядком '18 мм').",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Лише показати план дій без внесення змін.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Виводити детальну інформацію по кожному товару.",
        )

    def handle(self, *args, **options):
        category_name: str = options["category"]
        subcategory_names: list[str] | None = options["sub_categories"]
        dry_run: bool = options["dry_run"]
        verbose: bool = options["verbose"]

        furniture_qs = Furniture.objects.all()
        category = None

        if category_name and category_name.lower() != "all":
            category = Category.objects.filter(name__iexact=category_name).first()
            if category is None:
                raise CommandError(f"Категорію '{category_name}' не знайдено.")
            furniture_qs = furniture_qs.filter(sub_category__category=category)

        if subcategory_names:
            furniture_qs = furniture_qs.filter(sub_category__name__in=subcategory_names)

        furniture_qs = furniture_qs.select_related("sub_category", "sub_category__category").prefetch_related(
            "color_palettes", "variant_images"
        )

        if not furniture_qs.exists():
            self.stdout.write(self.style.WARNING("Для вказаної категорії немає меблів."))
            return

        self.stdout.write(
            self.style.NOTICE(
                "Опрацьовуємо {count} товарів{scope}.".format(
                    count=furniture_qs.count(),
                    scope=(
                        f" у категорії '{category.name}'"
                        if category
                        else (" у підкатегоріях: " + ", ".join(subcategory_names) if subcategory_names else " у каталозі")
                    ),
                )
            )
        )

        palette_targets = [
            PaletteTargets(
                thickness_label="16 мм",
                search_phrase="16 мм",
                palette=self._resolve_palette(options["palette_16"], "16 мм"),
            ),
            PaletteTargets(
                thickness_label="18 мм",
                search_phrase="18 мм",
                palette=self._resolve_palette(options["palette_18"], "18 мм"),
            ),
        ]

        missing_targets = [p.thickness_label for p in palette_targets if p.palette is None]
        if missing_targets:
            raise CommandError(
                "Не вдалося знайти палітри покриттів для товщин: "
                + ", ".join(missing_targets)
            )

        stats = {
            "items_processed": 0,
            "variants_removed": 0,
            "furniture_without_variants": 0,
        }

        for furniture in furniture_qs.iterator(chunk_size=100):
            stats["items_processed"] += 1
            variant_count = len(furniture.variant_images.all())

            if variant_count:
                stats["variants_removed"] += variant_count
                if verbose:
                    self.stdout.write(
                        f"- {furniture.name}: видаляємо {variant_count} кольорових варіантів"
                    )
                if not dry_run:
                    self._delete_variants(furniture)
            else:
                stats["furniture_without_variants"] += 1

            description = (furniture.description or "").lower()
            if not description.strip():
                continue

            for target in palette_targets:
                if target.search_phrase in description:
                    already_linked = furniture.color_palettes.filter(
                        pk=target.palette.pk
                    ).exists()
                    if already_linked:
                        continue

                    target.added_count += 1
                    if verbose:
                        self.stdout.write(
                            f"  • {furniture.name}: додаємо палітру '{target.palette.name}' ({target.thickness_label})"
                        )
                    if not dry_run:
                        furniture.color_palettes.add(target.palette)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nDRY-RUN: Зміни не збережено. Нижче наведена статистика, що б відбулося:"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Оброблено товарів: {stats['items_processed']}. "
                f"Видалено кольорових варіантів: {stats['variants_removed']}."
            )
        )
        self.stdout.write(
            f"Товарів без кольорових варіантів: {stats['furniture_without_variants']}."
        )

        for target in palette_targets:
            self.stdout.write(
                f"Палітра {target.thickness_label}: додано до {target.added_count} товарів "
                f"('{target.palette.name}')."
            )

    def _resolve_palette(self, identifier: str | None, fallback_fragment: str) -> FabricColorPalette | None:
        """
        Підбирає палітру за переданим значенням. Спочатку намагається підібрати за ID,
        потім — за повним збігом назви, і вже потім — за підрядком.
        """
        if not identifier:
            identifier = fallback_fragment

        palette_qs = FabricColorPalette.objects.all()

        identifier = identifier.strip()
        if identifier.isdigit():
            palette = palette_qs.filter(pk=int(identifier)).first()
            if palette:
                return palette

        palette = palette_qs.filter(name__iexact=identifier).first()
        if palette:
            return palette

        return palette_qs.filter(name__icontains=identifier).first()

    def _delete_variants(self, furniture: Furniture) -> None:
        """Видаляє всі варіанти кольорів для переданого товару в одній транзакції."""
        with transaction.atomic():
            FurnitureVariantImage.objects.filter(furniture=furniture).delete()
