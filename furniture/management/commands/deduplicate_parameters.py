"""
Management command: дедублікація та нормалізація ключів параметрів.

Крок 1 — Дедублікація:
  Параметри з однаковою міткою (після нормалізації пунктуації та регістру)
  об'єднуються. Канонічний — той з меншим id (найстаріший). Всі FurnitureParameter
  і SubCategory.allowed_params переводяться на канонічний, дублікати видаляються.

  Нормалізація label для порівняння: "Ширина, см" == "Ширина (см)" == "ширина см"

Крок 2 — Нормалізація ключів:
  Параметри з некрасивим ключем (param_XXXX) що ЗАЛИШИЛИСЬ після кроку 1
  перейменовуються через транслітерацію label → ASCII slug.
  Якщо slug вже зайнятий — параметр пропускається з попередженням.

Запуск:
    python manage.py deduplicate_parameters --dry-run
    python manage.py deduplicate_parameters
"""

from __future__ import annotations

import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from params.models import FurnitureParameter, Parameter
from sub_categories.models import SubCategory

# ---------------------------------------------------------------------------
# Транслітерація українських літер → латиниця
# ---------------------------------------------------------------------------
_UA_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d",
    "е": "e", "є": "ye", "ж": "zh", "з": "z", "и": "y", "і": "i",
    "ї": "yi", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ь": "", "ю": "yu", "я": "ya",
}


def _slugify_label(label: str) -> str:
    result = []
    for ch in label.lower():
        if ch in _UA_MAP:
            result.append(_UA_MAP[ch])
        elif ch.isascii() and (ch.isalnum() or ch in "-_ "):
            result.append(ch)
        else:
            result.append("_")
    slug = re.sub(r"[\s\-]+", "_", "".join(result))
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:80]


_UNIT_SUFFIXES = re.compile(
    r"\b(см|мм|cm|mm|кг|kg|г|м\b|m\b|шт|л|inch|дюйм)\b", re.IGNORECASE
)


def _normalize_label(label: str) -> str:
    """
    Нормалізує мітку для порівняння:
      - lowercase
      - прибирає пунктуацію (,  .  ()  []  {} /)
      - прибирає одиниці вимірювання (см, мм, кг, …)
      - нормалізує пробіли

    "Максимальна висота, см" → "максимальна висота"
    "Максимальна висота"     → "максимальна висота"  → збіг!
    "Ширина (см)"            → "ширина"
    "Ширина, мм"             → "ширина"              → збіг!
    """
    text = label.lower()
    text = re.sub(r"[,.()\[\]{}/\\]", " ", text)
    text = _UNIT_SUFFIXES.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


class Command(BaseCommand):
    help = "Дедублікує параметри за label, нормалізує ключі param_XXXX → slug"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN — БД не змінюється ===\n"))

        with transaction.atomic():
            # ids параметрів що будуть видалені — step2 їх пропускає
            to_delete_ids: set[int] = self._step1_deduplicate(dry_run)
            self._step2_normalize_keys(dry_run, skip_ids=to_delete_ids)

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS("\nГотово."))

    # ------------------------------------------------------------------
    def _step1_deduplicate(self, dry_run: bool) -> set[int]:
        """Повертає set id параметрів що будуть/були видалені."""
        self.stdout.write(self.style.HTTP_INFO("── Крок 1: дедублікація ──"))

        groups: dict[str, list[Parameter]] = defaultdict(list)
        for p in Parameter.objects.all().order_by("id"):
            groups[_normalize_label(p.label)].append(p)

        duplicates = {k: v for k, v in groups.items() if len(v) > 1}

        if not duplicates:
            self.stdout.write("  Дублікатів не знайдено.\n")
            return set()

        to_delete: set[int] = set()
        merged = fp_moved = sc_updated = 0

        for norm_label, params in sorted(duplicates.items()):
            canonical = params[0]   # найменший id = найстаріший
            others = params[1:]

            self.stdout.write(
                f"\n  [{norm_label}]\n"
                f"    Канонічний : id={canonical.id}  key={canonical.key!r}  label='{canonical.label}'\n"
                f"    Дублікати  : " +
                "  |  ".join(f"id={p.id} key={p.key!r} label='{p.label}'" for p in others)
            )

            for dup in others:
                to_delete.add(dup.id)

                for fp in FurnitureParameter.objects.filter(parameter=dup):
                    conflict = FurnitureParameter.objects.filter(
                        furniture_id=fp.furniture_id, parameter=canonical
                    ).first()
                    if conflict:
                        self.stdout.write(
                            f"      furniture_id={fp.furniture_id}: конфлікт — "
                            f"залишаємо '{conflict.value}', видаляємо '{fp.value}'"
                        )
                        if not dry_run:
                            fp.delete()
                    else:
                        self.stdout.write(
                            f"      furniture_id={fp.furniture_id}: переносимо '{fp.value}'"
                        )
                        if not dry_run:
                            fp.parameter = canonical
                            fp.save(update_fields=["parameter"])
                        fp_moved += 1

                for sc in SubCategory.objects.filter(allowed_params=dup):
                    self.stdout.write(f"      SubCategory '{sc.name}': оновлюємо allowed_params")
                    if not dry_run:
                        sc.allowed_params.remove(dup)
                        if not sc.allowed_params.filter(id=canonical.id).exists():
                            sc.allowed_params.add(canonical)
                    sc_updated += 1

                if not dry_run:
                    dup.delete()
                merged += 1

        self.stdout.write(
            f"\n  Результат: видалено {merged} дублікатів, "
            f"перенесено {fp_moved} прив'язок, оновлено {sc_updated} підкатегорій."
        )
        return to_delete

    # ------------------------------------------------------------------
    def _step2_normalize_keys(self, dry_run: bool, skip_ids: set[int]) -> None:
        self.stdout.write(self.style.HTTP_INFO("\n── Крок 2: нормалізація ключів ──"))

        ugly = Parameter.objects.filter(key__regex=r"^param_[0-9]+$").exclude(id__in=skip_ids)
        if not ugly.exists():
            self.stdout.write("  Некрасивих ключів не знайдено.")
            return

        # Ключі що вже зайняті після кроку 1 (без видалених дублікатів)
        taken_keys: set[str] = set(
            Parameter.objects.exclude(id__in=skip_ids).values_list("key", flat=True)
        )

        renamed = skipped = 0
        for param in ugly.order_by("id"):
            new_key = _slugify_label(param.label)

            if not new_key:
                self.stdout.write(
                    self.style.WARNING(f"  id={param.id} '{param.label}': slug порожній, пропускаємо")
                )
                skipped += 1
                continue

            if new_key in taken_keys and new_key != param.key:
                self.stdout.write(
                    self.style.WARNING(
                        f"  id={param.id} '{param.label}': slug '{new_key}' вже зайнятий, пропускаємо"
                    )
                )
                skipped += 1
                continue

            self.stdout.write(f"  id={param.id} '{param.label}': {param.key!r} → {new_key!r}")
            if not dry_run:
                taken_keys.discard(param.key)
                param.key = new_key
                param.save(update_fields=["key"])
                taken_keys.add(new_key)
            else:
                taken_keys.add(new_key)  # резервуємо в dry-run щоб не дублювати
            renamed += 1

        self.stdout.write(f"\n  Результат: перейменовано {renamed}, пропущено {skipped}.")
