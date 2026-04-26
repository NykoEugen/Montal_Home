from __future__ import annotations

import re

from django.core.management.base import BaseCommand

from furniture.models import Furniture


ADVANTAGES_HEADER_RE = re.compile(
    r'(?:'
    r'(?:Модель|Ліжко[^\n]{0,40}?)\s+має\s+(?:наступні\s+|масу\s+|такі\s+)?переваги|'
    r'Переваги моделі|'
    r'Особливості моделі|'
    r'Характеристики та переваги[^:\n]*:?|'
    r'Також\s+(?:виріб|модель)\s+має\s+такі\s+переваги|'
    r'Інші(?:\s+його)?\s+переваги(?:\s+виробу)?|'
    r'[\.!?]\s*переваги(?:\s+моделі)?'   # "...інтер'єр.переваги моделі:" — після крапки
    r')\s*:?',
    re.IGNORECASE,
)

REMOVE_SECTIONS: list[re.Pattern] = [
    # Characteristics block: remove until advantages header or end
    re.compile(
        r'Характеристики\s*:.*?'
        r'(?=Модель має|Також\s+(?:виріб|модель)|Інші\s+(?:його\s+)?переваги|Переваги моделі|Особливості моделі|$)',
        re.DOTALL | re.IGNORECASE,
    ),
    # Materials section: remove to end (Використовувані / Використовані / Використані)
    re.compile(r'Використ(?:овувані|овані|ані) матеріали.*$', re.DOTALL | re.IGNORECASE),
    # Buying / promo section: remove to end
    re.compile(r'Переваги покупки.*$', re.DOTALL | re.IGNORECASE),
    re.compile(r'Купити ліжко.*$', re.DOTALL | re.IGNORECASE),
    # Manufacturer disclaimer: remove to end
    re.compile(r'\*?\s*Виробник залишає за собою право.*$', re.DOTALL | re.IGNORECASE),
    # "Увага! Матрац в комплект не входить..." — remove sentence
    re.compile(r'Увага!\s*Матрац[^\.]+\.', re.IGNORECASE),
    # LUXE STUDIO promo block (first 2 sentences)
    re.compile(r'LUXE STUDIO.*?(?=Ліжко|Диван|Крісло|$)', re.DOTALL | re.IGNORECASE),
    # Generic "using our technology we produce..." company intro sentence
    re.compile(r'Використовуючи новітні технології[^\.]+\.', re.IGNORECASE),
    # "Детальніше про модель" section with specs
    re.compile(r'Детальніше про модель.*?(?=\n\n|Основні|$)', re.DOTALL | re.IGNORECASE),
    # "Розміри:" specs block
    re.compile(r'Розміри\s*:.*?(?=\n\n|$)', re.DOTALL | re.IGNORECASE),
    # "Основні" leftover label
    re.compile(r'^Основні\s*$', re.MULTILINE | re.IGNORECASE),
    # Leftover hardware specs line (e.g. "Люстерко. Ручка меблева...")
    re.compile(r'Люстерко\.[^\n]*', re.IGNORECASE),
    # "Підібрати ортопедичний матрац ... можна ТУТ"
    re.compile(r'Підібрати ортопедичний матрац[^\.]*\.?', re.IGNORECASE),
]

BRAND_SUBS: list[tuple[re.Pattern, str]] = [
    # "На сайті Matroluxe/Matro/etc [будь-що]." — тільки на початку речення (велика "Н")
    (
        re.compile(r'На сайті\s+\S*(?:Matrolux[e]?|Matro|Матролюкс|Матро)\S*[^\.]*\.'),
        '',
    ),
    # "Зверніть увагу на новинку від торгової марки Sofyno — "
    (
        re.compile(
            r'Зверніть увагу на новинку від\s+(?:торгової марки\s+)?'
            r'(?:Sofyno|Matrolux[e]?|Матролюкс)\s*[—–]\s*',
            re.IGNORECASE,
        ),
        '',
    ),
    # "Торгова марка Sofyno представляє до вашої уваги новинку — "
    (re.compile(r'Торгова марка\s+Sofyno\s+[^—–]+[—–]\s*', re.IGNORECASE), ''),
    # " ТМ Sofyno" / "торгової марки Sofyno" — видалити, зберегти подальший роздільник
    (re.compile(r'\s+(?:ТМ|торгової марки)\s+Sofyno', re.IGNORECASE), ''),
    # "на сайті Matro..." всередині речення
    (re.compile(r'на сайті\s+\S*(?:matro|матро|matrolux)\S*\s*', re.IGNORECASE), ''),
    # "в інтернет-магазині ..."
    (re.compile(r'в інтернет-магазині\s+\S+', re.IGNORECASE), ''),
    # Leftover "від виробника" after brand removal
    (re.compile(r'\s+від виробника\b', re.IGNORECASE), ''),
    # Leftover "які представлені" (fragment after mid-sentence brand removal)
    (re.compile(r',?\s*які представлені\s*', re.IGNORECASE), ''),
    # Standalone brand tokens
    (re.compile(r'\bMatrolux[e]?\b', re.IGNORECASE), ''),
    (re.compile(r'\bMatro\b', re.IGNORECASE), ''),
    (re.compile(r'\bSofyno\b', re.IGNORECASE), ''),
    (re.compile(r'\bМатролюкс\b'), ''),
    (re.compile(r'\bматро\b', re.IGNORECASE), ''),
    (re.compile(r'\bсофіно\b', re.IGNORECASE), ''),
]


