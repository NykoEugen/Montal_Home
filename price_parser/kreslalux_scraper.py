import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify

logger = logging.getLogger(__name__)

CATALOG_URL = "https://kreslalux.ua/uk/18-kresla-dlya-doma"
BASE_URL = "https://kreslalux.ua"
MAX_PRICE_DEFAULT = Decimal("40000")
REQUEST_DELAY = 0.6  # seconds between requests
IMAGE_CACHE_DIR = "supplier_cache/kreslalux"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

CYRILLIC_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e",
    "є": "ie", "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "yi", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ь": "", "ю": "yu", "я": "ya",
}


@dataclass
class KreslaluxProduct:
    url: str
    name: str
    article_code: str
    price: Decimal
    description: str = ""
    params: Dict[str, str] = field(default_factory=dict)
    image_urls: List[str] = field(default_factory=list)


def _transliterate(value: str) -> str:
    return "".join(CYRILLIC_MAP.get(ch.lower(), ch) for ch in value)


def _extract_sku(text: str) -> str:
    """Extract the actual SKU code, stripping labels like 'Артикул:', 'SKU:' etc."""
    text = (text or "").strip()
    # Strip known label prefixes
    text = re.sub(r"^(?:Артикул|Арт\.|SKU|Код)[.:\s]+", "", text, flags=re.IGNORECASE).strip()
    # Remove all whitespace
    text = re.sub(r"\s+", "", text)
    return text


def _parse_price(text: str) -> Optional[Decimal]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d]", "", text.replace(",", ".").replace("\xa0", ""))
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _generate_slug(name: str) -> str:
    from furniture.models import Furniture
    base = slugify(_transliterate(name)) or "krislo"
    slug = base
    suffix = 1
    while Furniture.objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


