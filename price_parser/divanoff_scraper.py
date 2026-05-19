import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

import openpyxl
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify

logger = logging.getLogger(__name__)

BASE_URL = "https://divanoff.ua"
CATALOG_URL = f"{BASE_URL}/divany"
MAX_PAGES = 2
REQUEST_DELAY = 0.8
IMAGE_CACHE_DIR = "supplier_cache/divanoff"
# 0-indexed columns C–J = Category 0 (cheapest) through Category VII
FABRIC_COLS = list(range(2, 10))
PRICE_COL = FABRIC_COLS[0]  # default: Category 0
FABRIC_CATEGORY_LABELS = [
    "Категорія 0", "Категорія I", "Категорія II", "Категорія III",
    "Категорія IV", "Категорія V", "Категорія VI", "Категорія VII",
]
# Fuzzy match threshold for name matching (0..1)
MATCH_THRESHOLD = 0.92

# For slug generation (standard Ukrainian transliteration)
CYRILLIC_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e",
    "є": "ie", "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "yi", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ь": "", "ю": "yu", "я": "ya",
    "ы": "y", "э": "e", "ъ": "",
}

# For matching — и and і both → "i" to handle Ukrainian/Russian spelling variants
_MATCH_CYRILLIC_MAP = {**CYRILLIC_MAP, "и": "i", "і": "i", "ї": "i"}

# Latin model-name words → Cyrillic canonical (applied before transliteration)
_LATIN_TO_NORM = {
    "modo": "модо",
    "coin": "коін",
    "rolf": "рольф",
    "rif": "риф",
    "leon": "леон",
    "cliff": "кліф",
    "lite": "лайт",
    "tahta": "тахта",
    "wood": "вуд",
    "nord": "норд",
}

# Word-level synonyms applied on both sides before comparison
_WORD_SYNONYMS = {
    "угловой": "кут",
    "угол": "кут",
    "кутовий": "кут",
    "mini": "міні",
    "lite": "лайт",
    "wood": "вуд",
    "tahta": "тахта",
    "оксамит": "бархат",
    "плюс": "plus",
    "биатрис": "беатрис",   # Ukrainian/Russian spelling variant
    "нью": "",
    "new": "",
    "вставка": "",
    "система": "",
    "модульна": "",
    "модульная": "",
}

# Only pure-type words stripped before matching (shape/size words kept)
_STOPWORDS = frozenset({"диван", "кресло", "крісло"})

# Specs to import from product page
_TARGET_SPECS = frozenset({
    "Длина спального места, см",
    "Ширина спального места, см",
})

SUBCATEGORY_CONFIG = {
    "slug": "divany-divanoff",
    "name": "Дивани (Divanoff)",
    "category_name": "М'які меблі",
}


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class PriceRow:
    raw_name: str
    base_name: str       # name with size number stripped
    size_label: str      # size number extracted (e.g. "160"), or ""
    norm_key: str        # normalised key for matching
    price: Decimal
    all_prices: List[Optional[Decimal]] = field(default_factory=list)  # Category 0–VII


@dataclass
class DivanoffProduct:
    url: str
    name: str
    site_article: str    # DV00230 from page
    description: str = ""
    sleep_length: str = ""
    sleep_width: str = ""
    image_urls: List[str] = field(default_factory=list)


# ── Normalisation helpers ─────────────────────────────────────────────────────

def _transliterate(text: str, cmap: dict = None, dzh_as_j: bool = True) -> str:
    if cmap is None:
        cmap = CYRILLIC_MAP
    result = []
    chars = list(text.lower())
    i = 0
    while i < len(chars):
        if dzh_as_j and i + 1 < len(chars) and chars[i] == "д" and chars[i + 1] == "ж":
            result.append("j")
            i += 2
        else:
            result.append(cmap.get(chars[i], chars[i]))
            i += 1
    return "".join(result)


def _extract_size_and_base(name: str) -> Tuple[str, str]:
    """Split price-sheet name into (base_name, size_label).

    'Джейм160'          → ('Джейм', '160')
    'Zum 140'           → ('Zum', '140')
    'Коін 160 тахта'    → ('Коін тахта', '160')
    'Хьюго диван'       → ('Хьюго диван', '')
    """
    name = re.sub(r"\s*/.*", "", name).strip()
    name = re.sub(r"\(.*?\)", "", name).strip()
    m = re.search(r"(\d{2,3})\s*(?:см)?", name)
    if m:
        size = m.group(1)
        base = re.sub(r"\s+", " ", (name[: m.start()] + name[m.end() :]).strip())
        return base, size
    return name.strip(), ""


