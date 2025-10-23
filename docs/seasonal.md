# Seasonal Campaigns Module

This module powers the “seasonal” app: a pluggable system for targeting, rendering, and managing limited-time UI campaigns (Halloween banners, holiday badges, etc.). It couples Django models, pack abstractions, template tags, and static bundles to deliver themed experiences safely.

---

## Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add to Django settings**
   `store/settings.py` already includes `seasonal.apps.SeasonalConfig` in `INSTALLED_APPS` and `seasonal.context_processors.active_packs` in `TEMPLATES[OPTIONS][context_processors]`. Double-check they remain present.

3. **Run migrations**
   ```bash
   python manage.py migrate seasonal
   ```

4. **Scaffold a campaign**
   ```bash
   python manage.py seasonal create ny2026 --title "New Year 2026" --start 2025-12-15 --end 2026-01-10 --priority 25
   ```
   This generates:
   - `seasonal/packs/ny2026/pack.py` (`PackImpl` class)
   - Static assets under `static/seasonal/ny2026/`
   - Stub templates under `templates/seasonal/ny2026/partials/`
   - A `SeasonalCampaign` row referencing `seasonal.packs.ny2026.pack:PackImpl`

5. **Customize templates & assets**
   - Update `pack.py` with real context, static bundles, and partial mapping.
   - Edit generated CSS/JS and the header/sidebar/footer partials.
   - Optional: add automated tests alongside `seasonal/tests/`.

6. **Enable in admin**
   - Visit `/admin/seasonal/seasonalcampaign/`
   - Toggle “enabled”, confirm schedule, and adjust rollout/country/device filters.

---

## Rendering Pipeline

### Context Processor
`seasonal.context_processors.active_packs` collects active `SeasonalCampaign` entries for the current request. It:
- Applies schedule (start/end) and enabled filters.
- Checks path (`fnmatch`), country/device (from `request.META`), and percentage rollout via salted hashing (`seasonal.ab.bucket_user`).
- Instantiates each pack (`seasonal.utils.loader.load_pack`) and calls `pack.ensure_request()` to respect opt-out cookies.
- Aggregates deduplicated asset bundles under `seasonal_assets` (`css`, `js` lists) to avoid duplicate `<link>/<script>` tags.

### Template Tags & Blocks
- `{% render_seasonal "region" %}` renders all packs for a region (`"header"`, `"sidebar"`, `"footer"`, etc.).
- Base layout (`templates/shop/base.html`) defines seasonal blocks:  
  `seasonal_css`, `seasonal_header`, `seasonal_sidebar`, `seasonal_footer`, `seasonal_js`.
- Shared include `templates/seasonal/loader.html` preloads CSS and defers JS, consuming `seasonal_assets`.

---

## Pack Interface

`seasonal/packs/base.py` provides `Pack` (dataclass + ABC) with lifecycle methods:
- `bind(campaign)` – attach model metadata.
- `ensure_request(request)` – run once-per-request initialization.
- `is_active(now)` – respects schedule and user opt-out.
- `render(region, request, extra_context)` – loads the region template, merges context, and returns HTML.
- Abstract hooks: `get_context`, `get_static_bundles`, `get_partial_template`, optional `on_request`.

Example: `seasonal/packs/halloween_2025/pack.py` demonstrates:
- Cloudinary-aware imagery via `seasonal.media.get_media_url`.
- Opt-out handling (removing animations when the `seasonal_opt_out` cookie is present).
- Shared animation controls script `static/seasonal/controls.js`.

---

## Targeting & Rollouts

- **Bucketing** (`seasonal/ab.py`): Derives a stable hash using an `sid` cookie (preferred) or `User-Agent + IP`; salted with campaign slug for consistent percentage rollouts.
- **Matchers** (`seasonal/matchers.py`): Helpers for `fnmatch` path filtering, country lookup (`HTTP_CF_IPCOUNTRY`, GeoIP fallback), and device detection (`HTTP_X_DEVICE`, etc.).
- **Opt-out**: Users can click `.seasonal-optout` buttons (provided by packs) to persist `seasonal_opt_out=1` for 30 days; animation data attributes are stripped accordingly.

---

## Assets & Cloudinary Integration

- `seasonal/media.get_media_url("halloween_2025/images/spiderweb.svg")` picks Cloudinary URLs when `settings.CLOUDINARY_STORAGE` is configured and `cloudinary` package is available; otherwise, it falls back to Django `static()`. This lets packs reference heavy media without code changes between dev/prod.
- Sample assets in `static/seasonal/halloween_2025/` include CSS, JS, and SVG iconography; update with campaign-specific files.

---

## Management Command

`python manage.py seasonal create <slug> [options]`

| Option       | Description                                   |
|--------------|-----------------------------------------------|
| `--title`    | Human-readable campaign name (required)       |
| `--start`    | ISO date/datetime (`YYYY-MM-DD` or ISO8601)   |
| `--end`      | ISO date/datetime                             |
| `--priority` | Higher numbers display first (default `0`)    |

Generated files contain TODO comments and placeholders—replace them with live assets and content.

---

## Testing

Pytest suites live under `seasonal/tests/`:
- `test_loader.py` – pack loading, attribute import, opt-out handling.
- `test_template_tags.py` – template rendering for registered packs.
- `test_context_processors.py` – bundle deduplication and active pack aggregation.
- `test_ab.py`, `test_matchers.py`, `test_media.py` – rollout bucketing, targeting filters, media helper fallbacks.

Run:
```bash
pytest seasonal/tests
```
> Note: Requires Python 3.12 (as per `.python-version`). Install with `pyenv install 3.12.1` or adjust configuration.

---

## Common Tasks

- **Add a new region**: Extend pack templates (e.g., create `templates/seasonal/my_pack/partials/banner.html`), update `get_partial_template` mapping, and insert `{% render_seasonal "banner" %}` where needed.
- **Customize opt-out behavior**: Modify shared script (`static/seasonal/controls.js`) or pack-specific JS/CSS.
- **Target specific audiences**: Set `path_glob`, `country`, `device`, or `percentage_rollout` on the `SeasonalCampaign` record.
- **Cloudinary asset swap**: Upload image/video to Cloudinary, then reference via `get_media_url("pack_slug/path.ext")`.

---

## Troubleshooting

- **TemplateSyntaxError: `default requires 2 arguments`** – ensure `default` isn’t applied to dict/list contexts; the provided `loader.html` already handles this edge case.
- **Missing pack assets** – verify `get_static_bundles` references existing files and run `collectstatic` in production.
- **Pack not visible** – check `enabled`, schedule, rollout percentage, targeting filters, and confirm `render_seasonal` is called for that region.
- **Opt-out ineffective** – ensure `.seasonal-optout` class exists on buttons and that `seasonal/controls.js` is delivered via `seasonal_js` block.

---

## Contributing

1. Create branch, implement changes across packs/app/helpers.
2. Add/update tests under `seasonal/tests`.
3. Run `pytest seasonal/tests`.
4. Update documentation if new features or configuration steps are introduced.

For major additions (e.g., new targeting matchers or middleware), extend this document with clear usage instructions.