def _strip_title_header(text: str) -> str:
    """Remove leading 'Переваги [model name][:][newline]' header."""
    # With colon + newline
    m = re.match(r'^Переваги[^\r\n:]{1,120}:\s*\r?\n', text)
    if m:
        return text[m.end():]
    # With just newline
    m = re.match(r'^Переваги[^\r\n]{1,120}\r?\n', text)
    if m:
        return text[m.end():]
    # Concatenated: detect lowercase→uppercase boundary (Cyrillic or Latin→Cyrillic)
    m = re.match(r'^Переваги\s+\S+(?:\s+\S+){0,12}?[а-яіїєa-z](?=[А-ЯІЇЄ])', text)
    if m:
        return text[m.end():]
    # Fallback: remove up to first colon
    m = re.match(r'^Переваги[^:]{1,120}:\s*', text)
    if m:
        return text[m.end():]
    return text


def _clean_whitespace(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' \.', '.', text)        # "слово ." → "слово."
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _split_list_items(raw: str) -> list[str]:
    """Split 'Item1.Item2.' or 'Item1;Item2;' into list items."""
    items = []
    for chunk in re.split(r'[\.;]\s*\n?', raw):
        chunk = chunk.strip()
        if len(chunk) > 4:
            items.append(chunk)
    return items


def _clean_name(name: str) -> str:
    """Remove dimensions and normalize slashes in furniture name."""
    name = re.sub(r'\s*\(\d+[хx×]\d+(?:[/\d хx×]*)\)\s*$', '', name).strip()
    name = re.sub(r'\s*/\s*', ' / ', name)
    return re.sub(r'\s+', ' ', name).strip()


def format_bed_description(raw: str, furniture_name: str) -> str:
    text = raw.strip()

    # Skip already-formatted HTML (more than one tag)
    if text.count('<') > 2:
        return raw

    # 1. Strip title header
    text = _strip_title_header(text)

    # 2. Remove unwanted sections
    for pattern in REMOVE_SECTIONS:
        text = pattern.sub('', text)

    # 3. Remove brand mentions
    for pattern, replacement in BRAND_SUBS:
        text = pattern.sub(replacement, text)

    text = _clean_whitespace(text)

    # Capitalize first letter after all removals
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    # 4. Split intro vs advantages list
    adv_match = ADVANTAGES_HEADER_RE.search(text)
    if adv_match:
        intro_raw = text[: adv_match.start()].strip()
        adv_raw = text[adv_match.end():].strip()
    else:
        intro_raw = text
        adv_raw = ''

    # 5. Build intro HTML
    paragraphs = [p.strip() for p in re.split(r'\n\n', intro_raw) if p.strip()]
    intro_html = ''.join(f'<p>{p}</p>' for p in paragraphs) if paragraphs else ''

    # 6. Build advantages HTML
    adv_html = ''
    if adv_raw:
        items = _split_list_items(adv_raw)
        if items:
            items_html = ''.join(f'<li>{item}.</li>' for item in items)
            adv_html = f'<h3>Переваги:</h3><ul>{items_html}</ul>'

    # 7. Compose final HTML
    h2 = _clean_name(furniture_name)
    return f'<h2>{h2}</h2>{intro_html}{adv_html}'


class Command(BaseCommand):
    help = "Переформатовує описи ліжок: видаляє бренди/характеристики, додає HTML структуру."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати результат без збереження в БД.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Обробити лише N ліжок (для тесту).",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Виводити кожен результат.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        limit: int | None = options["limit"]
        verbose: bool = options["verbose"]

        qs = (
            Furniture.objects.filter(sub_category__category__name="Ліжка")
            .exclude(description="")
            .select_related("sub_category__category")
        )

        if limit:
            qs = qs[:limit]

        updated = skipped = 0
        for bed in qs.iterator(chunk_size=50):
            new_desc = format_bed_description(bed.description, bed.name)
            if new_desc == bed.description:
                skipped += 1
                continue

            updated += 1
            if verbose:
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"ID {bed.id} | {bed.name}")
                self.stdout.write(new_desc)

            if not dry_run:
                bed.description = new_desc
                bed.save(update_fields=["description"])

        tag = "DRY-RUN" if dry_run else "DONE"
        self.stdout.write(
            self.style.SUCCESS(f"[{tag}] Оновлено: {updated}, без змін: {skipped}.")
        )