def _normalise_for_match(text: str) -> str:
    """Sorted bag-of-words normalisation for fuzzy name comparison.

    Algorithm:
    1. lowercase, replace '+' with ' plus '
    2. strip content after '/'
    3. apply Latin→Cyrillic model-name map (modo→модо, coin→коін…)
    4. apply word-level synonyms (угловой→кут, lite→лайт…)
    5. remove stopwords (диван, кресло)
    6. remove 2-3 digit size numbers (already extracted from price rows)
    7. transliterate to ASCII using и/і→i map
    8. remove non-alphanumeric
    9. sort words alphabetically (word-order independence)
    """
    text = text.lower().strip()
    text = text.replace("+", " plus ")
    text = re.sub(r"\s*/.*", "", text)
    text = re.sub(r"\(.*?\)", "", text)

    words = text.split()
    result = []
    for w in words:
        # Latin→Cyrillic model names
        w = _LATIN_TO_NORM.get(w, w)
        # Word synonyms
        w = _WORD_SYNONYMS.get(w, w)
        if not w:
            continue
        if w in _STOPWORDS:
            continue
        # Strip 2-3 digit size numbers already captured during price-row parsing
        if re.fullmatch(r"\d{2,3}", w):
            continue
        result.append(w)

    transliterated = []
    for w in result:
        # dzh_as_j=False: keep дж→dzh so 'Джеймс'/'Джейм' stay comparable
        t = _transliterate(w, _MATCH_CYRILLIC_MAP, dzh_as_j=False)
        t = re.sub(r"[^a-z0-9]", "", t)
        if t:
            transliterated.append(t)

    transliterated.sort()
    return "".join(transliterated)


def _fuzzy(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _parse_price(value) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("1"))
    except InvalidOperation:
        return None


def _generate_slug(name: str) -> str:
    from furniture.models import Furniture

    base = slugify(_transliterate(name)) or "divanoff"
    slug = base
    suffix = 1
    while Furniture.objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


# ── Price-sheet loader ────────────────────────────────────────────────────────

