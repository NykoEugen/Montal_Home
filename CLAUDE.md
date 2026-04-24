# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development
make run               # Dev server → http://localhost:8000
make shell             # Django interactive shell

# Database
make makemigrations    # Generate migration files
make migrate           # Apply migrations
make setupdb           # makemigrations + migrate (first-time setup)

# Code quality
make lint              # isort check + black check + mypy (all must pass before commit)
make autofmt           # isort + black auto-fix
make precommit         # autofmt + lint + test

# Testing
make test                                  # All tests
python manage.py test furniture.tests      # Single app
python manage.py test price_parser.tests

# Production
make production        # clean + collectstatic + migrate
```

Settings module: `store.settings` (defined in `pytest.ini`).

## Required `.env` variables

```env
SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=postgresql://user:pass@localhost:5432/montal_home
NOVA_POSHTA_API_KEY=...
LIQPAY_PUB_KEY=...         # optional, disables LiqPay if missing
LIQPAY_SECRET_KEY=...
```

Optional: `REDIS_URL`, `USE_CDN_STATIC`, `STATIC_CDN_URL`, `STATICFILES_BUCKET_NAME`.

---

## Architecture overview

### App map

| App | Path prefix | Purpose |
|---|---|---|
| `store/` | — | Project config, root urls, middleware, sitemaps |
| `furniture/` | `/furniture/` | Product catalog — core domain |
| `categories/` | `/catalogue/` | Top-level categories |
| `sub_categories/` | `/sub-categories/` | Second-level categories |
| `fabric_category/` | — | Material/upholstery brands, palettes, colors |
| `params/` | — | Generic parameter specs per sub-category |
| `shop/` | `/` | Storefront, cart, seasonal decoration toggle |
| `checkout/` | `/checkout/` | Orders, LiqPay payments, SalesDrive CRM, invoice PDF |
| `delivery/` | `/delivery/` | Nova Poshta API (city search, warehouses) |
| `price_parser/` | `/price-parser/` | Automated price updates (three strategies) |
| `custom_admin/` | `/custom-admin/` | Custom staff UI (separate from `/admin/`) |
| `seasonal/` | — | Holiday decoration toggle (singleton model) |
| `utils/` | — | Image variants, media paths, phone validation, R2 storage |

---

## Key models and relationships

### Product catalog

```
Category → SubCategory → Furniture
                              ├── FurnitureSizeVariant (per-size price, foldable flag)
                              ├── FurnitureVariantImage (color/style variants)
                              ├── FurnitureImage (gallery)
                              ├── FurnitureParameter (FK to params.Parameter)
                              ├── FurnitureCustomOption (selectable add-ons with price_delta)
                              ├── selected_fabric_brand → FabricBrand
                              └── color_palettes (M2M) → FabricColorPalette → FabricColor
```

**`Furniture` key fields:**
- `article_code` — unique SKU, used for price feed matching
- `price` — base price; `is_promotional` + `promotional_price` + `sale_end_date` for timed sales
- `fabric_value` — multiplier applied when a FabricCategory is chosen
- `stock_status` — `in_stock` | `on_order`
- Properties: `current_price`, `is_sale_active`, `best_promotional_price`, `discount_percentage`

**`FurnitureSizeVariant`** has its own independent promotional pricing (same fields as Furniture). When selected, its `price` replaces base `Furniture.price`. If a size variant links to a `Parameter`, it overrides that parameter value on the detail page.

**`FurnitureCustomOption`** — selectable extras (e.g., "headrest"). Has `price_delta` added to total.

### Pricing formula (product detail → cart → order)

```
base = size_variant.price  (or furniture.price if no variant)
      → apply promotional if active
