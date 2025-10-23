from dataclasses import dataclass
from datetime import timedelta

import pytest
from django.utils import timezone

from seasonal import context_processors
from seasonal.models import SeasonalCampaign
from seasonal.packs.base import Pack


@dataclass
class DummyPack(Pack):
    slug: str = "dummy"
    name: str = "Dummy Pack"
    version: str = "1.0.0"

    def get_context(self, request):
        return {}

    def get_static_bundles(self):
        return {
            "css": ["seasonal/dummy.css"],
            "js": ["seasonal/dummy.js"],
        }

    def get_partial_template(self, region: str):  # pragma: no cover - not needed for this test
        return None


@pytest.mark.django_db
def test_active_packs_collects_unique_assets(monkeypatch, rf):
    now = timezone.now()
    data = {
        "title": "Dummy Campaign",
        "enabled": True,
        "starts_at": now - timedelta(days=1),
        "ends_at": now + timedelta(days=1),
        "pack_path": "dummy.pack",
        "percentage_rollout": 100,
    }
    SeasonalCampaign.objects.create(slug="dummy-one", **data)
    SeasonalCampaign.objects.create(slug="dummy-two", **data)

    def fake_loader(pack_path):
        return DummyPack()

    monkeypatch.setattr(context_processors, "load_pack", fake_loader)

    request = rf.get("/")
    result = context_processors.active_packs(request)

    assert len(result["seasonal_packs"]) == 2
    assert result["seasonal_assets"]["css"] == ["seasonal/dummy.css"]
    assert result["seasonal_assets"]["js"] == ["seasonal/dummy.js"]
