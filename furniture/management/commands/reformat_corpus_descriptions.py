from __future__ import annotations

import re

from django.core.management.base import BaseCommand

from furniture.models import Furniture


ADVANTAGES_HEADER_RE = re.compile(
    r'^Переваги\s+'
    r'(?:комод[ауі]?|тумб[иі]|шаф[иі]?|полиц[ею]?|вішалк(?:и)?'
    r'|дзеркал[а-яіїє]*|антресол[ію]?|передпокою|стол[уа]?|виробу?|моделі?)'
    r'[^\n:.]{0,60}\s*:?\s*$'
    r'|^Переваги\s*:?\s*$',
    re.MULTILINE | re.IGNORECASE,
)

REMOVE_SECTIONS: list[re.Pattern] = [
    # LUXE STUDIO sentence: "LUXE STUDIO [—/-] це найбільший виробник...якості."
    re.compile(
        r'LUXE\s*STUDIO\s*(?:[-—–]|&mdash;)?\s*це\s+найбільший виробник.+?якост[іи]\.',
        re.DOTALL | re.IGNORECASE,
    ),
    # "Використовуючи новітні технології...інтер'єру."
    re.compile(
        r'Використовуючи новітні технології.+?інтер\'єру\.',
        re.DOTALL | re.IGNORECASE,
    ),
    # "Переваги покупки [...]" → remove to end
    re.compile(r'Переваги\s+покупки.*$', re.DOTALL | re.IGNORECASE),
    # "Купити [товар] можна в інтернет-магазині..." sentence
    re.compile(r'Купити\s+\S+[^\.]{0,100}інтернет-магазині[^\.]+\.', re.IGNORECASE),
    # "Почніть створювати свій неповторний дизайн квартири вже зараз."
    re.compile(r'Почніть створювати свій[^\.]+\.', re.IGNORECASE),
    # "X - це один з небагатьох варіантів меблів..." closing filler
    re.compile(r'[^\n]+це один з небагатьох[^\n\.]+\.?', re.IGNORECASE),
    # Characteristics blocks (incl. "та розміри", typo "Характеристка") → remove to "Переваги" or end
    re.compile(
        r'(?:Основні\s+)?Характерист\w*[^\n]*:.*?(?=\nПереваги|\Z)',
        re.DOTALL | re.IGNORECASE,
    ),
    # "Вироби виготовляються з ДСП..." → remove to end
    re.compile(r'Вироби виготовляються з ДСП.*$', re.DOTALL | re.IGNORECASE),
    # "Використані/Використовувані матеріали [в назві]" → remove to end
    re.compile(r'Використ(?:овувані|овані|ані)\s+матеріали.*$', re.DOTALL | re.IGNORECASE),
    # "Розміри (ШхГхВ): ..." dimension line (with or without brackets)
    re.compile(r'^Розміри\s*(?:\([^)]+\)\s*)?:.*?(?=\n\n|\Z)', re.DOTALL | re.MULTILINE | re.IGNORECASE),
    # Spec key-value lines: "Матеріал - ДСП ...", "Полки - 4 шт", "Корпус: ДСП ...", etc.
    re.compile(
        r'^(?:Матеріал|Полки|Орні\s+двері|Висувні\s+шухлядки|Ніжки|Ящики|Система|'
        r'Ручка|Кромка|Колір|Фасад|Корпус)\s*[-:][^\n]+$',
        re.MULTILINE | re.IGNORECASE,
    ),
    # Standalone "Матеріали:" label — remove label, keep following text
    re.compile(r'^Матеріали\s*:\s*', re.MULTILINE | re.IGNORECASE),
    # Ukrainian disclaimer
    re.compile(r'\*?\s*Виробник залишає за собою право.*$', re.DOTALL | re.IGNORECASE),
    # Russian disclaimer
    re.compile(r'\*?\s*Производитель оставляет за собой право.*$', re.DOTALL | re.IGNORECASE),
]

