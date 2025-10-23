from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from seasonal.packs.base import Pack


@dataclass
class SamplePack(Pack):
    slug: str = "sample-pack"
    name: str = "Sample Pack"
    version: str = "1.0.0"

    def get_context(self, request) -> Dict[str, object]:
        message = "Sample pack"
        if self.campaign:
            message = f"{message}: {self.campaign.title}"
        return {"sample_pack_message": message}

    def get_static_bundles(self) -> Dict[str, Iterable[str]]:
        return {"css": [], "js": []}

    def get_partial_template(self, region: str) -> Optional[str]:
        region_slug = region.replace(" ", "_").lower()
        template_name = f"seasonal/packs/sample/{region_slug}.html"
        return template_name


pack = SamplePack()

