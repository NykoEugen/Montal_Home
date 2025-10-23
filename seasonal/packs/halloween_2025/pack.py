from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, Optional

from django.utils import timezone

from seasonal.media import get_media_url
from seasonal.packs.base import Pack


@dataclass
class Halloween2025Pack(Pack):
    slug: str = "halloween-2025"
    name: str = "Halloween 2025"
    version: str = "2025.10"
    priority: int = 50
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    _opted_out: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.starts_at is None:
            self.starts_at = timezone.make_aware(datetime(2025, 10, 1, 0, 0, 0))
        if self.ends_at is None:
            self.ends_at = timezone.make_aware(datetime(2025, 10, 31, 23, 59, 59))

    def is_enabled(self) -> bool:
        return not self._opted_out

    def get_context(self, request) -> Dict[str, object]:
        return {
            "halloween_discount_badge": "-3% до 31.10",
            "spiderweb_image_url": get_media_url("halloween_2025/images/spiderweb.svg"),
        }

    def get_static_bundles(self) -> Dict[str, Iterable[str]]:
        return {
            "css": ["seasonal/halloween_2025/css/pack.css"],
            "js": [
                "seasonal/controls.js",
                "seasonal/halloween_2025/js/pack.js",
            ],
        }

    def get_partial_template(self, region: str) -> Optional[str]:
        region_map = {
            "header": "seasonal/halloween_2025/partials/header_badge.html",
            "footer": "seasonal/halloween_2025/partials/footer_ribbon.html",
            "sidebar": "seasonal/halloween_2025/partials/sidebar_card.html",
        }
        key = region.replace(" ", "_").lower()
        return region_map.get(key)

    def on_request(self, request) -> None:
        cookie_value = getattr(request, "COOKIES", {}).get("seasonal_opt_out") if request else None
        self._opted_out = cookie_value == "1"


pack = Halloween2025Pack()