class KreslaluxScraper:
    def __init__(self, max_price: Decimal = MAX_PRICE_DEFAULT):
        self.max_price = max_price
        self.session = self._build_session()
        self._progress_callback = None

    def set_progress_callback(self, callback):
        self._progress_callback = callback

    def _log(self, msg: str) -> None:
        logger.info(msg)
        if self._progress_callback:
            self._progress_callback(msg)

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "uk-UA,uk;q=0.9",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        })
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _get(self, url: str, timeout: int = 20) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as exc:
            logger.warning("GET failed %s: %s", url, exc)
            return None

    # ── Catalog scraping ──────────────────────────────────────────────────────

    def _scrape_catalog_page(self, url: str) -> List[Dict]:
        soup = self._get(url)
        if not soup:
            return []

        products = []
        for card in soup.select(".product-miniature"):
            link_el = card.select_one("h2 a, .product-title a, a.product_img_link")
            if not link_el:
                continue

            product_url = link_el.get("href", "")
            if not product_url.startswith("http"):
                product_url = BASE_URL + product_url

            name = link_el.get_text(strip=True)

            price_el = (
                card.select_one("span.product-price")
                or card.select_one("span.price")
                or card.select_one(".current-price-value")
                or card.select_one("[itemprop='price']")
            )
            price_text = ""
            if price_el:
                # Prefer content attribute (clean numeric value e.g. "4500")
                price_text = price_el.get("content") or price_el.get_text()
            price = _parse_price(price_text)

            # product-reference contains the SKU text directly (e.g. "03171")
            sku_el = card.select_one(".product-reference a, .product-reference")
            sku = ""
            if sku_el:
                sku = _extract_sku(sku_el.get_text(strip=True))

            products.append({"url": product_url, "name": name, "price": price, "sku": sku})

        return products

    def _detect_total_pages(self, soup: BeautifulSoup) -> int:
        pagination = soup.select("ul.page-list li a, .pagination a")
        max_page = 1
        for link in pagination:
            href = link.get("href", "")
            m = re.search(r"[?&]page=(\d+)", href)
            if m:
                max_page = max(max_page, int(m.group(1)))
            text = link.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
        return max_page

    def collect_candidate_urls(self, limit: Optional[int] = None) -> List[Dict]:
        """Return products from catalog with price ≤ max_price. Stops once limit is reached."""
        self._log(f"Збираємо товари до {self.max_price} грн з {CATALOG_URL}")

        first_soup = self._get(CATALOG_URL)
        if not first_soup:
            self._log("Не вдалося отримати каталог")
            return []

        total_pages = self._detect_total_pages(first_soup)
        self._log(f"Знайдено сторінок: {total_pages}")

        candidates = []

        def _add_from_page(products: List[Dict]) -> bool:
            for p in products:
                if p["price"] is not None and p["price"] <= self.max_price:
                    candidates.append(p)
                    if limit and len(candidates) >= limit:
                        return True
            return False

        if _add_from_page(self._scrape_catalog_page(CATALOG_URL)):
            self._log(f"Зібрано ліміт {limit} товарів з 1 сторінки")
            return candidates

        for page in range(2, total_pages + 1):
            time.sleep(REQUEST_DELAY)
            page_url = f"{CATALOG_URL}?page={page}"
            products = self._scrape_catalog_page(page_url)
            if not products:
                break
            if _add_from_page(products):
                self._log(f"Зібрано ліміт {limit} товарів (сторінка {page})")
                return candidates
            self._log(f"Сторінка {page}/{total_pages}: відібрано {len(candidates)} товарів")

        self._log(f"Всього відібрано кандидатів: {len(candidates)}")
        return candidates

    # ── Detail page scraping ──────────────────────────────────────────────────

    def scrape_product(self, url: str) -> Optional[KreslaluxProduct]:
        soup = self._get(url)
        if not soup:
            return None

        # Name
        name_el = soup.select_one("h1.page-title, h1[itemprop='name'], h1")
        name = name_el.get_text(strip=True) if name_el else ""
        if not name:
            return None

        # Article / SKU
        sku = ""
        # Find first product-reference that contains label like "Артикул:"
        sku = ""
        for ref_el in soup.select(".product-reference"):
            text = ref_el.get_text(strip=True)
            if re.search(r"(?:Артикул|Арт\.|SKU|Код)", text, re.IGNORECASE):
                sku = _extract_sku(text)
                break
        if not sku:
            # Fallback: first .product-reference element
            ref_el = soup.select_one(".product-reference")
            if ref_el:
                sku = _extract_sku(ref_el.get_text(strip=True))
        if not sku:
            match = re.search(r"(?:Артикул|Арт\.|SKU|Код)[.:\s]+([A-Za-z0-9\-]+)", soup.get_text())
            if match:
                sku = match.group(1).strip()

        if not sku:
            # Use product ID from URL as fallback article
            m = re.search(r"/(\d+)-", url)
            sku = f"KR-{m.group(1)}" if m else ""

        # Price
        price = Decimal("0")
        price_el = (
            soup.select_one("span.product-price[content]")
            or soup.select_one("meta[itemprop='price']")
            or soup.select_one(".current-price-value")
            or soup.select_one("span.product-price")
            or soup.select_one("span.price")
        )
        if price_el:
            price_text = price_el.get("content") or price_el.get_text()
            parsed = _parse_price(price_text)
            if parsed:
                price = parsed

        # Description
        desc_el = (
            soup.select_one("#product-description-short")
            or soup.select_one(".product-description")
            or soup.select_one("[itemprop='description']")
        )
        description = desc_el.get_text(strip=True) if desc_el else ""

        # Parameters (PrestaShop features table)
        params: Dict[str, str] = {}
        for row in soup.select(".product-features dl dt, .product-features dt"):
            label = row.get_text(strip=True)
            dd = row.find_next_sibling("dd")
            if dd:
                params[label] = dd.get_text(strip=True)

        # Also try table-based features
        for row in soup.select(".product-features tr"):
            cells = row.select("td, th")
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if label and value:
                    params[label] = value

        # Images — try multiple selectors (PrestaShop detail page)
        image_urls: List[str] = []
        seen = set()

        def _add_img_url(src: str) -> None:
            if not src or "svg" in src or src in seen:
                return
            if not src.startswith("http"):
                src = BASE_URL + src
            src = re.sub(r"/(home_default|medium_default|small_default|thickbox_default)/", "/large_default/", src)
            seen.add(src)
            image_urls.append(src)

        # Detail page: cover + thumbnails
        for img in soup.select(".product-cover img, #product-images-large img, .images-container img"):
            _add_img_url(img.get("src") or img.get("data-image-large-src") or img.get("data-src", ""))

        for img in soup.select("img.js-thumb, .product-images-thumbnails img"):
            src = (
                img.get("data-image-large-src")
                or img.get("data-full-size-image-url")
                or img.get("data-src")
                or img.get("src", "")
            )
            _add_img_url(src)

        # Fallback: any /img/p/ URL
        if not image_urls:
            for img in soup.find_all("img"):
                src = img.get("data-full-size-image-url") or img.get("data-src") or img.get("src", "")
                if "/img/p/" in src or "kreslalux" in src:
                    _add_img_url(src)

        return KreslaluxProduct(
            url=url,
            name=name,
            article_code=sku,
            price=price,
            description=description,
            params=params,
            image_urls=image_urls,
        )

    # ── Image download ────────────────────────────────────────────────────────

    def _download_image(self, url: str) -> Optional[str]:
        cache_path = self._image_cache_path(url)
        if default_storage.exists(cache_path):
            return cache_path
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Image download failed %s: %s", url, exc)
            return None

        content = ContentFile(resp.content)
        if not self._is_valid_image(content):
            return None
        default_storage.save(cache_path, content)
        return cache_path

    def _image_cache_path(self, url: str) -> str:
        parsed = urlsplit(url)
        ext = re.search(r"\.(jpg|jpeg|png|webp|gif)(\?|$)", parsed.path, re.I)
        ext_str = f".{ext.group(1).lower()}" if ext else ".jpg"
        digest = hashlib.sha1(url.encode()).hexdigest()
        return f"{IMAGE_CACHE_DIR}/{digest}{ext_str}"

    def _is_valid_image(self, content: ContentFile) -> bool:
        try:
            from PIL import Image, UnidentifiedImageError
            content.seek(0)
            with Image.open(content) as img:
                img.verify()
            content.seek(0)
            return True
        except Exception:
            content.seek(0)
            return False

    # ── Import ────────────────────────────────────────────────────────────────

    def run_import(
        self,
        dry_run: bool = False,
        limit: Optional[int] = None,
        subcategory_slug: str = "ortopedichni-krisla",
    ) -> Dict:
        from sub_categories.models import SubCategory
        from furniture.models import Furniture, FurnitureImage
        from params.models import FurnitureParameter, Parameter

        sub_category = SubCategory.objects.filter(slug=subcategory_slug).first()
        if not sub_category:
            return {"success": False, "error": f"Підкатегорія '{subcategory_slug}' не знайдена"}

        candidates = self.collect_candidate_urls(limit=limit)

        stats = {"created": 0, "updated": 0, "skipped": 0, "errors": []}

        for idx, candidate in enumerate(candidates, 1):
            self._log(f"[{idx}/{len(candidates)}] {candidate['name']}")
            time.sleep(REQUEST_DELAY)

            product = self.scrape_product(candidate["url"])
            if not product:
                stats["errors"].append(f"Не вдалося завантажити: {candidate['url']}")
                stats["skipped"] += 1
                continue

            if not product.article_code:
                stats["errors"].append(f"Немає артикулу: {product.name}")
                stats["skipped"] += 1
                continue

            existing = Furniture.objects.filter(article_code=product.article_code).first()

            if existing:
                if existing.price != product.price and product.price > 0:
                    if not dry_run:
                        existing.price = product.price
                        existing.save(update_fields=["price"])
                    self._log(f"  Оновлено ціну: {product.price}")
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
                continue

            if dry_run:
                self._log(f"  [DRY-RUN] Створив би: {product.name} ({product.article_code}) — {product.price} грн")
                stats["created"] += 1
                continue

            furniture = Furniture.objects.create(
                name=product.name,
                article_code=product.article_code,
                slug=_generate_slug(product.name),
                sub_category=sub_category,
                price=product.price,
                description=product.description or product.name,
                stock_status="in_stock",
            )

            # Parameters
            for param_label, param_value in product.params.items():
                if not param_label or not param_value:
                    continue
                key = slugify(param_label)[:100] or f"param_{abs(hash(param_label))}"
                param, _ = Parameter.objects.get_or_create(key=key, defaults={"label": param_label})
                if not sub_category.allowed_params.filter(pk=param.pk).exists():
                    sub_category.allowed_params.add(param)
                FurnitureParameter.objects.update_or_create(
                    furniture=furniture,
                    parameter=param,
                    defaults={"value": param_value},
                )

            # Images
            for img_idx, img_url in enumerate(product.image_urls):
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

            self._log(f"  Додано: {furniture.name} ({furniture.article_code})")
            stats["created"] += 1

        stats["success"] = True
        return stats

    # ── Price update ──────────────────────────────────────────────────────────

    def update_prices(self) -> Dict:
        """Scrape catalog pages and update prices for existing Furniture by article_code."""
        from furniture.models import Furniture

        self._log("Збираємо актуальні ціни з kreslalux.ua...")

        # Build article_code → furniture map
        furniture_map: Dict[str, Furniture] = {}
        for f in Furniture.objects.filter(
            sub_category__slug="ortopedichni-krisla"
        ).only("id", "name", "article_code", "price"):
            if f.article_code:
                furniture_map[f.article_code.strip()] = f

        if not furniture_map:
            return {"success": False, "error": "Немає товарів у підкатегорії ортопедичні крісла"}

        self._log(f"Товарів для оновлення: {len(furniture_map)}")

        first_soup = self._get(CATALOG_URL)
        if not first_soup:
            return {"success": False, "error": "Не вдалося отримати каталог"}

        total_pages = self._detect_total_pages(first_soup)

        stats = {"checked": 0, "updated": 0, "not_found": 0, "errors": []}

        def _process_page_products(products: List[Dict]) -> None:
            for p in products:
                if not p.get("sku") or p["price"] is None:
                    # Need to fetch detail page for SKU if not available on listing
                    continue
                furniture = furniture_map.get(p["sku"])
                if not furniture:
                    stats["not_found"] += 1
                    continue
                stats["checked"] += 1
                if furniture.price != p["price"] and p["price"] > 0:
                    furniture.price = p["price"]
                    furniture.save(update_fields=["price"])
                    self._log(f"  {furniture.name}: {p['price']} грн")
                    stats["updated"] += 1

        _process_page_products(self._scrape_catalog_page(CATALOG_URL))

        for page in range(2, total_pages + 1):
            time.sleep(REQUEST_DELAY)
            page_url = f"{CATALOG_URL}?page={page}"
            products = self._scrape_catalog_page(page_url)
            if not products:
                break
            _process_page_products(products)

        # For products whose SKU wasn't found via listing, try detail pages
        found_skus = {p["sku"] for p in self._scrape_catalog_page(CATALOG_URL) if p.get("sku")}
        missing = {sku: f for sku, f in furniture_map.items() if sku not in found_skus}

        for sku, furniture in missing.items():
            time.sleep(REQUEST_DELAY)
            # Search by name on detail pages — try to find by scraping
            # For now, log as not found
            stats["not_found"] += 1

        stats["success"] = True
        return stats