def load_price_rows(xlsx_path: str, price_col: int = PRICE_COL) -> List[PriceRow]:
    """Parse XLSX and return a list of PriceRow objects (rows 8+).

    Loads all 8 fabric-category prices (cols C–J) per row regardless of price_col.
    `price` is set to the column requested by price_col (for backward compat).
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb.active
    rows: List[PriceRow] = []
    col_offset = FABRIC_COLS[0]  # 2
    for row in ws.iter_rows(min_row=8, values_only=True):
        raw_name = row[1]
        if not raw_name or not isinstance(raw_name, str) or not raw_name.strip():
            continue
        all_prices = [
            _parse_price(row[col] if col < len(row) else None)
            for col in FABRIC_COLS
        ]
        price = all_prices[price_col - col_offset]
        if not price or price <= 0:
            continue
        base_name, size_label = _extract_size_and_base(raw_name)
        norm_key = _normalise_for_match(base_name)
        rows.append(PriceRow(
            raw_name=raw_name.strip(),
            base_name=base_name,
            size_label=size_label,
            norm_key=norm_key,
            price=price,
            all_prices=all_prices,
        ))
    wb.close()
    return rows


def _optimal_optimal_fabric_step(all_prices: List[Optional[Decimal]]) -> Decimal:
    """Minimum step S (rounded up to whole UAH) such that base + k*S >= actual_price[k].

    Iterates over categories 1..7 and picks the largest required step,
    guaranteeing the displayed price is never below the spreadsheet price.
    """
    import math

    base = all_prices[0] if all_prices else None
    if not base:
        return Decimal("0")
    min_step = Decimal("0")
    for k, price in enumerate(all_prices[1:], start=1):
        if price and price > base:
            needed = Decimal(str(math.ceil(float((price - base) / k))))
            if needed > min_step:
                min_step = needed
    return min_step


def _ensure_divanoff_brand():
    from fabric_category.models import FabricBrand, FabricCategory

    brand, _ = FabricBrand.objects.get_or_create(name="Divanoff")
    for i, label in enumerate(FABRIC_CATEGORY_LABELS):  # includes Category 0 (i=0)
        FabricCategory.objects.get_or_create(
            brand=brand, name=label, defaults={"price": Decimal(str(i))}
        )
    return brand


def _best_match_key(site_norm: str, price_rows: List[PriceRow]) -> Tuple[str, float]:
    """Return (best_norm_key, best_score) from price_rows for a given site_norm."""
    key_scores: Dict[str, float] = {}
    for pr in price_rows:
        if pr.norm_key in key_scores:
            continue
        key_scores[pr.norm_key] = _fuzzy(site_norm, pr.norm_key)
    return max(key_scores.items(), key=lambda kv: kv[1], default=("", 0.0))


def match_price_rows(product_name: str, price_rows: List[PriceRow]) -> List[PriceRow]:
    """Find all price rows whose base_name best matches the product name.

    Returns a list because one site product can map to multiple sizes (e.g.
    'Джеймс' → Джейм160 + Джейм180 + Джейм195).

    Two-pass strategy:
    Pass 1 — full normalised name including shape words (кут, міні, тахта).
    Pass 2 — if no match, retry without 'кут' (handles cases like 'Норд Мини
    угловой' vs price-sheet 'Норд mini' that omits the 'кут' word).
    """
    site_norm = _normalise_for_match(
        re.sub(r"^(?:диван|модульна[а-я]*)\s+", "", product_name, flags=re.I)
    )
    if not site_norm:
        return []

    best_key, best_score = _best_match_key(site_norm, price_rows)

    # Pass 2: if угловой/кутовий is in site name but price omits 'кут'
    if best_score < MATCH_THRESHOLD and re.search(r"угл|кут", product_name, re.I):
        norm_no_kut = re.sub(r"kut", "", site_norm)
        if norm_no_kut and norm_no_kut != site_norm:
            bk2, bs2 = _best_match_key(norm_no_kut, price_rows)
            if bs2 > best_score:
                best_key, best_score = bk2, bs2

    if best_score < MATCH_THRESHOLD:
        return []

    return [pr for pr in price_rows if pr.norm_key == best_key]


# ── Scraper class ─────────────────────────────────────────────────────────────

class DivanoffScraper:
    def __init__(self):
        self.session = self._build_session()
        self._progress_callback = None

    def set_progress_callback(self, callback):
        self._progress_callback = callback

    def _log(self, msg: str) -> None:
        logger.info(msg)
        if self._progress_callback:
            self._progress_callback(msg)

    def _build_session(self):
        session = cffi_requests.Session(impersonate="chrome124")
        session.headers.update({
            "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        })
        return session

    def _get(self, url: str, timeout: int = 25) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as exc:
            logger.warning("GET failed %s: %s", url, exc)
            return None

    # ── Catalog ───────────────────────────────────────────────────────────────

    def collect_product_urls(self, limit: Optional[int] = None) -> List[str]:
        all_urls: List[str] = []
        seen: set = set()

        for page in range(1, MAX_PAGES + 1):
            url = CATALOG_URL if page == 1 else f"{CATALOG_URL}?page={page}"
            self._log(f"Каталог сторінка {page}/{MAX_PAGES}: {url}")
            time.sleep(REQUEST_DELAY if page > 1 else 0)

            soup = self._get(url)
            if not soup:
                self._log(f"  ПОМИЛКА: сторінка {page} недоступна")
                break

            page_urls = []
            for card in soup.select(".product-bl"):
                a = card.select_one("a[href]")
                if not a:
                    continue
                href = a["href"]
                if not href.startswith("http"):
                    href = BASE_URL + href
                if href not in seen:
                    seen.add(href)
                    page_urls.append(href)
                    if limit and len(all_urls) + len(page_urls) >= limit:
                        break

            self._log(f"  Знайдено {len(page_urls)} посилань")
            all_urls.extend(page_urls)
            if limit and len(all_urls) >= limit:
                break

        self._log(f"Всього URL: {len(all_urls)}")
        return all_urls

    # ── Product detail ────────────────────────────────────────────────────────

    def scrape_product(self, url: str) -> Optional[DivanoffProduct]:
        soup = self._get(url)
        if not soup:
            return None

        name_el = soup.select_one(".pg-title")
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name:
            return None

        # Article code: "Артикул: DV00230" → "DV00230"
        site_article = ""
        sub_el = soup.select_one(".pg-subTitle")
        if sub_el:
            m = re.search(r"(DV\d+)", sub_el.get_text())
            if m:
                site_article = m.group(1)
        if not site_article:
            site_article = hashlib.md5(url.encode()).hexdigest()[:8].upper()

        # Description
        description = ""
        desc_el = soup.select_one(".description")
        if desc_el:
            description = re.sub(r"\s+", " ", desc_el.get_text(separator=" ", strip=True)).strip()

        # Specs — only target fields
        sleep_length = ""
        sleep_width = ""
        for item in soup.select(".attr-item"):
            parts = item.get_text(separator=":", strip=True).split(":")
            if len(parts) >= 2:
                key = parts[0].strip()
                val = parts[1].strip()
                if key == "Длина спального места, см":
                    sleep_length = val
                elif key == "Ширина спального места, см":
                    sleep_width = val

        # Images — from JSON-LD ImageObject (gives full-size contentUrl)
        image_urls = self._extract_images(soup)

        return DivanoffProduct(
            url=url,
            name=name,
            site_article=site_article,
            description=description,
            sleep_length=sleep_length,
            sleep_width=sleep_width,
            image_urls=image_urls,
        )

    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract full-size image URLs from JSON-LD ImageObject blocks."""
        urls: List[str] = []
        seen: set = set()

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            if data.get("@type") == "ImageObject":
                src = data.get("contentUrl", "")
                if src and src not in seen:
                    seen.add(src)
                    urls.append(src)

        # Fallback: thumbnail imgs in .image-side, convert to ~1920px
        if not urls:
            img_side = soup.select_one(".image-side")
            if img_side:
                for img in img_side.select("img.img-responsive"):
                    src = img.get("src", "")
                    if not src or "68x37" in src:
                        continue
                    # Convert 556x306 → 1920x768
                    full = re.sub(r"-\d+x\d+(\.[a-zA-Z]+)$", r"-1920x768\1", src)
                    if full not in seen:
                        seen.add(full)
                        urls.append(full)

        return urls

    # ── Subcategory helper ────────────────────────────────────────────────────

    def _ensure_subcategory(self, slug: str):
        from categories.models import Category
        from sub_categories.models import SubCategory

        sub = SubCategory.objects.filter(slug=slug).first()
        if sub:
            return sub

        cfg = SUBCATEGORY_CONFIG
        category = Category.objects.filter(name=cfg["category_name"]).first()
        if not category:
            raise RuntimeError(
                f"Категорія '{cfg['category_name']}' не знайдена в БД."
            )
        sub = SubCategory.objects.create(slug=slug, name=cfg["name"], category=category)
        self._log(f"Створено підкатегорію: {sub.name} ({sub.slug})")
        return sub

    # ── Image download ────────────────────────────────────────────────────────

    def _image_cache_path(self, url: str) -> str:
        ext = re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", url, re.I)
        ext_str = f".{ext.group(1).lower()}" if ext else ".jpg"
        digest = hashlib.sha1(url.encode()).hexdigest()
        return f"{IMAGE_CACHE_DIR}/{digest}{ext_str}"

    def _download_image(self, url: str) -> Optional[str]:
        cache_path = self._image_cache_path(url)
        if default_storage.exists(cache_path):
            return cache_path
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Image download failed %s: %s", url, exc)
            return None
        content = ContentFile(resp.content)
        if not self._is_valid_image(content):
            return None
        default_storage.save(cache_path, content)
        return cache_path

    def _is_valid_image(self, content: ContentFile) -> bool:
        try:
            from PIL import Image
            content.seek(0)
            with Image.open(content) as img:
                img.verify()
            content.seek(0)
            return True
        except Exception:
            content.seek(0)
            return False

    def _save_images(self, furniture, image_urls: List[str]) -> None:
        from furniture.models import FurnitureImage

        for idx, img_url in enumerate(image_urls[:5]):
            cache_path = self._download_image(img_url)
            if not cache_path:
                continue
            if idx == 0 and not furniture.image:
                furniture.image.name = cache_path
                furniture.save(update_fields=["image"])
            else:
                gallery = FurnitureImage(
                    furniture=furniture,
                    alt_text=f"{furniture.name} — фото {idx}",
                    position=idx,
                )
                gallery.image.name = cache_path
                gallery.save()

    # ── Import ────────────────────────────────────────────────────────────────

    def run_import(
        self,
        subcategory_slug: str,
        xlsx_path: str,
        dry_run: bool = False,
        limit: Optional[int] = None,
        price_col: int = PRICE_COL,
    ) -> Dict:
        from furniture.models import Furniture
        from params.models import FurnitureParameter, Parameter

        sub_category = None
        fabric_brand = None
        if not dry_run:
            try:
                sub_category = self._ensure_subcategory(subcategory_slug)
            except RuntimeError as exc:
                return {"success": False, "error": str(exc)}
            fabric_brand = _ensure_divanoff_brand()

        price_rows = load_price_rows(xlsx_path, price_col)
        self._log(f"Завантажено {len(price_rows)} рядків з прайсу")

        all_urls = self.collect_product_urls(limit=limit)
        self._log(f"Обробляємо {len(all_urls)} сторінок товарів...")

        # base_model_name → leader Furniture (for variant grouping)
        leaders: Dict[str, "Furniture"] = {}
        if not dry_run:
            for f in Furniture.objects.filter(
                sub_category__slug=subcategory_slug,
                variant_group_leader__isnull=True,
            ).exclude(base_model_name=""):
                leaders[f.base_model_name] = f

        stats = {
            "created": 0, "updated": 0, "skipped": 0,
            "unmatched": 0, "errors": [],
        }

        for idx, url in enumerate(all_urls, 1):
            self._log(f"[{idx}/{len(all_urls)}] {url}")
            time.sleep(REQUEST_DELAY)

            product = self.scrape_product(url)
            if not product:
                stats["errors"].append(f"Не вдалося завантажити: {url}")
                stats["skipped"] += 1
                continue

            matched = match_price_rows(product.name, price_rows)
            if not matched:
                self._log(f"  ⚠ Не знайдено в прайсі: {product.name}")
                stats["unmatched"] += 1
                continue

            self._log(
                f"  Знайдено {len(matched)} збіг(ів) в прайсі: "
                + ", ".join(f"{pr.raw_name} ({pr.price} грн)" for pr in matched)
            )

            # One site product → N furniture items (one per price row / size)
            multiple = len(matched) > 1
            base_key = product.site_article  # grouping key

            for pr in matched:
                article_code = (
                    f"DFN-{product.site_article}-{pr.size_label}"
                    if multiple and pr.size_label
                    else f"DFN-{product.site_article}"
                )
                variant_label = pr.size_label if multiple else ""
                size_suffix = f" {pr.size_label}" if (multiple and pr.size_label) else ""
                full_name = product.name + size_suffix

                existing = Furniture.objects.filter(article_code=article_code).first()
                if existing:
                    changed = self._update_existing(existing, pr, dry_run)
                    stats["updated" if changed else "skipped"] += 1
                    continue

                if dry_run:
                    role = "ЛІДЕР" if base_key not in leaders else "ВАРІАНТ"
                    self._log(
                        f"  [DRY-RUN] {role} {full_name} ({article_code}) — {pr.price} грн"
                    )
                    if base_key not in leaders:
                        leaders[base_key] = True  # type: ignore[assignment]
                        stats["created"] += 1
                    else:
                        stats["created"] += 1
                    continue

                leader = leaders.get(base_key) if multiple else None

                step = _optimal_fabric_step(pr.all_prices)
                furniture = Furniture.objects.create(
                    name=full_name,
                    article_code=article_code,
                    slug=_generate_slug(full_name),
                    sub_category=sub_category,
                    price=pr.price,
                    description=product.description or full_name,
                    stock_status="in_stock",
                    base_model_name=base_key if multiple else "",
                    variant_label=variant_label,
                    variant_group_leader=leader,
                    selected_fabric_brand=fabric_brand,
                    fabric_step_raw=step,
                    fabric_value=step,
                )

                # Specs params
                if product.sleep_length or product.sleep_width:
                    self._save_spec_param(
                        furniture, "Длина спального места, см",
                        product.sleep_length, "dovzhyna-spalnoho-mistsia-sm",
                    )
                    self._save_spec_param(
                        furniture, "Ширина спального места, см",
                        product.sleep_width, "shryna-spalnoho-mistsia-sm",
                    )

                self._save_images(furniture, product.image_urls)

                if multiple:
                    if leader:
                        self._log(f"  Варіант: {furniture.name} ({article_code}) → {leader.article_code}")
                        stats["created"] += 1
                    else:
                        self._log(f"  Лідер: {furniture.name} ({article_code})")
                        leaders[base_key] = furniture
                        stats["created"] += 1
                else:
                    self._log(f"  Створено: {furniture.name} ({article_code}) — {pr.price} грн")
                    stats["created"] += 1

        stats["success"] = True
        return stats

    def _save_spec_param(self, furniture, label: str, value: str, key: str) -> None:
        from params.models import FurnitureParameter, Parameter

        if not value:
            return
        param, _ = Parameter.objects.get_or_create(key=key, defaults={"label": label})
        FurnitureParameter.objects.update_or_create(
            furniture=furniture,
            parameter=param,
            defaults={"value": value},
        )

    def _update_existing(self, furniture, pr: "PriceRow", dry_run: bool) -> bool:
        new_price = pr.price
        new_step = _optimal_fabric_step(pr.all_prices)
        if furniture.price == new_price and furniture.fabric_step_raw == new_step:
            return False
        self._log(f"  Оновлено {furniture.article_code}: {furniture.price} → {new_price}")
        if not dry_run:
            furniture.price = new_price
            furniture.fabric_step_raw = new_step
            furniture.fabric_value = new_step
            furniture.save(update_fields=["price", "fabric_step_raw", "fabric_value"])
        return True

    # ── Price update ──────────────────────────────────────────────────────────

    def update_prices(
        self,
        subcategory_slug: str,
        xlsx_path: str,
        price_col: int = PRICE_COL,
    ) -> Dict:
        from furniture.models import Furniture

        self._log("Оновлення цін Divanoff...")

        fabric_brand = _ensure_divanoff_brand()
        price_rows = load_price_rows(xlsx_path, price_col)
        self._log(f"Завантажено {len(price_rows)} рядків з прайсу")

        # article_code → Furniture
        furniture_map: Dict[str, "Furniture"] = {
            f.article_code: f
            for f in Furniture.objects.filter(sub_category__slug=subcategory_slug)
            .only("id", "article_code", "price")
            if f.article_code
        }
        if not furniture_map:
            return {"success": False, "error": "Немає товарів — спочатку запустіть import"}

        all_urls = self.collect_product_urls()
        stats = {"checked": 0, "updated": 0, "not_found": 0, "unmatched": 0}

        for idx, url in enumerate(all_urls, 1):
            self._log(f"[{idx}/{len(all_urls)}] {url}")
            time.sleep(REQUEST_DELAY)

            product = self.scrape_product(url)
            if not product:
                continue

            matched = match_price_rows(product.name, price_rows)
            if not matched:
                self._log(f"  ⚠ Не знайдено в прайсі: {product.name}")
                stats["unmatched"] += 1
                continue

            multiple = len(matched) > 1
            for pr in matched:
                article_code = (
                    f"DFN-{product.site_article}-{pr.size_label}"
                    if multiple and pr.size_label
                    else f"DFN-{product.site_article}"
                )
                furniture = furniture_map.get(article_code)
                if not furniture:
                    stats["not_found"] += 1
                    continue

                stats["checked"] += 1
                step = _optimal_fabric_step(pr.all_prices)
                update_fields = []
                if furniture.price != pr.price:
                    furniture.price = pr.price
                    update_fields.append("price")
                if furniture.fabric_step_raw != step:
                    furniture.fabric_step_raw = step
                    furniture.fabric_value = step
                    update_fields += ["fabric_step_raw", "fabric_value"]
                if not furniture.selected_fabric_brand_id:
                    furniture.selected_fabric_brand = fabric_brand
                    update_fields.append("selected_fabric_brand")
                if update_fields:
                    furniture.save(update_fields=update_fields)
                    self._log(f"  {article_code}: {pr.price} грн")
                    stats["updated"] += 1

        stats["success"] = True
        return stats
