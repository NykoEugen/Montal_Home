from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser

from django.core.management.base import BaseCommand, CommandError

from categories.models import Category
from furniture.models import Furniture


class _PlainTextParser(HTMLParser):
    """Extracts readable paragraphs from HTML content."""

    BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "table", "tr"}

    def __init__(self) -> None:
        super().__init__()
        self._segments: list[str] = []
        self._buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag):
        if tag in self.BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        text = data.strip()
        if text:
            self._buffer.append(text)

    def get_text(self) -> str:
        self._flush()
        return "\n\n".join(self._segments).strip()

    def _flush(self):
        if not self._buffer:
            return
        chunk = " ".join(self._buffer).strip()
        if chunk:
            self._segments.append(chunk)
        self._buffer.clear()


@dataclass
class CleanResult:
    original: str
    cleaned: str


class Command(BaseCommand):
    help = (
        "Очищає описи для категорій 'Столи' та 'Стільці': видаляє HTML-розмітку, "
        "залишає читабельний текст з абзацами."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--categories",
            nargs="+",
            default=["Столи", "Стільці"],
            help="Назви категорій, які потрібно обробити (за замовчуванням: Столи, Стільці).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати, які зміни будуть застосовані, без збереження в базу.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Обмежити кількість опрацьованих товарів (для швидкого тесту).",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Виводити очищений опис для кожного товару.",
        )

    def handle(self, *args, **options):
        category_names: list[str] = options["categories"]
        dry_run: bool = options["dry_run"]
        limit: int | None = options["limit"]
        verbose: bool = options["verbose"]

        categories = list(Category.objects.filter(name__in=category_names))
        if not categories:
            raise CommandError("Не знайдено жодної з указаних категорій.")

        category_map = {category.id: category.name for category in categories}
        furniture_qs = Furniture.objects.filter(
            sub_category__category__in=categories
        ).select_related("sub_category", "sub_category__category")

        total = furniture_qs.count()
        self.stdout.write(
            self.style.NOTICE(
                f"Знайдено {total} товарів у категоріях: {', '.join(category_map.values())}"
            )
        )

        if limit:
            furniture_qs = furniture_qs[:limit]

        updated = 0
        skipped = 0
        for furniture in furniture_qs.iterator(chunk_size=100):
            result = self._clean_description(furniture.description or "")
            if not result.cleaned or result.cleaned == result.original:
                skipped += 1
                continue

            updated += 1
            if verbose:
                self.stdout.write(
                    f"\n--- {furniture.name} ({furniture.sub_category.category.name}) ---"
                )
                self.stdout.write(result.cleaned)
                self.stdout.write("--- end ---\n")

            if not dry_run:
                furniture.description = result.cleaned
                furniture.save(update_fields=["description"])

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY-RUN: Оновлено було б {updated} описів, пропущено {skipped}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Оновлено описів: {updated}, без змін: {skipped}.")
            )

    def _clean_description(self, raw: str) -> CleanResult:
        if not raw:
            return CleanResult(raw, raw)

        text = raw.strip()
        if text.startswith("<![CDATA[") and text.endswith("]]>"):
            text = text[9:-3].strip()

        parser = _PlainTextParser()
        parser.feed(text)
        parser.close()

        cleaned = parser.get_text()
        cleaned = unescape(cleaned)
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        return CleanResult(raw, cleaned)