BRAND_SUBS: list[tuple[re.Pattern, str]] = [
    # "На фабриці/сайті MatroLuxe [sentence]."
    (re.compile(r'На\s+(?:фабриці|сайті)\s+\S*(?:Matrolux[e]?|MatroLux[e]?|Матролюкс)\S*[^\.]*\.'), ''),
    # "технологи компанії/фабрики [Brand]" → "технологи"
    (re.compile(r'технолог(?:и|ів|ам)\s+(?:компанії|фабрики)\s+\S+', re.IGNORECASE), 'технологи'),
    # "від торгової марки LuxeStudio"
    (re.compile(r'від\s+торгової\s+марки\s+(?:LUXE\s*STUDIO|LuxeStudio)', re.IGNORECASE), ''),
    # "виробництва Матролюкс/Matroluxe"
    (re.compile(r'виробництва\s+\S*(?:Matrolux[e]?|MatroLux[e]?|Матролюкс)\S*', re.IGNORECASE), ''),
    # "фабрики/компанії/виробника [Brand]"
    (re.compile(
        r'(?:фабрики|компанії|виробника)\s+\S*(?:Matrolux[e]?|MatroLux[e]?|Матролюкс|LUXE\s*STUDIO)\S*',
        re.IGNORECASE,
    ), ''),
    # "в інтернет-магазині [Brand]"
    (re.compile(r'в\s+інтернет-магазині\s+\S+', re.IGNORECASE), ''),
    # "магазину [Brand]"
    (re.compile(
        r'магазину\s+\S*(?:Matrolux[e]?|MatroLux[e]?|Матролюкс|LUXE\s*STUDIO)\S*',
        re.IGNORECASE,
    ), ''),
    # Standalone LUXE STUDIO / LuxeStudio tokens
    (re.compile(r'\bLUXE\s*STUDIO\b', re.IGNORECASE), ''),
    (re.compile(r'\bLuxeStudio\b', re.IGNORECASE), ''),
    # Matroluxe / MatroLuxe variants
    (re.compile(r'\bMatrolux[e]?\b', re.IGNORECASE), ''),
    (re.compile(r'\bMatroLux[e]?\b', re.IGNORECASE), ''),
    (re.compile(r'\bMatro\b', re.IGNORECASE), ''),
    (re.compile(r'\bМатролюкс\b'), ''),
    (re.compile(r'\bматро\b', re.IGNORECASE), ''),
    # Leftover fragments
    (re.compile(r'\s+від виробника\b', re.IGNORECASE), ''),
    (re.compile(r',?\s*які представлені\s*', re.IGNORECASE), ''),
    # Dangling preposition before uppercase Cyrillic or dash
    (re.compile(r'\s+від\s+(?=[А-ЯІЇЄ])', re.IGNORECASE), ' '),
    (re.compile(r'\s+від\s+(?=[-–—])', re.IGNORECASE), ' '),
]


