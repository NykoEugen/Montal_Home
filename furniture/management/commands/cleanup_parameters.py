"""
Management command:
  1. Видаляє параметри-виробники (торгова марка, бренд, виробник тощо),
     крім «країна виробник».
  2. Нормалізує одиниці вимірювання розмірів: приводить значення до сантиметрів.
     Значення > 300 вважається міліметрами (типові розміри меблів: 40–300 см).
  3. Нормалізує розділювач у розмірних значеннях: *, х (кирилиця), X → x.
     Наприклад: «100*120» або «100х120» → «100x120».
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction

from params.models import FurnitureParameter, Parameter

# Паттерн: label містить щось із цього списку → параметр-виробник → видаляємо
MANUFACTURER_RE = re.compile(
    r"(торгова\s*марка|торг[\.\s]марка|бренд|brand|виробник|manufacturer|фабрика|"
    r"постачальник|supplier|марка\s*(матрацу|меблів|товару|бренду)?)",
    re.IGNORECASE,
)
# Виняток: якщо label містить це — НЕ видаляємо
MANUFACTURER_KEEP_RE = re.compile(r"країна", re.IGNORECASE)

DIMENSION_KEYS = {"width_cm", "height_cm", "depth_cm"}
# Параметри, що можуть містити композитний формат типу «100x200»
DIMENSION_LABEL_RE = re.compile(
    r"(ширин|висот|глибин|розмір|габарит|довжин)", re.IGNORECASE
)
MM_THRESHOLD = Decimal("300")  # вище — точно мм, нижче — вже см
# Усі варіанти розділювача між числами у розмірі
SEPARATOR_RE = re.compile(r"[*×хХxX\s]+")  # * × х(кир) Х(кир) x X пробіл


class Command(BaseCommand):
    help = "Видаляє 'Торгова марка' та нормалізує одиниці/формат розмірів"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати що буде зроблено, без змін у БД",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN — БД не змінюється ==="))

        with transaction.atomic():
            self._delete_manufacturer_params(dry_run)
            self._normalize_dimensions(dry_run)

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS("Готово."))

    # ------------------------------------------------------------------
    def _delete_manufacturer_params(self, dry_run: bool) -> None:
        """Видаляє параметри-виробники (бренд, торгова марка, виробник…),
        але зберігає «Країна виробник» та подібні."""
        candidates = [
            p for p in Parameter.objects.all()
            if MANUFACTURER_RE.search(p.label) and not MANUFACTURER_KEEP_RE.search(p.label)
        ]

        if not candidates:
            self.stdout.write("Параметри-виробники — не знайдено.")
            return

        self.stdout.write(f"Параметри-виробники до видалення ({len(candidates)}):")
        for param in candidates:
            fp_count = FurnitureParameter.objects.filter(parameter=param).count()
            self.stdout.write(
                f"  id={param.id} '{param.label}' (key={param.key}): {fp_count} прив'язок"
            )
            if not dry_run:
                FurnitureParameter.objects.filter(parameter=param).delete()
                param.delete()

    # ------------------------------------------------------------------
    def _normalize_dimensions(self, dry_run: bool) -> None:
        # Обробляємо і стандартні ключі, і параметри з «розмір» у мітці
        dim_params = Parameter.objects.filter(key__in=DIMENSION_KEYS)
        label_params = Parameter.objects.filter(label__iregex=DIMENSION_LABEL_RE.pattern)
        params = (dim_params | label_params).distinct()

        if not params.exists():
            self.stdout.write("Розмірні параметри не знайдено.")
            return

        total_fixed = 0
        for param in params:
            for fp in FurnitureParameter.objects.filter(parameter=param):
                new_val = self._normalize_value(fp.value)
                if new_val != fp.value:
                    self.stdout.write(
                        f"  {param.key}: furniture_id={fp.furniture_id} "
                        f"'{fp.value}' → '{new_val}'"
                    )
                    if not dry_run:
                        fp.value = new_val
                        fp.save(update_fields=["value"])
                    total_fixed += 1

        self.stdout.write(f"Розміри: виправлено {total_fixed} значень.")

    # ------------------------------------------------------------------
    def _normalize_value(self, raw: str) -> str:
        """
        Нормалізує одне значення параметра:
        - прибирає суфікси одиниць (мм, см, mm, cm)
        - конвертує мм → см якщо > 300
        - нормалізує розділювач між числами → x
        """
        stripped = raw.strip()

        # Розбиваємо на частини за будь-яким розділювачем
        # Спочатку прибираємо одиниці вимірювання з усього рядка
        cleaned = re.sub(r"\s*(мм|mm|см|cm)\s*", "", stripped, flags=re.IGNORECASE).strip()

        # Перевіряємо чи є розділювач (композитне значення)
        parts = SEPARATOR_RE.split(cleaned)
        parts = [p.strip() for p in parts if p.strip()]

        if not parts:
            return raw

        converted = []
        for part in parts:
            try:
                val = Decimal(part)
            except InvalidOperation:
                # не числова частина — повертаємо оригінал без змін
                return raw
            if val > MM_THRESHOLD:
                val = (val / Decimal("10")).normalize()
            else:
                val = val.normalize()
            converted.append(format(val, "f"))

        result = "x".join(converted)
        return result

