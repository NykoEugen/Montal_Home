from __future__ import annotations

import re
from dataclasses import dataclass, field

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from furniture.models import Furniture
from params.models import FurnitureParameter, Parameter

# ---------------------------------------------------------------------------
# Normalization (same as reformat_corpus_descriptions._normalize)
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    text = text.replace('&mdash;', '—').replace('&nbsp;', ' ').replace('\xa0', ' ')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n[ \t]{4,}', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'([а-яіїє])([А-ЯІЇЄ])', r'\1\n\2', text)
    text = re.sub(r'([A-Z0-9])([А-ЯІЇЄ])', r'\1\n\2', text)
    text = re.sub(r'\.([А-ЯІЇЄ])', r'.\n\1', text)
    text = re.sub(r':([А-ЯІЇЄ])', r':\n\1', text)
    text = re.sub(r' \.', '.', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Dimension patterns
# ---------------------------------------------------------------------------

# "Розміри (ШхГхВ): 800х350х1100"  or  "Розмір (ШхГхВ) – 1212х460х834"
# Order: Width × Depth × Height
_DIM_WDH_RE = re.compile(
    r'Розмір[и]?\s*\(?Ш\s*[хx×]\s*Г\s*[хx×]\s*В\)?\s*[:\s,]*[-–]?\s*'
    r'(\d+)\s*[хx×]\s*(\d+)\s*[хx×]\s*(\d+)',
    re.IGNORECASE,
)

# "Розміри Ш х В х Г, мм : 1490х1940х350" (стелажі)
# Order: Width × Height × Depth
_DIM_WHD_RE = re.compile(
    r'Розмір[и]?\s*\(?Ш\s*[хx×]\s*В\s*[хx×]\s*Г\)?\s*[,:\s]*(?:мм)?\s*[-–:]\s*'
    r'(\d+)\s*[хx×]\s*(\d+)\s*[хx×]\s*(\d+)',
    re.IGNORECASE,
)

# "Розміри, мм: 1200 х 275 х 1210" — unlabeled triple, assume ШхГхВ
_DIM_MM_RE = re.compile(
    r'Розмір[и]?\s*,\s*мм\s*:\s*'
    r'(\d+)\s*[хx×\s]\s*(\d+)\s*[хx×\s]\s*(\d+)',
    re.IGNORECASE,
)

# Individual dimension lines:  "Висота: 796 мм"  "Ширина 1321 мм"
_HEIGHT_RE = re.compile(r'(?:^|\n)Висота\s*[:\s]\s*(\d+)\s*мм', re.IGNORECASE | re.MULTILINE)
_WIDTH_RE  = re.compile(r'(?:^|\n)Ширина\s*[:\s]\s*(\d+)\s*мм',  re.IGNORECASE | re.MULTILINE)
_DEPTH_RE  = re.compile(r'(?:^|\n)Глибина\s*[:\s]\s*(\d+)\s*мм', re.IGNORECASE | re.MULTILINE)

# Inline: "розміри (висота 750 мм, ширина 600 мм, глибина 540 мм)"
_INLINE_H_RE = re.compile(r'висота\s+(\d+)\s*мм',  re.IGNORECASE)
_INLINE_W_RE = re.compile(r'ширина\s+(\d+)\s*мм',  re.IGNORECASE)
_INLINE_D_RE = re.compile(r'глибина\s+(\d+)\s*мм', re.IGNORECASE)

# ---------------------------------------------------------------------------
# Material pattern
# ---------------------------------------------------------------------------

# "Матеріал - ДСП ламінована, 16 мм"  "Корпус: ДСП дуб сонома"
_MATERIAL_RE = re.compile(
    r'(?:^|\n)(?:Матеріал[и]?|Корпус)\s*[-–:]\s*([^\n,\(]{3,80})',
    re.IGNORECASE | re.MULTILINE,
)

# Accept only values that start with a material name, not a sentence about the product
_MATERIAL_VALID_START = re.compile(
    r'^(?:ДСП|МДФ|Метал|Дерево|Пластик|Скло|Висок|Якісн|ламінован)',
    re.IGNORECASE,
)

_SKIP_MATERIAL = re.compile(r'на вибір|колір', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Extraction logic
# ---------------------------------------------------------------------------

def _mm_to_cm(mm: int) -> str:
    cm = mm / 10
    return str(int(cm)) if cm == int(cm) else f'{cm:.1f}'


@dataclass
class Extracted:
    width: str | None = None
    height: str | None = None
    depth: str | None = None
    material_korpusa: str | None = None
    ambiguous_dims: bool = field(default=False, repr=False)


def extract_parameters(raw: str) -> Extracted:
    text = _normalize(raw)
    result = Extracted()

    # --- Dimensions ---
    # Try labeled triples first (most reliable)
    wdh_matches = _DIM_WDH_RE.findall(text)
    whd_matches = _DIM_WHD_RE.findall(text)
    mm_matches  = _DIM_MM_RE.findall(text)

    triple_matches = wdh_matches + whd_matches + mm_matches
    unique_triples = list(dict.fromkeys(triple_matches))  # preserve order, deduplicate

    if len(unique_triples) == 1:
        w, d_or_h, h_or_d = (int(v) for v in unique_triples[0])
        if wdh_matches or mm_matches:
            result.width, result.depth, result.height = (
                _mm_to_cm(w), _mm_to_cm(d_or_h), _mm_to_cm(h_or_d)
            )
        else:
            # WHD order
            result.width, result.height, result.depth = (
                _mm_to_cm(w), _mm_to_cm(d_or_h), _mm_to_cm(h_or_d)
            )
    elif len(unique_triples) > 1:
        result.ambiguous_dims = True

    # If no labeled triple, try individual lines or inline mentions
    if result.width is None and not result.ambiguous_dims:
        h_m = _HEIGHT_RE.search(text) or _INLINE_H_RE.search(text)
        w_m = _WIDTH_RE.search(text)  or _INLINE_W_RE.search(text)
        d_m = _DEPTH_RE.search(text)  or _INLINE_D_RE.search(text)

        # Only use if all three present and there is exactly one match each
        h_all = _HEIGHT_RE.findall(text) + _INLINE_H_RE.findall(text)
        w_all = _WIDTH_RE.findall(text)  + _INLINE_W_RE.findall(text)
        d_all = _DEPTH_RE.findall(text)  + _INLINE_D_RE.findall(text)

        if h_m and w_m and d_m and len(set(h_all)) == 1 and len(set(w_all)) == 1 and len(set(d_all)) == 1:
            result.height = _mm_to_cm(int(h_all[0]))
            result.width  = _mm_to_cm(int(w_all[0]))
            result.depth  = _mm_to_cm(int(d_all[0]))

    # --- Material ---
    mat_matches = _MATERIAL_RE.findall(text)
    for raw_val in mat_matches:
        value = raw_val.strip().rstrip(',').strip()
        if (
            len(value) >= 3
            and not _SKIP_MATERIAL.search(value)
            and _MATERIAL_VALID_START.match(value)
        ):
            result.material_korpusa = value[:100]
            break

    return result


# ---------------------------------------------------------------------------
# Parameter key → label map for the parameters we insert
# ---------------------------------------------------------------------------

PARAM_KEYS = ('width', 'height', 'depth', 'material_korpusa')


class Command(BaseCommand):
    help = 'Витягує параметри (розміри, матеріал) з описів корпусних меблів і зберігає в FurnitureParameter.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run',  action='store_true', help='Показати без збереження.')
        parser.add_argument('--limit',    type=int, default=None, help='Обробити лише N товарів.')
        parser.add_argument('--verbose',  action='store_true', help='Детальний вивід по кожному товару.')
        parser.add_argument(
            '--skip-existing', action='store_true', default=True,
            help='Пропускати параметри, які вже є у товару (за замовчуванням увімкнено).',
        )
        parser.add_argument(
            '--overwrite', action='store_true',
            help='Перезаписувати існуючі параметри (небезпечно — краще не використовувати).',
        )

    def handle(self, *args, **options):
        dry_run:  bool     = options['dry_run']
        limit:    int|None = options['limit']
        verbose:  bool     = options['verbose']
        overwrite: bool    = options['overwrite']

        # Load Parameter objects once
        params: dict[str, Parameter] = {}
        for key in PARAM_KEYS:
            try:
                params[key] = Parameter.objects.get(key=key)
            except Parameter.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Parameter key={key!r} не знайдено в БД — пропускається.'))

        qs = (
            Furniture.objects.filter(sub_category__category__name='Корпусні меблі')
            .exclude(description='')
            .prefetch_related('parameters__parameter')
        )
        if limit:
            qs = qs[:limit]

        created = skipped_existing = skipped_no_data = ambiguous = 0

        for item in qs.iterator(chunk_size=50):
            extracted = extract_parameters(item.description)

            # Build existing param keys for this item
            existing_keys = {fp.parameter.key for fp in item.parameters.all()}

            to_insert: list[tuple[str, str]] = []  # (key, value)

            for attr, key in [('width', 'width'), ('height', 'height'), ('depth', 'depth'),
                               ('material_korpusa', 'material_korpusa')]:
                value = getattr(extracted, attr)
                if value is None:
                    continue
                param = params.get(key)
                if param is None:
                    continue
                if key in existing_keys and not overwrite:
                    skipped_existing += 1
                    continue
                to_insert.append((key, value))

            if extracted.ambiguous_dims:
                ambiguous += 1

            if not to_insert:
                skipped_no_data += 1
                continue

            if verbose:
                self.stdout.write(f"\n{'=' * 60}")
                self.stdout.write(f'ID {item.id} | {item.name}')
                if extracted.ambiguous_dims:
                    self.stdout.write(self.style.WARNING('  [ambiguous dims — skipped]'))
                for key, value in to_insert:
                    label = params[key].label
                    self.stdout.write(f'  {label}: {value}')

            if dry_run:
                created += len(to_insert)
            else:
                for key, value in to_insert:
                    param = params[key]
                    if overwrite:
                        FurnitureParameter.objects.update_or_create(
                            furniture=item, parameter=param,
                            defaults={'value': value},
                        )
                        created += 1
                    else:
                        try:
                            FurnitureParameter.objects.create(
                                furniture=item, parameter=param, value=value,
                            )
                            created += 1
                        except IntegrityError:
                            skipped_existing += 1

        tag = 'DRY-RUN' if dry_run else 'DONE'
        self.stdout.write(self.style.SUCCESS(
            f'[{tag}] Створено: {created}, '
            f'пропущено (вже є): {skipped_existing}, '
            f'без даних: {skipped_no_data}, '
            f'неоднозначних розмірів: {ambiguous}.'
        ))
