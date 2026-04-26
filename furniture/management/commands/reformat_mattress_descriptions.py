from __future__ import annotations

import re

from django.core.management.base import BaseCommand

from furniture.models import Furniture


ADVANTAGES_HEADER_RE = re.compile(
    r'(?:'
    r'Чому варто обрати[^\n:]{0,40}:?|'
    r'(?:Модель|Матрац[^\n]{0,40}?)\s+(?:має|володіє)[^\n]{0,30}?переваг(?:и|ами)?|'
    r'(?:А\s+)?[Тт]акож\s+(?:виріб|матрац|модель)\s+має\s+(?:такі|наступні)\s+переваг(?:и|ами)?|'
    r'(?:А\s+)?[Тт]акож\s+матрац\s+має\s+(?:такі|наступні)\s+переваг(?:и|ами)?|'
    r'А\s+також\s+має\s+(?:наступні|такі)\s+переваг(?:и|ами)?|'
    r'Переваги моделі|'
    r'Інші(?:\s+його)?\s+переваг(?:и|ами)?(?:\s+виробу)?|'
    r'[\.!?]\s*переваг(?:и|ами)?(?:\s+моделі)?'
    r')\s*:?',
    re.IGNORECASE,
)

REMOVE_SECTIONS: list[re.Pattern] = [
    # Characteristics block
    re.compile(
        r'(?:Основні\s+)?Характеристики\s*:.*?'
        r'(?=Чому варто|Також\s+(?:виріб|матрац)|Інші\s+переваг(?:и|ами)?|Модель має|$)',
        re.DOTALL | re.IGNORECASE,
    ),
    # "Наповнення матрацу / матраця:" — remove to end
    re.compile(r'Наповнення матрац[яу][^\n]*:.*$', re.DOTALL | re.IGNORECASE),
    # "Матеріали та конструкція:" / "Матеріали:" / "Матеріали, що використовуються..."
    re.compile(r'Матеріали(?:\s+та\s+конструкція|,\s+що\s+використовуються[^:]*)?'
               r'\s*:.*?(?=Додаткові\s+особливості|$)',
               re.DOTALL | re.IGNORECASE),
    # "Додаткові особливості:" — remove to end of that block or next section
    re.compile(r'Додаткові\s+особливості\s*:.*?(?=\n\n|$)', re.DOTALL | re.IGNORECASE),
    # "Використовувані / Використані матеріали" — remove to end
    re.compile(r'Використ(?:овувані|овані|ані) матеріали.*$', re.DOTALL | re.IGNORECASE),
    # "Переваги покупки" — remove to end
    re.compile(r'Переваги покупки.*$', re.DOTALL | re.IGNORECASE),
    # "Купити матрац" — remove to end
    re.compile(r'Купити матрац.*$', re.DOTALL | re.IGNORECASE),
    # Shopping hints: "Ціна виробу залежить від розмірів...", "Вибрати найбільш відповідний..."
    re.compile(r'Ціна виробу залежить[^\.]*\.', re.IGNORECASE),
    re.compile(r'Вибрати найбільш відповідний[^\.]*\.', re.IGNORECASE),
    # Manufacturer disclaimer
    re.compile(r'\*?\s*Виробник залишає за собою право.*$', re.DOTALL | re.IGNORECASE),
    # Short inline specs lines: "Жорсткість – середня", "Єврокаркас", "Гарантія – X місяців"
    re.compile(
        r'\n(?:Жорсткість|Висота|Гарантія|Єврокаркас|Навантаження|Розмір|Матеріал чохла)[^\n]{0,80}',
        re.IGNORECASE,
    ),
]

