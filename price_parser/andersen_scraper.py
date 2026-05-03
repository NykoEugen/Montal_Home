import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit, urljoin

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify

logger = logging.getLogger(__name__)

BASE_URL = "https://andersen.ua"
REQUEST_DELAY = 0.8
IMAGE_CACHE_DIR = "supplier_cache/andersen"

CATALOG_CONFIGS: Dict[str, Dict] = {
    "matratsy": {
        "url": "https://andersen.ua/product-category/matratsy/",
        "subcategory_name": "Матраци (Andersen)",
        "subcategory_slug": "matracy-andersen",
        "category_name": "Матраци",
    },
    "podushky": {
        "url": "https://andersen.ua/product-category/podushky/",
        "subcategory_name": "Подушки",
        "subcategory_slug": "podushky-andersen",
        "category_name": "Матраци",
    },
    "namatratsnyky": {
        "url": "https://andersen.ua/product-category/namatratsnyky/",
        "subcategory_name": "Наматрацники",
        "subcategory_slug": "namatratsnyky-andersen",
        "category_name": "Матраци",
    },
}

CYRILLIC_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e",
    "є": "ie", "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "yi", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ь": "", "ю": "yu", "я": "ya",
}

# Розміри-суфікси які WP генерує для thumbnails
_WP_SIZE_RE = re.compile(r"-\d+x\d+(\.[a-z]+)$", re.I)


@dataclass
class SizeOption:
    label: str
    variation_id: str
    regular_price: Decimal
    sale_price: Optional[Decimal]  # None = не акційна


@dataclass
class AndersenProduct:
    url: str
    name: str
    article_code: str
    description: str = ""
    sizes: List[SizeOption] = field(default_factory=list)
    price: Optional[Decimal] = None       # flat price (якщо нема розмірів)
    sale_price: Optional[Decimal] = None
    image_urls: List[str] = field(default_factory=list)
    params: Dict[str, str] = field(default_factory=dict)


def _transliterate(value: str) -> str:
    return "".join(CYRILLIC_MAP.get(ch.lower(), ch) for ch in value)


