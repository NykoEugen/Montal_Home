import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify

logger = logging.getLogger(__name__)

BASE_URL = "https://evrodim-company.com.ua"
CATALOG_URL = f"{BASE_URL}/yevrodim"
REQUEST_DELAY = 0.8
IMAGE_CACHE_DIR = "supplier_cache/evrodim"

CYRILLIC_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e",
    "є": "ie", "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "yi", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ь": "", "ю": "yu", "я": "ya",
}

SUBCATEGORY_CONFIG = {
    "slug": "stoly-evrodim",
    "name": "Столи (Evrodim)",
    "category_name": "Столи",
}

# Шаблонні фрагменти Evrodim, які видаляємо з опису.
_DESC_STRIP_PATTERNS: List[re.Pattern] = [
    re.compile(r"Країна\s+виробництва\s*:\s*\S+\.?", re.I),
    re.compile(r"Товар знаходиться\s+на складі в Україні\.?", re.I),
    re.compile(r"Продавець\s*:\s*Evrodim\.?", re.I),
    re.compile(r"Умови оплати,?\s*доставки та повернення\s*[—–-]\s*на сайті\.?", re.I),
    re.compile(r"Теги\s*:.*", re.I | re.S),
    # Назви бренду (латиниця та кирилиця)
    re.compile(r"«?[ЄЕ]вродім»?", re.I),
    re.compile(r"\bevrodim\b", re.I),
]

# Ключові слова для мітки кольору/матеріалу варіанту
_COLOR_RE = re.compile(
    r"\b(grey|gray|beige|white|black|brown|blue|green|red|gold|silver|"
    r"glossy|gloss|satin|snow|stone|marble|oak|walnut|ash|ceramic|"
    r"mountain|cream|sand|anthracite|wenge|natural|ivory)\b",
    re.I,
)

# Заголовки секцій у блоці характеристик (не є парами ключ-значення)
_PARAM_SECTION_HEADERS = {"характеристики", "розміри"}

_SIZE_SUFFIX_RE = re.compile(r"-\d+x\d+(\.[A-Za-z]+)$")


@dataclass
class EvrodimProduct:
    url: str
    name: str
    article_code: str       # EVR-{product_id} — унікальний
    base_model_name: str    # Код товару (T-904) — для групування варіантів
    variant_label: str      # Колір/стиль для чіпа (Grey Gloss, Beige…)
    price: Decimal
    sale_price: Optional[Decimal] = None
    description: str = ""
    params: Dict[str, str] = field(default_factory=dict)
    image_urls: List[str] = field(default_factory=list)


def _transliterate(value: str) -> str:
    return "".join(CYRILLIC_MAP.get(ch.lower(), ch) for ch in value)


def _parse_price_text(text: str) -> Optional[Decimal]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d]", "", text.replace("\xa0", ""))
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _clean_description(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text)
    for pattern in _DESC_STRIP_PATTERNS:
        normalized = pattern.sub("", normalized)
    return re.sub(r"\s{2,}", " ", normalized).strip()


def _extract_variant_label(name: str) -> str:
    """Витягує мітку кольору/стилю з назви товару. Додає 'Mini' якщо є в назві."""
    matches = _COLOR_RE.findall(name)
    if matches:
        seen: set = set()
        unique = []
        for m in matches:
            key = m.lower()
            if key not in seen:
                seen.add(key)
                unique.append(m.title())
        label = " ".join(unique[:3])
    else:
        # Fallback: перша латинська послідовність (не артикул)
        m = re.search(r"[A-Za-z][A-Za-z\s]{3,20}", name)
        label = m.group().strip() if m else ""

    if re.search(r"\bMini\b", name, re.I) and "Mini" not in label:
        label = (label + " Mini").strip()
    return label


def _compute_base_model_name(kod_tovaru: str, name: str) -> str:
    """Ключ групування варіантів. Основний — Код товару; fallback — нормалізована назва."""
    if kod_tovaru:
        return kod_tovaru
    # Прибираємо кольори, Mini і артикули → залишаємо «скелет» назви
    normalized = _COLOR_RE.sub("", name)
    normalized = re.sub(r"\bMini\b", "", normalized, flags=re.I)
    normalized = re.sub(r"\b[A-Z][A-Z0-9]{1,}-\d+[A-Z0-9\-]*\b", "", normalized)  # T-904, DF505-2T…
    normalized = re.sub(r"\s+", " ", normalized).strip(" ,–—-")
    return normalized or name[:60]


