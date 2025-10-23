from datetime import timedelta
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from django.utils import timezone

from seasonal.models import SeasonalCampaign
from seasonal.packs.base import Pack
from seasonal.utils import loader
from seasonal.utils.loader import PackImportError, load_pack


def _create_campaign(**kwargs) -> SeasonalCampaign:
    now = timezone.now()
    defaults = {
        "slug": "sample-campaign",
        "title": "Sample Campaign",
        "enabled": True,
        "starts_at": now - timedelta(days=1),
        "ends_at": now + timedelta(days=1),
        "pack_path": "seasonal.packs.sample",
        "percentage_rollout": 100,
    }
    defaults.update(kwargs)
    return SeasonalCampaign.objects.create(**defaults)


@pytest.mark.django_db
def test_load_pack_renders_template(rf):
    campaign = _create_campaign()
    pack = load_pack(campaign.pack_path).bind(campaign)

    request = rf.get("/")
    pack.ensure_request(request)
    rendered = pack.render("desktop", request=request)

    assert "Sample pack: Sample Campaign" in rendered


def test_load_pack_invalid_path():
    with pytest.raises(PackImportError):
        load_pack("")

    with pytest.raises(PackImportError):
        load_pack("......")


@pytest.mark.django_db
def test_halloween_pack_respects_opt_out_cookie(rf):
    campaign = _create_campaign(
        slug="halloween-2025",
        title="Halloween 2025",
        pack_path="seasonal.packs.halloween_2025.pack",
    )
    pack = load_pack(campaign.pack_path).bind(campaign)

    request = rf.get("/")
    request.COOKIES["seasonal_opt_out"] = "1"
    pack.ensure_request(request)

    assert not pack.is_enabled()
    assert not pack.is_active(timezone.now())


def test_load_pack_with_attribute(monkeypatch):
    @dataclass
    class AttrPack(Pack):
        slug: str = "attr-pack"
        name: str = "Attr Pack"
        version: str = "1.0"

        def get_context(self, request):
            return {}

        def get_static_bundles(self):
            return {"css": [], "js": []}

        def get_partial_template(self, region: str):
            return None

    module = SimpleNamespace(PackImpl=AttrPack)
    real_import = loader.import_module

    def fake_import(name):
        if name == "dummy.module":
            return module
        return real_import(name)

    monkeypatch.setattr(loader, "import_module", fake_import)

    pack = load_pack("dummy.module:PackImpl")
    assert isinstance(pack, AttrPack)