def _normalize(text: str) -> str:
    text = text.replace('&mdash;', '—').replace('&nbsp;', ' ').replace('\xa0', ' ')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Remove HTML indentation (4+ leading spaces/tabs on a line)
    text = re.sub(r'\n[ \t]{4,}', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    # Insert newlines at concatenated sentence / word boundaries
    text = re.sub(r'([а-яіїє])([А-ЯІЇЄ])', r'\1\n\2', text)   # Cyrillic lower→upper
    text = re.sub(r'([A-Z0-9])([А-ЯІЇЄ])', r'\1\n\2', text)    # Latin/digit → Cyrillic upper
    text = re.sub(r'\.([А-ЯІЇЄ])', r'.\n\1', text)             # period → Cyrillic upper
    text = re.sub(r':([А-ЯІЇЄ])', r':\n\1', text)              # colon → Cyrillic upper
    text = re.sub(r' \.', '.', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _strip_title_header(text: str, furniture_name: str) -> str:
    """Remove leading 'Переваги [product name]' or repeated product name on first line."""
    first_word = furniture_name.split()[0] if furniture_name else ''

    # "Переваги [name][:][newline]" — strip the whole first line
    m = re.match(r'^Переваги[^\n]{1,120}\n', text)
    if m:
        return text[m.end():]
    # Fallback: up to first colon
    m = re.match(r'^Переваги[^:]{1,120}:\s*', text)
    if m:
        return text[m.end():]

    # Repeated name: first line is just the product name (no period), second starts uppercase
    if first_word and text.startswith(first_word):
        m = re.match(r'^[^\n.]{1,120}\n', text)
        if m:
            rest = text[m.end():]
            if rest and rest[0].isupper():
                return rest

    return text


def _split_list_items(raw: str) -> list[str]:
    # Split on '.' / ';' OR newline before Cyrillic uppercase (concatenated items without period)
    items = []
    for chunk in re.split(r'[\.;]\s*\n?|\n(?=[А-ЯІЇЄ])', raw):
        chunk = chunk.strip()
        if len(chunk) > 4:
            items.append(chunk)
    return items


def _clean_name(name: str) -> str:
    name = re.sub(r'\s*\d+[хx×]\d+(?:[хx×]\d+)?\s*(?:мм)?\s*$', '', name).strip()
    name = re.sub(r'\s*\(\d+[хx×]\d+(?:[/\d хx×]*)\)\s*$', '', name).strip()
    name = re.sub(r'\s*/\s*', ' / ', name)
    return re.sub(r'\s+', ' ', name).strip()


def format_corpus_description(raw: str, furniture_name: str) -> str:
    text = raw.strip()

    # Skip already-formatted HTML
    if text.count('<') > 2:
        return raw

    # 1. Normalize encoding, indentation, and concatenated sentences
    text = _normalize(text)

    # 2. Strip leading title header
    text = _strip_title_header(text, furniture_name)

    # 3. Remove unwanted sections
    for pattern in REMOVE_SECTIONS:
        text = pattern.sub('', text)

    # 4. Remove brand mentions
    for pattern, replacement in BRAND_SUBS:
        text = pattern.sub(replacement, text)

    text = _normalize(text)

    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    # 5. Split intro vs advantages list
    adv_match = ADVANTAGES_HEADER_RE.search(text)
    if adv_match:
        intro_raw = text[: adv_match.start()].strip()
        adv_raw = text[adv_match.end():].strip()
    else:
        intro_raw = text
        adv_raw = ''

    # 6. Build intro HTML
    paragraphs = [p.strip() for p in re.split(r'\n\n+', intro_raw) if p.strip()]
    intro_html = ''.join(f'<p>{p}</p>' for p in paragraphs) if paragraphs else ''

    # 7. Build advantages HTML
    adv_html = ''
    if adv_raw:
        items = _split_list_items(adv_raw)
        if items:
            items_html = ''.join(f'<li>{item}.</li>' for item in items)
            adv_html = f'<h3>Переваги:</h3><ul>{items_html}</ul>'

    # 8. Compose final HTML
    h2 = _clean_name(furniture_name)
    return f'<h2>{h2}</h2>{intro_html}{adv_html}'


class Command(BaseCommand):
    help = 'Переформатовує описи корпусних меблів: видаляє бренди/характеристики, додає HTML структуру.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Показати результат без збереження в БД.')
        parser.add_argument('--limit', type=int, default=None, help='Обробити лише N товарів (для тесту).')
        parser.add_argument('--verbose', action='store_true', help='Виводити HTML для кожного товару.')

    def handle(self, *args, **options):
        dry_run: bool = options['dry_run']
        limit: int | None = options['limit']
        verbose: bool = options['verbose']

        qs = (
            Furniture.objects.filter(sub_category__category__name='Корпусні меблі')
            .exclude(description='')
            .select_related('sub_category__category')
        )

        if limit:
            qs = qs[:limit]

        updated = skipped = 0
        for item in qs.iterator(chunk_size=50):
            new_desc = format_corpus_description(item.description, item.name)
            if new_desc == item.description:
                skipped += 1
                continue

            updated += 1
            if verbose:
                self.stdout.write(f"\n{'=' * 60}")
                self.stdout.write(f'ID {item.id} | {item.name}')
                self.stdout.write(new_desc)

            if not dry_run:
                item.description = new_desc
                item.save(update_fields=['description'])

        tag = 'DRY-RUN' if dry_run else 'DONE'
        self.stdout.write(self.style.SUCCESS(f'[{tag}] Оновлено: {updated}, без змін: {skipped}.'))