def _generate_slug(name: str) -> str:
    from furniture.models import Furniture
    base = slugify(_transliterate(name)) or "evrodim"
    slug = base
    suffix = 1
    while Furniture.objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


class EvrodimScraper:
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
            "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8",
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

    def _detect_total_pages(self, soup: BeautifulSoup) -> int:
        max_page = 1
        for a in soup.select("ul.pagination a, .pagination a"):
            href = a.get("href", "")
            m = re.search(r"[?&]page=(\d+)", href)
            if m:
                max_page = max(max_page, int(m.group(1)))
        return max_page

    def _collect_urls_from_page(self, soup: BeautifulSoup) -> List[str]:
        seen: set = set()
        urls: List[str] = []
        for card in soup.select(".product-layout"):
            for a in card.select("a[href]"):
                href = a.get("href", "")
                if href and href not in seen:
                    seen.add(href)
                    urls.append(href)
                    break
        return urls

    def collect_product_urls(self, limit: Optional[int] = None) -> List[str]:
        self._log(f"Збираємо посилання з {CATALOG_URL}")
        first_soup = self._get(CATALOG_URL)
        if not first_soup:
            self._log("ПОМИЛКА: каталог недоступний")
            return []

        total_pages = self._detect_total_pages(first_soup)
        self._log(f"Сторінок: {total_pages}")

        all_urls: List[str] = []
        seen_global: set = set()

        def _add_urls(urls: List[str]) -> bool:
            for url in urls:
                if url not in seen_global:
                    seen_global.add(url)
                    all_urls.append(url)
                    if limit and len(all_urls) >= limit:
                        return True
            return False

        page1_urls = self._collect_urls_from_page(first_soup)
        self._log(f"Сторінка 1/{total_pages}: {len(page1_urls)} посилань")
        if _add_urls(page1_urls):
            return all_urls

        for page in range(2, total_pages + 1):
            time.sleep(REQUEST_DELAY)
            soup = self._get(f"{CATALOG_URL}/?page={page}")
            if not soup:
                break
            urls = self._collect_urls_from_page(soup)
            self._log(f"Сторінка {page}/{total_pages}: {len(urls)} посилань")
            if _add_urls(urls):
                break

        self._log(f"Всього посилань зібрано: {len(all_urls)}")
        return all_urls

    # ── Product detail ────────────────────────────────────────────────────────

    def scrape_product(self, url: str) -> Optional[EvrodimProduct]:
        soup = self._get(url)
        if not soup:
            return None

        name_el = soup.select_one("h1")
        if not name_el:
            return None
        name = name_el.get_text(strip=True)

        # Filter: only tables ("Стіл ...", not "Стілець" or "Стільниця")
        name_lower = name.lower()
        if not (name_lower.startswith("стіл ") or name_lower == "стіл"):
            return None

        # Filter: only Generic manufacturer
        if self._parse_manufacturer(soup).lower() != "generic":
            return None

        article_code = self._parse_article_code(soup, url)
        kod_tovaru = self._parse_base_model_name(soup)
        base_model_name = _compute_base_model_name(kod_tovaru, name)
        variant_label = _extract_variant_label(name)
        price, sale_price = self._parse_prices(soup)
        description = self._parse_description(soup)
        params = self._parse_params(soup)
        image_urls = self._extract_images(soup)

        return EvrodimProduct(
            url=url,
            name=name,
            article_code=article_code,
            base_model_name=base_model_name,
            variant_label=variant_label,
            price=price,
            sale_price=sale_price,
            description=description,
            params=params,
            image_urls=image_urls,
        )

    def _parse_manufacturer(self, soup: BeautifulSoup) -> str:
        for title_el in soup.select(".rm-product-center-info-item-title"):
            if "Виробник" in title_el.get_text():
                sibling = title_el.find_next_sibling()
                if sibling:
                    return sibling.get_text(strip=True)
        return ""

    def _parse_article_code(self, soup: BeautifulSoup, url: str) -> str:
        """EVR-{product_id} з URL — унікальний для кожного товару.
        Fallback — MD5 від URL.
        """
        m = re.search(r"product_id=(\d+)", url)
        if m:
            return f"EVR-{m.group(1)}"
        return f"EVR-{hashlib.md5(url.encode()).hexdigest()[:8]}"

    def _parse_base_model_name(self, soup: BeautifulSoup) -> str:
        """'Код товару' зі сторінки (T-904) — спільний для кольорових варіантів."""
        for el in soup.find_all(string=re.compile("Код товару")):
            parent = el.parent
            text = (parent.parent.get_text(strip=True) if parent.parent else parent.get_text(strip=True))
            m = re.search(r"Код товару[:\s]*(.+)", text)
            if m:
                code = m.group(1).strip()
                if code:
                    return code
        return ""

    def _parse_prices(self, soup: BeautifulSoup) -> Tuple[Decimal, Optional[Decimal]]:
        """Повертає (regular_price, sale_price). sale_price=None якщо акції немає."""
        old_el = soup.select_one(".rm-product-center-price-old")
        new_el = soup.select_one(".rm-product-mobile-fixed-price-new")

        if old_el and new_el:
            regular = _parse_price_text(old_el.get_text(strip=True)) or Decimal("0")
            sale = _parse_price_text(new_el.get_text(strip=True))
            if sale and sale < regular:
                return regular, sale
            return regular, None

        # Немає знижки — одна ціна
        price_el = soup.select_one(".rm-product-center-price span")
        price = _parse_price_text(price_el.get_text(strip=True)) if price_el else Decimal("0")
        return price or Decimal("0"), None

    def _parse_description(self, soup: BeautifulSoup) -> str:
        desc_el = soup.select_one("#product_description.rm-product-tabs-description")
        if not desc_el:
            desc_el = soup.select_one(".rm-product-tabs-description")
        if desc_el:
            return _clean_description(desc_el.get_text(separator="\n", strip=True))
        return ""

    def _parse_params(self, soup: BeautifulSoup) -> Dict[str, str]:
        params: Dict[str, str] = {}
        # На сторінці є два окремих блоки з однаковим класом: Характеристики і Розміри
        for block in soup.select(".rm-product-tabs-attributtes-list"):
            for item in block.select(".rm-product-tabs-attributtes-list-item"):
                divs = item.find_all("div", recursive=False)
                if len(divs) >= 2:
                    key = divs[0].get_text(strip=True)
                    val = divs[1].get_text(strip=True)
                    if key and val:
                        params[key] = val
        return params

    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        image_urls: List[str] = []
        seen: set = set()
        for img in soup.select(".oct-gallery img"):
            src = img.get("src", "")
            if not src or "50x50" in src or "Банер" in src:
                continue
            if src not in seen:
                seen.add(src)
                image_urls.append(src)
        return image_urls

    # ── Subcategory auto-create ───────────────────────────────────────────────

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
                f"Категорія '{cfg['category_name']}' не знайдена в БД. "
                f"Створіть її або вкажіть правильну назву в SUBCATEGORY_CONFIG."
            )

        sub = SubCategory.objects.create(slug=slug, name=cfg["name"], category=category)
        self._log(f"Створено підкатегорію: {sub.name} ({sub.slug})")
        return sub

    # ── Image download ────────────────────────────────────────────────────────

    def _image_cache_path(self, url: str) -> str:
        parsed = urlsplit(url)
        ext = re.search(r"\.(jpg|jpeg|png|webp|gif)(\?|$)", parsed.path, re.I)
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

    # ── Promo sync ────────────────────────────────────────────────────────────

    def _apply_promo(self, furniture, product: EvrodimProduct) -> List[str]:
        """Оновлює is_promotional / promotional_price. Повертає змінені поля."""
        is_promo = product.sale_price is not None
        fields = []
        if furniture.is_promotional != is_promo:
            furniture.is_promotional = is_promo
            fields.append("is_promotional")
        target_price = product.sale_price if is_promo else None
        if furniture.promotional_price != target_price:
            furniture.promotional_price = target_price
            fields.append("promotional_price")
        return fields

    # ── Import ────────────────────────────────────────────────────────────────

    def run_import(
        self,
        subcategory_slug: str,
        dry_run: bool = False,
        limit: Optional[int] = None,
    ) -> Dict:
        from furniture.models import Furniture
        from params.models import FurnitureParameter, Parameter

        sub_category = None
        if not dry_run:
            try:
                sub_category = self._ensure_subcategory(subcategory_slug)
            except RuntimeError as exc:
                return {"success": False, "error": str(exc)}

        # Завантажуємо існуючих лідерів варіантних груп із БД
        # base_model_name → Furniture (лідер групи)
        leaders: Dict[str, "Furniture"] = {}
        if not dry_run:
            for f in Furniture.objects.filter(
                sub_category__slug=subcategory_slug,
                variant_group_leader__isnull=True,
            ).exclude(base_model_name=""):
                leaders[f.base_model_name] = f

        all_urls = self.collect_product_urls(limit=limit)
        self._log(f"Обробляємо {len(all_urls)} сторінок товарів...")

        stats = {"created": 0, "variants": 0, "updated": 0, "skipped": 0, "not_table": 0, "errors": []}

        for idx, url in enumerate(all_urls, 1):
            self._log(f"[{idx}/{len(all_urls)}] {url}")
            time.sleep(REQUEST_DELAY)

            product = self.scrape_product(url)
            if not product:
                stats["not_table"] += 1
                continue

            sale_info = f" [акція: {product.sale_price} грн]" if product.sale_price else ""

            # Вже існує в БД
            existing = Furniture.objects.filter(article_code=product.article_code).first()
            if existing:
                changed = self._update_existing(existing, product, dry_run)
                stats["updated" if changed else "skipped"] += 1
                continue

            if dry_run:
                is_variant = product.base_model_name in leaders if leaders else False
                role = "ВАРІАНТ" if is_variant else "ЛІДЕР"
                self._log(
                    f"  [DRY-RUN] {role} {product.name} ({product.article_code})"
                    f" [{product.base_model_name}] — {product.price} грн{sale_info}"
                )
                # В dry-run моделюємо: перший з base_model_name стає лідером
                if product.base_model_name and product.base_model_name not in leaders:
                    leaders[product.base_model_name] = True  # type: ignore[assignment]
                    stats["created"] += 1
                else:
                    stats["variants"] += 1
                continue

            # Визначаємо роль: лідер або варіант
            leader = leaders.get(product.base_model_name) if product.base_model_name else None

            promo_fields: Dict = {}
            if product.sale_price:
                promo_fields = {
                    "is_promotional": True,
                    "promotional_price": product.sale_price,
                }

            furniture = Furniture.objects.create(
                name=product.name,
                article_code=product.article_code,
                slug=_generate_slug(product.name),
                sub_category=sub_category,
                price=product.price,
                description=product.description or product.name,
                stock_status="in_stock",
                base_model_name=product.base_model_name,
                variant_label=product.variant_label,
                variant_group_leader=leader,
                **promo_fields,
            )

            if product.params:
                for param_label, param_value in product.params.items():
                    if not param_label or not param_value:
                        continue
                    key = slugify(_transliterate(param_label))[:100] or f"param_{abs(hash(param_label))}"
                    param, _ = Parameter.objects.get_or_create(key=key, defaults={"label": param_label})
                    FurnitureParameter.objects.update_or_create(
                        furniture=furniture,
                        parameter=param,
                        defaults={"value": param_value},
                    )

            self._save_images(furniture, product.image_urls)

            if leader:
                self._log(
                    f"  Варіант: {furniture.name} ({furniture.article_code})"
                    f" → лідер {leader.article_code}{sale_info}"
                )
                stats["variants"] += 1
            else:
                self._log(f"  Лідер: {furniture.name} ({furniture.article_code}){sale_info}")
                if product.base_model_name:
                    leaders[product.base_model_name] = furniture
                stats["created"] += 1

        stats["success"] = True
        return stats

    def _update_existing(self, furniture, product: EvrodimProduct, dry_run: bool) -> bool:
        changed = False
        update_fields = []

        if product.price and furniture.price != product.price:
            if not dry_run:
                furniture.price = product.price
                update_fields.append("price")
            self._log(f"  Оновлено ціну: {product.price}")
            changed = True

        if not dry_run:
            promo_fields = self._apply_promo(furniture, product)
            update_fields.extend(promo_fields)
            if promo_fields:
                changed = True

        if update_fields and not dry_run:
            furniture.save(update_fields=update_fields)

        if not furniture.image and product.image_urls:
            if not dry_run:
                self._save_images(furniture, product.image_urls)
            self._log("  Додано зображення")
            changed = True

        return changed

    def _save_images(self, furniture, image_urls: List[str]) -> None:
        from furniture.models import FurnitureImage

        for img_idx, img_url in enumerate(image_urls[:5]):
            cache_path = self._download_image(img_url)
            if not cache_path:
                continue
            if img_idx == 0 and not furniture.image:
                furniture.image.name = cache_path
                furniture.save(update_fields=["image"])
            else:
                gallery = FurnitureImage(
                    furniture=furniture,
                    alt_text=f"{furniture.name} — фото {img_idx}",
                    position=img_idx,
                )
                gallery.image.name = cache_path
                gallery.save()

    # ── Price update ──────────────────────────────────────────────────────────

    def update_prices(self, subcategory_slug: str) -> Dict:
        from furniture.models import Furniture

        self._log("Оновлення цін Evrodim...")

        try:
            self._ensure_subcategory(subcategory_slug)
        except RuntimeError as exc:
            return {"success": False, "error": str(exc)}

        furniture_map: Dict[str, Furniture] = {
            f.article_code: f
            for f in Furniture.objects.filter(sub_category__slug=subcategory_slug)
            .only("id", "article_code", "price", "is_promotional", "promotional_price")
            if f.article_code
        }

        if not furniture_map:
            return {"success": False, "error": "Немає товарів — спочатку запустіть import"}

        all_urls = self.collect_product_urls()
        stats = {"checked": 0, "updated": 0, "not_found": 0, "errors": []}

        for idx, url in enumerate(all_urls, 1):
            self._log(f"[{idx}/{len(all_urls)}] {url}")
            time.sleep(REQUEST_DELAY)

            product = self.scrape_product(url)
            if not product:
                continue

            furniture = furniture_map.get(product.article_code)
            if not furniture:
                stats["not_found"] += 1
                continue

            stats["checked"] += 1
            update_fields = []

            if product.price and furniture.price != product.price:
                furniture.price = product.price
                update_fields.append("price")

            promo_fields = self._apply_promo(furniture, product)
            update_fields.extend(promo_fields)

            if update_fields:
                furniture.save(update_fields=update_fields)
                sale_info = f" → акція {product.sale_price} грн" if product.sale_price else ""
                self._log(f"  {furniture.article_code}: {product.price} грн{sale_info}")
                stats["updated"] += 1

        stats["success"] = True
        return stats

    # ── Params update ─────────────────────────────────────────────────────────

    def update_params(self, subcategory_slug: str) -> Dict:
        """Оновлює характеристики (включно з Розмірами) для вже імпортованих товарів."""
        from furniture.models import Furniture
        from params.models import FurnitureParameter, Parameter

        self._log("Оновлення характеристик Evrodim...")

        furniture_map: Dict[str, int] = {
            f.article_code: f.id
            for f in Furniture.objects.filter(sub_category__slug=subcategory_slug)
            .only("id", "article_code")
            if f.article_code
        }

        if not furniture_map:
            return {"success": False, "error": "Немає товарів — спочатку запустіть import"}

        all_urls = self.collect_product_urls()
        stats = {"checked": 0, "updated": 0, "not_found": 0}

        for idx, url in enumerate(all_urls, 1):
            self._log(f"[{idx}/{len(all_urls)}] {url}")
            time.sleep(REQUEST_DELAY)

            product = self.scrape_product(url)
            if not product:
                continue

            furniture_id = furniture_map.get(product.article_code)
            if not furniture_id:
                stats["not_found"] += 1
                continue

            stats["checked"] += 1
            if not product.params:
                continue

            for param_label, param_value in product.params.items():
                if not param_label or not param_value:
                    continue
                key = slugify(_transliterate(param_label))[:100] or f"param_{abs(hash(param_label))}"
                param, _ = Parameter.objects.get_or_create(key=key, defaults={"label": param_label})
                FurnitureParameter.objects.update_or_create(
                    furniture_id=furniture_id,
                    parameter=param,
                    defaults={"value": param_value},
                )

            self._log(f"  {product.article_code}: {len(product.params)} параметрів")
            stats["updated"] += 1

        stats["success"] = True
        return stats