BRAND_SUBS: list[tuple[re.Pattern, str]] = [
    # "На сайті Matroluxe/Matro/etc [речення]." — тільки з великої
    (re.compile(r'На сайті\s+\S*(?:Matrolux[e]?|Matro|Матролюкс|Матро)\S*[^\.]*\.'), ''),
    # "Зверніть увагу на новинку від ... Sofyno/Matroluxe —"
    (re.compile(r'Зверніть увагу на новинку від\s+(?:торгової марки\s+)?'
                r'(?:Sofyno|Matrolux[e]?|Матролюкс)\s*[—–]\s*', re.IGNORECASE), ''),
    # "від торгової марки Low Cost" / "від Matroluxe"
    (re.compile(r'від\s+(?:торгової марки\s+)?(?:Low Cost|Matrolux[e]?|Матролюкс)\s*[—–]?\s*',
                re.IGNORECASE), ''),
    # "компанії Matroluxe", "фабрики Матролюкс"
    (re.compile(r'(?:компанії|фабрики|виробника)\s+\S*(?:Matrolux[e]?|Матролюкс)\S*\s*',
                re.IGNORECASE), ''),
    # "Торгова марка Sofyno представляє..."
    (re.compile(r'Торгова марка\s+Sofyno\s+[^—–]+[—–]\s*', re.IGNORECASE), ''),
    # " ТМ Sofyno" / "торгової марки Sofyno"
    (re.compile(r'\s+(?:ТМ|торгової марки)\s+Sofyno', re.IGNORECASE), ''),
    # "на сайті Matro..." всередині речення
    (re.compile(r'на сайті\s+\S*(?:matro|матро|matrolux)\S*\s*', re.IGNORECASE), ''),
    # "в інтернет-магазині ..."
    (re.compile(r'в інтернет-магазині\s+\S+', re.IGNORECASE), ''),
    # Standalone brand tokens
    (re.compile(r'\bMatrolux[e]?\b', re.IGNORECASE), ''),
    (re.compile(r'\bMatro\b', re.IGNORECASE), ''),
    (re.compile(r'\bSofyno\b', re.IGNORECASE), ''),
    (re.compile(r'\bLow Cost\b', re.IGNORECASE), ''),
    (re.compile(r'\bМатролюкс\b'), ''),
    (re.compile(r'\bматро\b', re.IGNORECASE), ''),
    (re.compile(r'\bсофіно\b', re.IGNORECASE), ''),
    # Leftover fragments after brand removal
    (re.compile(r'\s+від виробника\b', re.IGNORECASE), ''),
    (re.compile(r',?\s*які представлені\s*', re.IGNORECASE), ''),
    # "від Це" / "від " at end of sentence (dangling preposition)
    (re.compile(r'\s+від\s+(?=[А-ЯІЇЄ])', re.IGNORECASE), ' '),
]


def _strip_title_header(text: str) -> str:
    """Remove leading 'Переваги матраца[-топпера] [назва]' or repeated-name header."""
    # "Переваги матраца/матраця[-топпера] [name]:" with colon+newline
    m = re.match(r'^Переваги\s+матрац[яа]?(?:-топпера)?[^\r\n:]{1,120}:\s*\r?\n', text)
    if m:
        return text[m.end():]
    # With just newline
    m = re.match(r'^Переваги\s+матрац[яа]?(?:-топпера)?[^\r\n]{1,120}\r?\n', text)
    if m:
        return text[m.end():]
    # Concatenated: find lowercase→uppercase Cyrillic boundary within first 150 chars
    m = re.match(r'^Переваги\s+матрац[яа]?(?:-топпера)?[^\n]{1,150}?[а-яіїєa-z](?=[А-ЯІЇЄ])', text)
    if m:
        return text[m.end():]
    # Fallback: up to first colon
    m = re.match(r'^Переваги\s+матрац[яа]?(?:-топпера)?[^:]{1,120}:\s*', text)
    if m:
        return text[m.end():]
    # "Матрац [name]\nМатрац [name] від..." — repeated name with newline
    m = re.match(r'^Матрац\s+\S+(?:/\S+)?\r?\n', text)
    if m:
        return text[m.end():]
    # "Матрац [name]Матрац" — repeated name concatenated
    m = re.match(r'^(?:Матрац\s+\S+(?:/\S+)?)(?=Матрац\s)', text)
    if m:
        return text[m.end():]
    return text


def _clean_whitespace(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' \.', '.', text)
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
    """Remove dimensions and normalize slashes in mattress name."""
    name = re.sub(r'\s*\(\d+[хx×]\d+(?:[/\d хx×]*)\)\s*$', '', name).strip()
    name = re.sub(r'\s*/\s*', ' / ', name)
    return re.sub(r'\s+', ' ', name).strip()


def format_mattress_description(raw: str, furniture_name: str) -> str:
    text = raw.strip()

    # Strip HTML wrapper if it's just a single <p>...</p>
    if re.match(r'^<p>(.*)</p>$', text, re.DOTALL):
        text = re.sub(r'^<p>|</p>$', '', text).strip()
    elif text.count('<') > 2:
        # Already rich HTML — skip
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

    # Capitalize first letter
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

    # 5. Build intro HTML — split on blank lines
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
    help = "Переформатовує описи матраців: видаляє бренди/характеристики, додає HTML структуру."

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
            help="Обробити лише N матраців (для тесту).",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Виводити HTML для кожного матраця.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        limit: int | None = options["limit"]
        verbose: bool = options["verbose"]

        qs = (
            Furniture.objects.filter(sub_category__category__name="Матраци")
            .exclude(description="")
            .select_related("sub_category__category")
        )

        if limit:
            qs = qs[:limit]

        updated = skipped = 0
        for mat in qs.iterator(chunk_size=50):
            new_desc = format_mattress_description(mat.description, mat.name)
            if new_desc == mat.description:
                skipped += 1
                continue

            updated += 1
            if verbose:
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"ID {mat.id} | {mat.name}")
                self.stdout.write(new_desc)

            if not dry_run:
                mat.description = new_desc
                mat.save(update_fields=["description"])

        tag = "DRY-RUN" if dry_run else "DONE"
        self.stdout.write(
            self.style.SUCCESS(f"[{tag}] Оновлено: {updated}, без змін: {skipped}.")
        )
