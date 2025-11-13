import hashlib
import os
import re
import uuid
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlsplit

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from categories.models import Category
from furniture.models import Furniture, FurnitureVariantImage, FurnitureSizeVariant, FurnitureImage
from params.models import FurnitureParameter, Parameter
from sub_categories.models import SubCategory

logger = logging.getLogger(__name__)


DEFAULT_CATEGORY_NAMES = (
    "Корпусні меблі",
    "Комплекти меблів",
)

DIMENSION_PARAMS = {
    "width_mm": {"source": "Ширина, мм", "key": "width_cm", "label": "Ширина (см)"},
    "height_mm": {"source": "Висота, мм", "key": "height_cm", "label": "Висота (см)"},
    "depth_mm": {"source": "Глибина, мм", "key": "depth_cm", "label": "Глибина (см)"},
}
DIMENSION_LABELS = {meta["source"] for meta in DIMENSION_PARAMS.values()}

COLOR_PARAM_NAME = "Готові кольорові рішення"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

IMAGE_CACHE_DIR = "supplier_cache"

SKIP_PARAMETER_NAMES = {"торгова марка", "готові кольорові рішення"}

TARGET_SUBCATEGORY_NAMES = [
    "Полиці",
    "Тумби",
    "Пенал",
    "Комод",
    "Столи",
    "Подіуми",
    "Шафи",
    "Ергономічні елементи",
    "Модульні системи",
]

SUBCATEGORY_KEYWORDS: List[Tuple[str, Tuple[str, ...]]] = [
    ("Подіуми", ("подіум",)),
    (
        "Шафи",
        (
            "шафа",
            "шаф ",
            "гардероб",
            "передпок",
            "прихож",
            "вітальн",
            "спальн",
            "шкаф распаш",
        ),
    ),
    ("Модульні системи", ("модульна система", "модульний", "modular system")),
    (
        "Ергономічні елементи",
        (
            "вішал",
            "вешал",
            "лавка",
            "лавочка",
            "дзеркал",
            "полка-віш",
            "полка ",
        ),
    ),
    ("Полиці", ("полиц", "антрес", "навісн", "шафа навісна", "стелаж")),
    ("Комод", ("комод",)),
    ("Тумби", ("тумб",)),
    ("Пенал", ("пенал",)),
    ("Столи", ("стіл", "стол", "столик")),
]

NAME_REPLACEMENTS = [
    ("Вешалка", "Вішалка"),
    ("вешалка", "вішалка"),
    ("Модульная система", "Модульна система"),
    ("модульная система", "модульна система"),
]

CYRILLIC_MAP = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "h",
    "ґ": "g",
    "д": "d",
    "е": "e",
    "є": "ie",
    "ж": "zh",
    "з": "z",
    "и": "y",
    "і": "i",
    "ї": "yi",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ь": "",
    "ю": "yu",
    "я": "ya",
    "ы": "y",
    "ъ": "",
    "э": "e",
    "ё": "e",
}


@dataclass
class FeedOffer:
    offer_id: str
    raw_name: str
    base_name: str
    article_code: str
    group_id: Optional[str]
    description: str
    available: bool
    category_id: str
    price: Optional[Decimal]
    old_price: Optional[Decimal]
    params: Dict[str, str]
    picture_urls: List[str]

    @property
    def color_name(self) -> Optional[str]:
        value = self.params.get(COLOR_PARAM_NAME)
        return value.strip() if value else None


def build_catalog_slug(name: Optional[str]) -> str:
    raw_slug = slugify(_transliterate(name or ""))
    return raw_slug or "furniture"


def generate_catalog_slug(name: Optional[str]) -> str:
    base_slug = build_catalog_slug(name)
    slug_candidate = base_slug
    suffix = 1

    while Furniture.objects.filter(slug=slug_candidate).exists():
        suffix += 1
        slug_candidate = f"{base_slug}-{suffix}"

    return slug_candidate


def _transliterate(value: str) -> str:
    result_chars: List[str] = []
    for ch in value:
        lower = ch.lower()
        repl = CYRILLIC_MAP.get(lower)
        if repl is None:
            result_chars.append(ch)
        else:
            result_chars.append(repl)
    return "".join(result_chars)