def _parse_price(text: str) -> Optional[Decimal]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d]", "", text.replace("\xa0", "").replace(",", "").replace(".", ""))
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_size(label: str) -> Optional[Tuple[int, int]]:
    """'90*200' або '160*200*22см' → (width, length)."""
    m = re.match(r"(\d+)\s*[*xхХ×]\s*(\d+)", label.strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _thumbnail_to_full(url: str) -> str:
    """Знімає WP-thumbnail суфікс: 'img-150x150.jpg' → 'img.jpg'."""
    m = _WP_SIZE_RE.search(url)
    if m:
        ext = m.group(1)
        return url[: m.start()] + ext
    return url


def _generate_slug(name: str) -> str:
    from furniture.models import Furniture
    base = slugify(_transliterate(name)) or "andersen"
    slug = base
    suffix = 1
    while Furniture.objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


class AndersenScraper:
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

    def collect_product_urls(self, catalog_key: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Сайт andersen.ua — кастомна WP-тема, всі товари на одній сторінці.
        Селектор: .product_page_list a[href*="/product/"]
        """
        config = CATALOG_CONFIGS[catalog_key]
        url = config["url"]
        self._log(f"Збираємо товари з {url}")

        soup = self._get(url)
        if not soup:
            self._log("ПОМИЛКА: сторінка недоступна")
            return []

        products = []
        for card in soup.select('.product_page_list a[href*="/product/"]'):
            product_url = card.get("href", "")
            if not product_url:
                continue
            if not product_url.startswith("http"):
                product_url = urljoin(BASE_URL, product_url)

            h = card.find(["h3", "h2", "h4"])
            name = h.get_text(strip=True) if h else card.get_text(strip=True)[:80]

            products.append({"url": product_url, "name": name})
            if limit and len(products) >= limit:
                break

        self._log(f"Знайдено: {len(products)} товарів")
        return products

    # ── Product detail ────────────────────────────────────────────────────────

    def scrape_product(self, url: str) -> Optional[AndersenProduct]:
        soup = self._get(url)
        if not soup:
            return None

        # Назва — перший h2 (не заголовок відгуків)
        name = ""
        for h2 in soup.find_all("h2"):
            cls = h2.get("class") or []
            if "woocommerce-Reviews-title" not in cls:
                name = h2.get_text(strip=True)
                break
        if not name:
            return None

        # Article code — зі shortlink (?p=NNN)
        article_code = ""
        shortlink = soup.select_one("link[rel='shortlink']")
        if shortlink:
            m = re.search(r"[?&]p=(\d+)", shortlink.get("href", ""))
            if m:
                article_code = f"AND-{m.group(1)}"
        if not article_code:
            digest = hashlib.md5(url.encode()).hexdigest()[:8]
            article_code = f"AND-{digest}"

        # Розмірні варіанти
        sizes = self._parse_size_options(soup)

        # Опис з .product_info_block
        description = ""
        info_block = soup.select_one(".product_info_block")
        if info_block:
            description = info_block.get_text(separator="\n", strip=True)

        # Параметри — парсимо .product_info_block як пари ключ:значення
        params = self._parse_params(info_block) if info_block else {}

        # Зображення
        image_urls = self._extract_images(soup)

        # Flat price (якщо нема розмірів)
        # Використовуємо точні класи .regular_price / .sale_price щоб уникнути
        # захоплення батьківських блоків з кількома цінами підряд
        flat_price = None
        flat_sale = None
        if not sizes:
            pc = soup.select_one(".product_charactristik")
            if pc:
                reg_el = pc.select_one(".regular_price")
                sale_el = pc.select_one(".sale_price")
                flat_price = _parse_price(reg_el.get_text(strip=True)) if reg_el else None
                flat_sale = _parse_price(sale_el.get_text(strip=True)) if sale_el else None

                if flat_price is None:
                    # .regular_price порожній — ціна є тільки в .sale_price, знижки нема
                    flat_price = flat_sale
                    flat_sale = None
                elif flat_sale is not None and flat_sale >= flat_price:
                    flat_sale = None

        return AndersenProduct(
            url=url,
            name=name,
            article_code=article_code,
            description=description,
            sizes=sizes,
            price=flat_price,
            sale_price=flat_sale,
            image_urls=image_urls,
            params=params,
        )

    def _parse_size_options(self, soup: BeautifulSoup) -> List[SizeOption]:
        sizes = []
        for inp in soup.select(".size-options .size-option input[type=radio]"):
            label = inp.get("value", "").strip()
            variation_id = inp.get("data-variation-id", "").strip()
            regular_str = inp.get("data-regular-price", "").strip()
            sale_str = inp.get("data-sale-price", "").strip()

            if not variation_id:
                continue
            regular = _parse_price(regular_str)
            if regular is None:
                continue

            sale = _parse_price(sale_str)
            if sale is not None and sale >= regular:
                sale = None

            sizes.append(SizeOption(
                label=label,
                variation_id=variation_id,
                regular_price=regular,
                sale_price=sale,
            ))
        return sizes

    def _parse_params(self, info_block) -> Dict[str, str]:
        """
        .product_info_block містить пари 'Ключ:|Значення|' через |.
        Парсимо в словник.
        """
        params = {}
        items = info_block.get_text(separator="|", strip=True).split("|")
        i = 0
        while i < len(items) - 1:
            key = items[i].rstrip(":").strip()
            val = items[i + 1].strip()
            if key and val and not val.startswith("|"):
                params[key] = val
                i += 2
            else:
                i += 1
        return params

    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """
        Структура: div.slider > div.main-image > img (повний розмір)
                   div.slider > div.thumbnails > img (150x150, конвертуємо у full)
        """
        image_urls: List[str] = []
        seen: set = set()

        def _add(src: str) -> None:
            if not src or src in seen:
                return
            seen.add(src)
            image_urls.append(src)

        slider = soup.select_one("div.slider")
        if slider:
            # Головне фото
            main_img = slider.select_one(".main-image img")
            if main_img:
                _add(main_img.get("src") or "")

            # Галерея — конвертуємо thumbnail→full
            for img in slider.select(".thumbnails img"):
                src = img.get("src") or ""
                if src:
                    _add(_thumbnail_to_full(src))

        # Fallback: перший img без класу в uploads
        if not image_urls:
            for img in soup.select("img"):
                src = img.get("src") or ""
                if "wp-content/uploads" in src and not img.get("class"):
                    _add(_thumbnail_to_full(src))
                    if len(image_urls) >= 3:
                        break

        return image_urls

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

    # ── Subcategory auto-create ───────────────────────────────────────────────

    def _ensure_subcategory(self, catalog_key: str):
        from categories.models import Category
        from sub_categories.models import SubCategory

        config = CATALOG_CONFIGS[catalog_key]
        category = Category.objects.filter(name=config["category_name"]).first()
        if not category:
            raise RuntimeError(
                f"Категорія '{config['category_name']}' не знайдена в БД."
            )

        sub, created = SubCategory.objects.get_or_create(
            slug=config["subcategory_slug"],
            defaults={
                "name": config["subcategory_name"],
                "category": category,
            },
        )
        if created:
            self._log(f"Створено підкатегорію: {sub.name} ({sub.slug})")
        return sub

    # ── Import ────────────────────────────────────────────────────────────────

    def run_import(
        self,
        catalog_key: str,
        dry_run: bool = False,
        limit: Optional[int] = None,
    ) -> Dict:
        from furniture.models import Furniture, FurnitureImage, FurnitureSizeVariant
        from params.models import FurnitureParameter, Parameter

        sub_category = self._ensure_subcategory(catalog_key)

        candidates = self.collect_product_urls(catalog_key, limit=limit)
        self._log(f"Обробляємо {len(candidates)} товарів...")

        stats = {
            "created": 0, "updated": 0, "skipped": 0,
            "candidates": len(candidates), "errors": [],
        }

        for idx, candidate in enumerate(candidates, 1):
            self._log(f"[{idx}/{len(candidates)}] {candidate['name']}")
            time.sleep(REQUEST_DELAY)

            product = self.scrape_product(candidate["url"])
            if not product:
                stats["errors"].append(f"Не вдалося завантажити: {candidate['url']}")
                stats["skipped"] += 1
                continue

            existing = Furniture.objects.filter(article_code=product.article_code).first()

            if existing:
                changed = self._update_existing(existing, product, dry_run)
                if changed:
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
                continue

            if dry_run:
                sizes_info = f", {len(product.sizes)} розмірів" if product.sizes else ""
                self._log(
                    f"  [DRY-RUN] {product.name} ({product.article_code}){sizes_info}"
                )
                stats["created"] += 1
                continue

            base_price = self._base_price(product)
            furniture = Furniture.objects.create(
                name=product.name,
                article_code=product.article_code,
                slug=_generate_slug(product.name),
                sub_category=sub_category,
                price=base_price,
                description=product.description or product.name,
                stock_status="in_stock",
            )

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

            self._create_size_variants(furniture, product.sizes)
            self._sync_promo_to_furniture(furniture, product)
            self._save_images(furniture, product.image_urls)

            self._log(
                f"  Створено: {furniture.name} ({furniture.article_code})"
                + (f", {len(product.sizes)} розмірів" if product.sizes else "")
            )
            stats["created"] += 1

        stats["success"] = True
        return stats

    def _sync_promo_to_furniture(self, furniture, product: AndersenProduct) -> None:
        """
        Синхронізує Furniture.is_promotional / promotional_price з даних продукту,
        щоб бейдж зі знижкою відображався в каталозі (шаблон перевіряє ці поля).

        Для розмірних варіантів: беремо варіант з мінімальною ціною (він же є
        базовою ціною Furniture) і копіюємо його акційну інформацію.
        Для flat-price товарів: використовуємо sale_price безпосередньо.
        """
        if product.sizes:
            # Знайдемо розмір з мінімальною regular_price
            cheapest = min(product.sizes, key=lambda s: s.regular_price)
            is_promo = cheapest.sale_price is not None
            promo_price = cheapest.sale_price if is_promo else None
        else:
            is_promo = product.sale_price is not None
            promo_price = product.sale_price if is_promo else None

        fields = []
        if furniture.is_promotional != is_promo:
            furniture.is_promotional = is_promo
            fields.append("is_promotional")
        if furniture.promotional_price != promo_price:
            furniture.promotional_price = promo_price
            fields.append("promotional_price")
        if fields:
            furniture.save(update_fields=fields)

    def _base_price(self, product: AndersenProduct) -> Decimal:
        if product.sizes:
            prices = [s.regular_price for s in product.sizes if s.regular_price]
            return min(prices) if prices else Decimal("0")
        return product.price or Decimal("0")

    def _create_size_variants(self, furniture, sizes: List[SizeOption]) -> None:
        from furniture.models import FurnitureSizeVariant

        for size in sizes:
            dims = _parse_size(size.label)
            width, length = dims if dims else (0, 0)
            is_promo = size.sale_price is not None

            FurnitureSizeVariant.objects.update_or_create(
                furniture=furniture,
                vendor_code=size.variation_id,
                defaults={
                    "height": 0,
                    "width": width,
                    "length": length,
                    "price": size.regular_price,
                    "promotional_price": size.sale_price if is_promo else None,
                    "is_promotional": is_promo,
                    "parameter_value": size.label,
                },
            )

    def _update_existing(self, furniture, product: AndersenProduct, dry_run: bool) -> bool:
        from furniture.models import FurnitureSizeVariant

        changed = False

        if product.sizes:
            for size in product.sizes:
                variant = FurnitureSizeVariant.objects.filter(
                    furniture=furniture,
                    vendor_code=size.variation_id,
                ).first()

                if variant:
                    fields = []
                    if variant.price != size.regular_price:
                        if not dry_run:
                            variant.price = size.regular_price
                        fields.append("price")
                    is_promo = size.sale_price is not None
                    if variant.promotional_price != size.sale_price or variant.is_promotional != is_promo:
                        if not dry_run:
                            variant.promotional_price = size.sale_price
                            variant.is_promotional = is_promo
                        fields.extend(["promotional_price", "is_promotional"])
                    if fields:
                        if not dry_run:
                            variant.save(update_fields=fields)
                        self._log(
                            f"  Оновлено {size.label}: {size.regular_price}"
                            + (f" (акція: {size.sale_price})" if size.sale_price else "")
                        )
                        changed = True
                else:
                    # Новий розмір з'явився
                    if not dry_run:
                        dims = _parse_size(size.label)
                        width, length = dims if dims else (0, 0)
                        FurnitureSizeVariant.objects.create(
                            furniture=furniture,
                            vendor_code=size.variation_id,
                            height=0,
                            width=width,
                            length=length,
                            price=size.regular_price,
                            promotional_price=size.sale_price,
                            is_promotional=size.sale_price is not None,
                            parameter_value=size.label,
                        )
                    self._log(f"  Новий розмір: {size.label}")
                    changed = True
        else:
            new_price = product.price or Decimal("0")
            if new_price and furniture.price != new_price:
                if not dry_run:
                    furniture.price = new_price
                    furniture.save(update_fields=["price"])
                self._log(f"  Оновлено ціну: {new_price}")
                changed = True

        # Синхронізуємо бейдж знижки на батьківській Furniture
        if not dry_run:
            self._sync_promo_to_furniture(furniture, product)

        if not furniture.image and product.image_urls:
            if not dry_run:
                self._save_images(furniture, product.image_urls)
            self._log(f"  Додано картинки")
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

    # ── Price update (fast path) ──────────────────────────────────────────────

    def update_prices(self, catalog_key: str) -> Dict:
        from furniture.models import Furniture, FurnitureSizeVariant

        config = CATALOG_CONFIGS[catalog_key]
        self._log(f"Оновлення цін: {config['subcategory_name']}")

        variant_map: Dict[str, FurnitureSizeVariant] = {
            v.vendor_code: v
            for v in FurnitureSizeVariant.objects.filter(
                furniture__sub_category__slug=config["subcategory_slug"]
            ).select_related("furniture")
            if v.vendor_code
        }

        flat_map: Dict[str, Furniture] = {
            f.article_code: f
            for f in Furniture.objects.filter(
                sub_category__slug=config["subcategory_slug"]
            ).only("id", "article_code", "price")
            if f.article_code
        }

        if not variant_map and not flat_map:
            self._log("  Немає товарів — спочатку запустіть import")

        candidates = self.collect_product_urls(catalog_key)
        stats = {"checked": 0, "updated": 0, "not_found": 0, "errors": []}

        for idx, candidate in enumerate(candidates, 1):
            self._log(f"[{idx}/{len(candidates)}] {candidate['name']}")
            time.sleep(REQUEST_DELAY)

            product = self.scrape_product(candidate["url"])
            if not product:
                stats["errors"].append(f"Не вдалося: {candidate['url']}")
                continue

            if product.sizes:
                furniture_updated = False
                for size in product.sizes:
                    variant = variant_map.get(size.variation_id)
                    if not variant:
                        stats["not_found"] += 1
                        continue
                    stats["checked"] += 1
                    fields = []
                    if variant.price != size.regular_price:
                        variant.price = size.regular_price
                        fields.append("price")
                    is_promo = size.sale_price is not None
                    if variant.promotional_price != size.sale_price or variant.is_promotional != is_promo:
                        variant.promotional_price = size.sale_price
                        variant.is_promotional = is_promo
                        fields.extend(["promotional_price", "is_promotional"])
                    if fields:
                        variant.save(update_fields=fields)
                        self._log(
                            f"  {size.label}: {size.regular_price}"
                            + (f" → акція {size.sale_price}" if size.sale_price else "")
                        )
                        stats["updated"] += 1
                        furniture_updated = True
                # Синхронізуємо бейдж знижки на батьківській Furniture
                if furniture_updated:
                    first_variant = next(iter(variant_map.values()), None)
                    if first_variant:
                        self._sync_promo_to_furniture(first_variant.furniture, product)
            else:
                furniture = flat_map.get(product.article_code)
                if not furniture:
                    stats["not_found"] += 1
                    continue
                new_price = product.price or Decimal("0")
                updated = False
                if new_price and furniture.price != new_price:
                    furniture.price = new_price
                    furniture.save(update_fields=["price"])
                    self._log(f"  {furniture.article_code}: {new_price}")
                    stats["updated"] += 1
                    updated = True
                if updated:
                    self._sync_promo_to_furniture(furniture, product)
                stats["checked"] += 1

        stats["success"] = True
        return stats
