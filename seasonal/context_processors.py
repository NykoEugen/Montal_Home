from __future__ import annotations

import logging
from typing import Dict, List

from django.utils import timezone

from .models import SeasonalCampaign
from .packs.base import Pack
from .utils.loader import load_pack, PackImportError

logger = logging.getLogger(__name__)


def active_packs(request) -> Dict[str, List[Pack]]:
    """Expose the list of active seasonal packs filtered against the request."""
    now = timezone.now()
    campaigns = SeasonalCampaign.objects.filter(
        enabled=True, starts_at__lte=now, ends_at__gte=now
    ).order_by("-priority", "-starts_at")

    packs: List[Pack] = []
    css_files: List[str] = []
    js_files: List[str] = []
    seen_css: set[str] = set()
    seen_js: set[str] = set()

    for campaign in campaigns:
        if not campaign.matches_request(request):
            continue

        try:
            pack = load_pack(campaign.pack_path).bind(campaign)
            pack.ensure_request(request)
            if not pack.is_active(now):
                continue
            bundles = pack.get_static_bundles() or {}
            if not isinstance(bundles, dict):
                logger.warning("Pack %s returned invalid bundles (%s)", campaign.slug, type(bundles))
                bundles = {}
        except PackImportError:
            logger.warning("Failed to load seasonal pack", exc_info=True, extra={"campaign": campaign.slug})
            continue
        except Exception:
            logger.exception("Unexpected error preparing pack %s", campaign.slug)
            continue

        for css in bundles.get("css", []):
            if css not in seen_css:
                seen_css.add(css)
                css_files.append(css)

        for js in bundles.get("js", []):
            if js not in seen_js:
                seen_js.add(js)
                js_files.append(js)

        packs.append(pack)

    return {
        "seasonal_packs": packs,
        "seasonal_assets": {"css": css_files, "js": js_files},
    }