def _apply_name_replacements(value: str) -> str:
    result = value
    for old, new in NAME_REPLACEMENTS:
        result = result.replace(old, new)
    return result


class Command(BaseCommand):
    """
    Одноразовий імпорт меблів з постачальницького XML (Matrolux тощо).

    Логіка:
    - Беремо лише категорії "Корпусні меблі" та "Комплекти меблів"
    - Для кожної пропозиції створюємо/оновлюємо базовий запис Furniture
    - Зберігаємо параметри ширина/висота/глибина у сантиметрах
    - Додаємо варіанти кольорів у FurnitureVariantImage
    """

    help = (
        "Імпорт меблів з постачальницького XML. "
        "Скрипт очікується до одноразового запуску для створення нових товарів."
    )

    def add_arguments(self, parser) -> None:  # pragma: no cover - CLI glue
        parser.add_argument(
            "--feed-url",
            help="HTTP/HTTPS посилання на XML-фід постачальника",
        )
        parser.add_argument(
            "--feed-file",
            help="Локальний шлях до XML-файла",
        )
        parser.add_argument(
            "--categories",
            nargs="+",
            default=DEFAULT_CATEGORY_NAMES,
            help="Назви категорій, які потрібно імпортувати (збіг за текстом)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Лише показати, що буде створено, без змін у БД",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Обмежити кількість оброблених пропозицій (для тестів)",
        )
        parser.add_argument(
            "--category-map",
            action="append",
            metavar="FEED_NAME=SUBCATEGORY_NAME",
            help=(
                "Явно вкажіть до якої підкатегорії потрапляє категорія з фіда. "
                "Можна повторювати аргумент для кількох мапінгів."
            ),
        )
        parser.add_argument(
            "--category-id-map",
            action="append",
            metavar="FEED_ID=SUBCATEGORY_NAME",
            help=(
                "Жорстко прив'язати categoryId з фіда до конкретної підкатегорії. "
                "Перекриває мапінг за назвою."
            ),
        )

    def handle(self, *args, **options) -> None:  # pragma: no cover - CLI glue
        feed_url = options.get("feed_url")
        feed_file = options.get("feed_file")
        dry_run = options.get("dry_run")
        categories = tuple(options.get("categories") or DEFAULT_CATEGORY_NAMES)
        limit = options.get("limit")
        category_overrides = self._parse_category_overrides(options.get("category_map"))
        category_id_overrides = self._parse_category_id_overrides(
            options.get("category_id_map")
        )

        if not feed_url and not feed_file:
            raise CommandError("Вкажіть --feed-url або --feed-file")

        xml_data = self._load_feed_data(feed_url, feed_file)
        root = ET.fromstring(xml_data)

        self.target_subcategories = self._load_target_subcategories()
        self.subcategory_cache_by_id: Dict[int, SubCategory] = {
            subcat.id: subcat for subcat in self.target_subcategories.values()
        }

        category_lookup = self._build_category_lookup(root)
        category_targets = self._resolve_target_categories(
            category_lookup,
            categories,
            forced_ids=set(category_id_overrides.keys()),
        )
        if not category_targets:
            raise CommandError("Не знайдено жодної категорії, що відповідає заданим назвам.")

        offers = self._extract_offers(root, category_targets, limit=limit)
        if not offers:
            self.stdout.write(self.style.WARNING("Не знайдено пропозицій у заданих категоріях."))
            return
        self.stdout.write(
            f"Знайдено {len(offers)} пропозицій у {len(category_targets)} категоріях"
        )

        subcategory_map = self._map_categories_to_subcategories(
            category_targets, category_overrides, category_id_overrides
        )
        if not subcategory_map:
            self.stdout.write(
                self.style.WARNING(
                    "Не знайдено відображень через --category-map/--category-id-map. "
                    "Використаємо лише ключові слова."
                )
            )

        stats = {
            "furniture_created": 0,
            "furniture_skipped": 0,
            "variants_created": 0,
            "variants_skipped": 0,
        }

        grouped_offers: Dict[Tuple[str, str, int], List[FeedOffer]] = {}
        group_cache: Dict[str, str] = {}
        for offer in offers:
            sub_category = self._determine_subcategory(
                offer,
                group_cache=group_cache,
                category_overrides=subcategory_map,
            )
            if not sub_category:
                logger.warning(
                    "Пропозиція %s пропущена: не вдалося визначити підкатегорію (%s)",
                    offer.offer_id,
                    offer.raw_name,
                )
                continue

            self._register_subcategory(sub_category)
            key = (offer.base_name, offer.article_code, sub_category.id)
            grouped_offers.setdefault(key, []).append(offer)

        for idx, (group_key, variants) in enumerate(grouped_offers.items(), start=1):
            base_name, article_code, sub_category_id = group_key
            sub_category = self.subcategory_cache_by_id.get(sub_category_id)
            if not sub_category:
                sub_category = SubCategory.objects.get(id=sub_category_id)
                self._register_subcategory(sub_category)
            primary_offer = variants[0]
            if idx % 10 == 1 or len(grouped_offers) <= 10:
                self.stdout.write(
                    f"[{idx}/{len(grouped_offers)}] Обробка '{base_name}' "
                    f"({article_code}) — варіантів: {len(variants)}"
                )

            furniture, created = self._get_or_create_furniture(
                offer=primary_offer,
                sub_category=sub_category,
                dry_run=dry_run,
            )

            if furniture is None:
                stats["furniture_skipped"] += 1
                continue

            if created:
                stats["furniture_created"] += 1

            size_variants_created = 0
            if not dry_run:
                slash_variants = self._extract_slashed_dimensions(primary_offer)
                if slash_variants:
                    variant_count = len(slash_variants["variants"])
                    base_price = self._adjust_pricing_for_dimension_variants(
                        furniture, variant_count + 1  # include основний розмір
                    )
                    self._sync_parameters(
                        furniture,
                        primary_offer,
                        override_values=slash_variants["primary"],
                    )
                    size_variants_created = self._create_dimension_variants(
                        furniture,
                        primary_offer,
                        slash_variants["variants"],
                        base_price=base_price,
                    )
                else:
                    self._sync_parameters(furniture, primary_offer)
                self._sync_additional_parameters(furniture, primary_offer)
                self._ensure_main_image(furniture, primary_offer)
                self._sync_gallery_images(furniture, primary_offer)

            variants_created = self._sync_variants(
                furniture=furniture,
                offers=variants,
                dry_run=dry_run,
            )
            stats["variants_created"] += variants_created
            stats["variants_skipped"] += max(len(variants) - variants_created, 0)
            if size_variants_created:
                self.stdout.write(
                    f"  + створено {size_variants_created} розмірних варіантів із параметрів"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Імпорт завершено: "
                f"створено меблів={stats['furniture_created']}, "
                f"варіантів={stats['variants_created']}."
            )
        )
        if stats["furniture_skipped"] or stats["variants_skipped"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Пропущено меблів={stats['furniture_skipped']}, "
                    f"варіантів={stats['variants_skipped']}."
                )
            )

    # --- Feed helpers -------------------------------------------------

    def _load_feed_data(self, feed_url: Optional[str], feed_file: Optional[str]) -> bytes:
        if feed_file:
            path = Path(feed_file).expanduser().resolve()
            if not path.exists():
                raise CommandError(f"XML-файл {path} не знайдено")
            return path.read_bytes()

        headers = {"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8"}
        try:
            response = requests.get(feed_url, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"Не вдалося завантажити XML: {exc}") from exc
        return response.content

    def _build_category_lookup(self, root: ET.Element) -> Dict[str, str]:
        lookup: Dict[str, str] = {}
        for category_el in root.findall(".//category"):
            category_id = category_el.get("id")
            if not category_id:
                continue
            name = (category_el.text or "").strip()
            if name:
                lookup[category_id] = name
        return lookup

    def _resolve_target_categories(
        self,
        lookup: Dict[str, str],
        allowed_names: Iterable[str],
        forced_ids: Optional[Iterable[str]] = None,
    ) -> Dict[str, str]:
        normalized_allowed = {name.strip().lower() for name in allowed_names if name}
        forced_set = {str(value) for value in forced_ids or []}
        resolved: Dict[str, str] = {}
        for category_id, name in lookup.items():
            normalized_name = name.strip().lower()
            if normalized_name in normalized_allowed or category_id in forced_set:
                resolved[category_id] = name
        return resolved

    def _extract_offers(
        self,
        root: ET.Element,
        target_categories: Dict[str, str],
        limit: Optional[int] = None,
    ) -> List[FeedOffer]:
        offers: List[FeedOffer] = []
        for offer_el in root.findall(".//offer"):
            category_id = offer_el.findtext("categoryId")
            if not category_id or category_id not in target_categories:
                continue

            offer = self._parse_offer_element(offer_el, category_id)
            if not offer or not offer.price:
                continue

            offers.append(offer)
            if limit and len(offers) >= limit:
                break
        return offers

    def _parse_offer_element(self, offer_el: ET.Element, category_id: str) -> Optional[FeedOffer]:
        offer_id = offer_el.get("id") or str(uuid.uuid4())
        name = _apply_name_replacements((offer_el.findtext("name") or "").strip())
        model = (offer_el.findtext("model") or "").strip()
        group_id = offer_el.get("group_id")
        price = self._parse_decimal(offer_el.findtext("price"))
        old_price = self._parse_decimal(offer_el.findtext("oldprice"))
        description = (offer_el.findtext("description") or "").strip()
        available = (offer_el.get("available") or "true").lower() == "true"

        params: Dict[str, str] = {}
        for param_el in offer_el.findall("param"):
            param_name = (param_el.get("name") or "").strip()
            if not param_name:
                continue
            params[param_name] = (param_el.text or "").strip()

        picture_urls = [pic.text.strip() for pic in offer_el.findall("picture") if pic.text]

        base_name = self._extract_base_name(name)
        article_code = self._extract_article_code(model)

        if not base_name or not article_code:
            logger.warning(
                "Пропозиція %s пропущена: відсутня назва або артикул (name=%s, model=%s)",
                offer_id,
                name,
                model,
            )
            return None

        return FeedOffer(
            offer_id=offer_id,
            raw_name=name,
            base_name=base_name,
            article_code=article_code,
            group_id=group_id,
            description=description,
            available=available,
            category_id=category_id,
            price=price,
            old_price=old_price,
            params=params,
            picture_urls=picture_urls,
        )

    @staticmethod
    def _extract_base_name(raw_name: str) -> str:
        if not raw_name:
            return ""
        return _apply_name_replacements(raw_name.split(",")[0].strip())

    @staticmethod
    def _extract_article_code(raw_model: str) -> str:
        if not raw_model:
            return ""
        return raw_model.split(",")[0].strip()

    @staticmethod
    def _parse_decimal(value: Optional[str]) -> Optional[Decimal]:
        if not value:
            return None
        cleaned = re.sub(r"[^0-9,.-]", "", value)
        if not cleaned:
            return None
        if cleaned.count(",") == 1 and cleaned.count(".") == 0:
            cleaned = cleaned.replace(",", ".")
        elif cleaned.count(",") > 0 and cleaned.count(".") > 0:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    # --- DB helpers -------------------------------------------------

    def _parse_category_overrides(self, raw_values: Optional[List[str]]) -> Dict[str, str]:
        overrides: Dict[str, str] = {}
        if not raw_values:
            return overrides
        for raw in raw_values:
            if not raw or "=" not in raw:
                continue
            feed_name, subcategory_name = raw.split("=", 1)
            feed_name = feed_name.strip().lower()
            subcategory_name = subcategory_name.strip()
            if feed_name and subcategory_name:
                overrides[feed_name] = subcategory_name
        return overrides

    def _parse_category_id_overrides(self, raw_values: Optional[List[str]]) -> Dict[str, str]:
        overrides: Dict[str, str] = {}
        if not raw_values:
            return overrides
        for raw in raw_values:
            if not raw or "=" not in raw:
                continue
            feed_id, subcategory_name = raw.split("=", 1)
            feed_id = feed_id.strip()
            subcategory_name = subcategory_name.strip()
            if feed_id and subcategory_name:
                overrides[feed_id] = subcategory_name
        return overrides

    def _resolve_subcategory_target(self, target: str) -> Optional[SubCategory]:
        target = (target or "").strip()
        if not target:
            return None
        if target.startswith("id:"):
            try:
                pk = int(target[3:])
            except ValueError:
                return None
            return SubCategory.objects.filter(pk=pk).first()
        if target.startswith("slug:"):
            slug_value = target[5:].strip()
            if not slug_value:
                return None
            return SubCategory.objects.filter(slug__iexact=slug_value).first()
        # Default to name-based lookup
        sub_category = SubCategory.objects.filter(name__iexact=target).first()
        if not sub_category:
            sub_category = SubCategory.objects.filter(name__icontains=target).first()
        if not sub_category:
            sub_category = SubCategory.objects.filter(category__name__iexact=target).first()
        return sub_category

    def _map_categories_to_subcategories(
        self,
        category_map: Dict[str, str],
        overrides_by_name: Dict[str, str],
        overrides_by_id: Dict[str, str],
    ) -> Dict[str, SubCategory]:
        resolved: Dict[str, SubCategory] = {}
        for category_id, category_name in category_map.items():
            override_target = overrides_by_id.get(category_id)
            if not override_target:
                override_target = overrides_by_name.get(category_name.lower())
            sub_category = None
            if override_target:
                sub_category = self._resolve_subcategory_target(override_target)
            if sub_category:
                resolved[category_id] = sub_category
        return resolved

    def _load_target_subcategories(self) -> Dict[str, SubCategory]:
        category = Category.objects.filter(name__iexact="Корпусні меблі").first()
        if not category:
            raise CommandError("Категорію 'Корпусні меблі' не знайдено.")

        subcategories = SubCategory.objects.filter(
            category=category, name__in=TARGET_SUBCATEGORY_NAMES
        )
        mapping = {subcat.name: subcat for subcat in subcategories}
        missing = [name for name in TARGET_SUBCATEGORY_NAMES if name not in mapping]
        if missing:
            raise CommandError(
                f"Не знайдено підкатегорії: {', '.join(missing)}. "
                "Запустіть команду ensure_corpus_subcategories."
            )
        return mapping

    def _register_subcategory(self, sub_category: SubCategory) -> None:
        if sub_category.id not in self.subcategory_cache_by_id:
            self.subcategory_cache_by_id[sub_category.id] = sub_category

    def _determine_subcategory(
        self,
        offer: FeedOffer,
        group_cache: Dict[str, str],
        category_overrides: Dict[str, SubCategory],
    ) -> Optional[SubCategory]:
        name_lower = offer.raw_name.lower()
        matched_name = self._match_subcategory_keyword(name_lower)
        if matched_name:
            sub_category = self.target_subcategories.get(matched_name)
            if sub_category:
                if offer.group_id:
                    group_cache[offer.group_id] = matched_name
                return sub_category

        if offer.group_id:
            cached_name = group_cache.get(offer.group_id)
            if cached_name:
                sub_category = self.target_subcategories.get(cached_name)
                if sub_category:
                    return sub_category

        mapped = category_overrides.get(offer.category_id)
        if mapped:
            return mapped

        return None

    def _match_subcategory_keyword(self, name_lower: str) -> Optional[str]:
        for subcat_name, keywords in SUBCATEGORY_KEYWORDS:
            if any(keyword in name_lower for keyword in keywords):
                return subcat_name
        return None

    def _get_or_create_furniture(
        self,
        offer: FeedOffer,
        sub_category: SubCategory,
        dry_run: bool = False,
    ) -> Tuple[Optional[Furniture], bool]:
        existing = Furniture.objects.filter(article_code=offer.article_code).first()
        if existing:
            self.stdout.write(
                f"Скипнуто існуючий товар '{existing.name}' ({existing.article_code})"
            )
            return existing, False

        base_price, promo_price, is_promotional = self._resolve_prices(offer)

        if dry_run:
            self.stdout.write(
                f"[DRY-RUN] Створив би меблі '{offer.base_name}' ({offer.article_code}) "
                f"у підкатегорії '{sub_category.name}'"
            )
            dry_slug = generate_catalog_slug(offer.base_name)
            furniture = Furniture(
                name=offer.base_name,
                article_code=offer.article_code,
                stock_status="in_stock" if offer.available else "on_order",
                sub_category=sub_category,
                price=base_price or Decimal("0"),
                promotional_price=promo_price,
                is_promotional=is_promotional,
                description=offer.description,
            )
            furniture.slug = dry_slug
            furniture._state.adding = True  # type: ignore[attr-defined]
            return furniture, True

        furniture = Furniture.objects.create(
            name=offer.base_name,
            article_code=offer.article_code,
            stock_status="in_stock" if offer.available else "on_order",
            sub_category=sub_category,
            price=base_price or Decimal("0"),
            promotional_price=promo_price,
            is_promotional=is_promotional,
            description=offer.description,
            slug=generate_catalog_slug(offer.base_name),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Додано '{furniture.name}' (article={furniture.article_code}, slug={furniture.slug})"
            )
        )
        return furniture, True

    @staticmethod
    def _resolve_prices(offer: FeedOffer) -> Tuple[Optional[Decimal], Optional[Decimal], bool]:
        base_price = offer.old_price or offer.price
        promo_price = offer.price if offer.old_price else None
        is_promotional = promo_price is not None and base_price is not None
        return base_price, promo_price, is_promotional

    def _sync_parameters(
        self,
        furniture: Furniture,
        offer: FeedOffer,
        override_values: Optional[Dict[str, str]] = None,
    ) -> None:
        for key, metadata in DIMENSION_PARAMS.items():
            if override_values and key in override_values:
                cm_value = override_values[key]
            else:
                raw_value = offer.params.get(metadata["source"])
                cm_value = self._convert_mm_to_cm(raw_value)
            if not cm_value:
                continue
            parameter = self._get_or_create_parameter(metadata["key"], metadata["label"])
            sub_category = furniture.sub_category
            if parameter not in sub_category.allowed_params.all():
                sub_category.allowed_params.add(parameter)
            FurnitureParameter.objects.update_or_create(
                furniture=furniture,
                parameter=parameter,
                defaults={"value": cm_value},
            )

    def _sync_additional_parameters(self, furniture: Furniture, offer: FeedOffer) -> None:
        sub_category = furniture.sub_category
        for param_name, value in offer.params.items():
            if not value:
                continue
            clean_name = (param_name or "").strip()
            if not clean_name:
                continue
            name_lower = clean_name.lower()
            if name_lower in SKIP_PARAMETER_NAMES:
                continue
            if clean_name in DIMENSION_LABELS:
                continue

            parameter = self._get_or_create_generic_parameter(clean_name)
            if parameter not in sub_category.allowed_params.all():
                sub_category.allowed_params.add(parameter)

            FurnitureParameter.objects.update_or_create(
                furniture=furniture,
                parameter=parameter,
                defaults={"value": _apply_name_replacements(value.strip())},
            )

    def _ensure_main_image(self, furniture: Furniture, offer: FeedOffer) -> None:
        if furniture.image or not offer.picture_urls:
            return
        cache_path = self._download_or_get_cached_image(offer.picture_urls[0])
        if not cache_path:
            return
        furniture.image.name = cache_path
        furniture.save(update_fields=["image"])

    def _sync_gallery_images(self, furniture: Furniture, offer: FeedOffer) -> None:
        if not offer.picture_urls or len(offer.picture_urls) <= 1:
            return

        start_position = furniture.images.count()
        for idx, url in enumerate(offer.picture_urls[1:], start=1):
            cache_path = self._download_or_get_cached_image(url)
            if not cache_path:
                continue
            gallery_image = FurnitureImage(
                furniture=furniture,
                alt_text=f"{furniture.name} — фото {start_position + idx}",
                position=start_position + idx,
            )
            gallery_image.image.name = cache_path
            gallery_image.save()

    def _sync_variants(
        self,
        furniture: Furniture,
        offers: List[FeedOffer],
        dry_run: bool = False,
    ) -> int:
        created = 0
        for index, offer in enumerate(offers):
            color_name = offer.color_name or ("Колір " + str(index + 1))
            defaults = {
                "stock_status": "in_stock" if offer.available else "on_order",
                "is_default": index == 0,
                "position": index,
            }

            if dry_run:
                self.stdout.write(
                    f"[DRY-RUN] Додав би варіант '{color_name}' для "
                    f"{furniture.article_code}"
                )
                created += 1
                continue

            variant, was_created = FurnitureVariantImage.objects.get_or_create(
                furniture=furniture,
                name=color_name,
                defaults=defaults,
            )
            if not was_created:
                continue

            created += 1
            if offer.picture_urls:
                cache_path = self._download_or_get_cached_image(offer.picture_urls[0])
                if cache_path:
                    variant.image.name = cache_path
                    variant.save(update_fields=["image"])
            if index == 0 and not furniture.image and variant.image:
                furniture.image.name = variant.image.name
                furniture.save(update_fields=["image"])
        return created

    def _convert_mm_to_cm(self, raw_value: Optional[str]) -> Optional[str]:
        if not raw_value:
            return None
        cleaned = raw_value.replace(",", ".").strip()
        cleaned = re.sub(r"[^\d.]", "", cleaned)
        if not cleaned:
            return None
        try:
            value = Decimal(cleaned)
        except InvalidOperation:
            return None
        cm_value = value / Decimal("10")
        normalized = format(cm_value.normalize(), "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        return normalized

    def _get_or_create_parameter(self, key: str, label: str) -> Parameter:
        parameter, _ = Parameter.objects.get_or_create(key=key, defaults={"label": label})
        if parameter.label != label:
            parameter.label = label
            parameter.save(update_fields=["label"])
        return parameter

    def _extract_slashed_dimensions(self, offer: FeedOffer) -> Optional[Dict[str, Dict]]:
        parsed_values: Dict[str, List[str]] = {}
        has_slashed = False

        for key, metadata in DIMENSION_PARAMS.items():
            raw_value = offer.params.get(metadata["source"])
            if not raw_value or "/" not in raw_value:
                continue
            parts = [part.strip() for part in raw_value.split("/") if part.strip()]
            if len(parts) < 2:
                continue
            parsed_values[key] = parts
            has_slashed = True

        if not has_slashed:
            return None

        primary: Dict[str, str] = {}
        variants: List[Dict[str, str]] = []

        widest_list = max((len(values) for values in parsed_values.values()), default=0)

        for key, values in parsed_values.items():
            first_value = self._convert_mm_to_cm(values[0])
            if first_value:
                primary[key] = first_value

        for idx in range(1, widest_list):
            variant_entry: Dict[str, str] = {}
            for key, values in parsed_values.items():
                if idx >= len(values):
                    continue
                cm_value = self._convert_mm_to_cm(values[idx])
                if cm_value:
                    variant_entry[key] = cm_value
            if variant_entry:
                variants.append(variant_entry)

        if not primary:
            return None

        return {"primary": primary, "variants": variants}

    def _adjust_pricing_for_dimension_variants(
        self,
        furniture: Furniture,
        variant_count: int,
    ) -> Optional[Decimal]:
        """
        Якщо є рівно два розмірних варіанти і присутня акційна ціна –
        оновлюємо базову (оригінальну) ціну до promo + 10%.
        Якщо стара ціна вже більша, залишаємо її.
        Якщо акційної немає, нічого не змінюємо.
        """
        if variant_count != 2:
            return furniture.price

        reference = furniture.promotional_price
        if not reference or reference <= 0:
            return furniture.price

        candidate = (Decimal(reference) * Decimal("1.10")).quantize(Decimal("0.01"))
        original_price = max(candidate, furniture.price or Decimal("0"))

        furniture.price = original_price
        furniture.promotional_price = None
        furniture.is_promotional = False
        furniture.save(update_fields=["price", "promotional_price", "is_promotional"])
        return original_price

    def _create_dimension_variants(
        self,
        furniture: Furniture,
        offer: FeedOffer,
        variant_dimensions: List[Dict[str, str]],
        base_price: Optional[Decimal],
    ) -> int:
        if not variant_dimensions:
            return 0

        width_param = DIMENSION_PARAMS["width_mm"]["key"]
        height_param = DIMENSION_PARAMS["height_mm"]["key"]
        depth_param = DIMENSION_PARAMS["depth_mm"]["key"]

        base_width = self._get_parameter_value(furniture, width_param)
        base_height = self._get_parameter_value(furniture, height_param)
        base_depth = self._get_parameter_value(furniture, depth_param)

        total_variants = len(variant_dimensions) + 1
        base_reference = base_price or furniture.price or Decimal("0")
        if base_reference <= 0:
            base_reference = Decimal("0")
        flat_thirty = total_variants == 2

        created = 0
        for position, dimensions in enumerate(variant_dimensions, start=1):
            width = dimensions.get("width_mm") or base_width
            height = dimensions.get("height_mm") or base_height
            depth = dimensions.get("depth_mm") or base_depth

            if not width or not height or not depth:
                continue

            if flat_thirty:
                variant_price = (
                    (base_reference * Decimal("1.30")).quantize(Decimal("0.01"))
                    if base_reference > 0
                    else Decimal("0")
                )
            else:
                multiplier = Decimal("1.0") + (Decimal("0.10") * Decimal(position))
                variant_price = (
                    (base_reference * multiplier).quantize(Decimal("0.01"))
                    if base_reference > 0
                    else Decimal("0")
                )

            created += self._create_size_variant(
                furniture=furniture,
                width=width,
                height=height,
                depth=depth,
                offer=offer,
                variant_price=variant_price,
            )
        return created

    def _get_parameter_value(self, furniture: Furniture, key: str) -> Optional[str]:
        parameter = Parameter.objects.filter(key=key).first()
        if not parameter:
            return None
        record = FurnitureParameter.objects.filter(
            furniture=furniture, parameter=parameter
        ).first()
        if not record:
            return None
        return record.value

    def _create_size_variant(
        self,
        furniture: Furniture,
        width: str,
        height: str,
        depth: str,
        offer: FeedOffer,
        variant_price: Decimal,
    ) -> int:

        try:
            width_val = Decimal(width)
            height_val = Decimal(height)
            depth_val = Decimal(depth)
        except InvalidOperation:
            return 0

        length_val = depth_val
        effective_price = variant_price if variant_price > 0 else furniture.price or Decimal("0")

        variant, created = FurnitureSizeVariant.objects.get_or_create(
            furniture=furniture,
            width=width_val,
            height=height_val,
            length=length_val,
            defaults={
                "price": effective_price,
                "is_foldable": False,
                "is_promotional": furniture.is_promotional,
            },
        )
        if not created and variant.price != effective_price:
            variant.price = effective_price
            variant.save(update_fields=["price"])
        return 1 if created else 0

    def _get_or_create_generic_parameter(self, label: str) -> Parameter:
        key = self._parameter_key_from_name(label)
        parameter, created = Parameter.objects.get_or_create(key=key, defaults={"label": label})
        if not created and parameter.label != label:
            parameter.label = label
            parameter.save(update_fields=["label"])
        return parameter

    def _parameter_key_from_name(self, label: str) -> str:
        base = slugify(label)
        if base:
            return base[:100]
        return f"param_{abs(hash(label))}"

    def _fetch_image(self, url: str) -> Optional[ContentFile]:
        if not url:
            return None
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "image/*,*/*;q=0.8",
            "Referer": url,
        }
        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Не вдалося завантажити зображення %s: %s", url, exc)
            return None
        return ContentFile(response.content)

    def _download_or_get_cached_image(self, url: str) -> Optional[str]:
        if not url:
            return None
        cache_path = self._build_cache_path(url)
        if default_storage.exists(cache_path):
            return cache_path
        image_content = self._fetch_image(url)
        if not image_content:
            return None
        default_storage.save(cache_path, image_content)
        return cache_path

    def _build_cache_path(self, url: str) -> str:
        parsed = urlsplit(url)
        base = os.path.basename(parsed.path)
        ext = os.path.splitext(base)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return f"{IMAGE_CACHE_DIR}/{digest}{ext}"