+ fabric_category.price * furniture.fabric_value
+ custom_option.price_delta
= item_total
```

### Order / Cart

**Session cart key format:**
```
"{furniture_id}_size_{variant_id}_fabric_{fabric_id}_variant_{variant_img_id}_custom_{option_id}"
```
Cart value is a dict with: `quantity`, `size_variant_id`, `fabric_category_id`, `custom_option_id/value/price`, `color_id/name/palette_name`.

**`Order`** — customer info, delivery type (`novaposhta` | `local`), payment type (`iban` | `liqpay`), invoice PDF lifecycle fields.

**`OrderItem`** — snapshot of price at order time. Stores `size_variant_id`, `fabric_category_id`, `variant_image_id`, `color_id/name/hex`, `custom_option` FK. Has cached property accessors to avoid N+1.

---

## Price parser subsystem (`price_parser/`)

Three independent strategies, each has a `Config` model + `UpdateLog` model + service class in `services.py`:

| Strategy | Config model | Service class | Trigger |
|---|---|---|---|
| Google Sheets / XLSX | `GoogleSheetConfig` | `GoogleSheetsPriceUpdater` | `update_prices` management command or custom admin button |
| Supplier XML/YML feed | `SupplierFeedConfig` | `SupplierFeedUpdater` | `import_supplier_furniture` command or admin button |
| Web scraping | `SupplierWebConfig` | `SupplierWebUpdater` | Custom admin button |

**XML feed import** (`import_supplier_furniture`): matches offers by `<model>` (article_code) then `<name>`. Multiple offers with same name but different `<param name="Готові кольорові рішення">` become `FurnitureVariantImage` under one `Furniture`. Profiles: `--profile furniture|mattresses|chairs`.

**Web scraper**: crawls `robots.txt` → `sitemap.xml`, extracts prices via CSS selector (`price_block_selector` field). `del` tag = base price, `ins` tag = promotional; optionally uses Selenium for JS-rendered prices.

**Google Sheets**: downloads as CSV (public share URL → `export?format=csv`), maps rows to `Furniture` via `FurniturePriceCellMapping` (explicit row+column → furniture FK).

---

## External integrations

### LiqPay (`checkout/liqpay.py`)
Minimal in-house SDK (no PyPI package). Base64+SHA1 signature. Order ID sent as `"MONTAL-{order.id}"`. Sandbox controlled by `LIQPAY_SANDBOX` env var.

### SalesDrive CRM (`checkout/salesdrive.py`)
Submits order on creation. Graceful: logs but never fails the order if CRM is down. Cleans phone to digits only.

### Nova Poshta (`delivery/views.py`)
- `search_city()` / `autocomplete_city()` — city autocomplete (12h cache)
- `get_warehouses()` — warehouse list for selected city ref
- Warehouse type filtering via `CARGO_WAREHOUSE_REF` setting

### Static files
- **Dev**: WhiteNoise serves `static/` / `staticfiles/`
- **Prod**: `USE_CDN_STATIC=True` → `R2StaticStorage` (Cloudflare R2) + BunnyCDN (`cdn.montal.com.ua`)

---

## Custom admin (`custom_admin/`)

Staff-only UI at `/custom-admin/`. Registry-based: sections (furniture, orders, categories, etc.) map to model + form + formsets. Provides:
- Inline formsets for size variants, custom options, parameters, images, variant images
- Bulk price update buttons (triggers each price_parser service)
- Invoice PDF generation for orders
- Supplier feed "Test parse" / "Update prices" buttons

**Important**: This is the primary day-to-day management UI, not Django's `/admin/`.

---

## Middleware (`store/middleware.py`)

Three custom middleware classes:
1. **ConnectionResilienceMiddleware** — DB health check with circuit breaker (CLOSED → OPEN → HALF_OPEN)
2. **PostRequestResilienceMiddleware** — saves POST form drafts to session if DB write fails
3. **AdminConnectionMonitorMiddleware** — injects DB status banner in admin

---

## Image system (`utils/`)

**`image_variants.py`**: After saving an image field, generates responsive WebP variants (400w, 800w, 1200w) in a background thread (post-transaction commit). EXIF orientation and alpha transparency handled automatically.

**`media_paths.py`**: Upload paths use slug + timestamp + UUID to avoid collisions.
Example: `furniture/{slug}/main_{uuid}_{timestamp}.webp`

---

## Useful management commands

```bash
python manage.py setup_jem_config              # Create Google Sheets config
python manage.py update_prices                 # Run Google Sheets price update
python manage.py setup_matroluxe_supplier_feed # Create XML feed config
python manage.py ensure_corpus_subcategories   # Create corpus furniture subcategories
python manage.py ensure_mattress_subcategories # Create mattress subcategories
python manage.py ensure_chair_subcategories    # Create chair subcategories
python manage.py import_supplier_furniture \   # Import from XML feed
  --feed-file path.xml --profile furniture|mattresses|chairs [--dry-run] [--limit N]
```

---

## What to watch out for

- **Promotional pricing is multi-level**: `Furniture` and each `FurnitureSizeVariant` independently can be on sale. Always check `is_sale_active` property, not just `is_promotional`.
- **Cart key parsing**: The compound session key encodes all product configuration. Changing its format breaks existing sessions.
- **Article code is the price-feed anchor**: `Furniture.article_code` must match `<model>` in XML feeds. Don't change it without updating the feed or remapping.
- **Size variant overrides parameter**: If a `FurnitureSizeVariant` has a linked `Parameter`, the variant's `parameter_value` is shown instead of the base furniture's parameter — don't lose this on edits.
- **SalesDrive is fire-and-forget**: Errors are logged but don't block order creation. Check logs if CRM orders are missing.
- **Image generation is async**: Images may not have WebP variants immediately after upload; the background thread handles it post-commit.
