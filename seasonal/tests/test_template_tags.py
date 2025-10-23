from datetime import timedelta

import pytest
from django.template import Context, Template
from django.utils import timezone

from seasonal.models import SeasonalCampaign
from seasonal.utils.loader import load_pack


def _campaign(**kwargs):
    now = timezone.now()
    data = {
        "slug": "sample-campaign",
        "title": "Sample Campaign",
        "enabled": True,
        "starts_at": now - timedelta(days=1),
        "ends_at": now + timedelta(days=1),
        "pack_path": "seasonal.packs.sample",
        "percentage_rollout": 100,
    }
    data.update(kwargs)
    return SeasonalCampaign.objects.create(**data)


@pytest.mark.django_db
def test_render_seasonal_renders_active_pack(rf):
    campaign = _campaign()
    pack = load_pack(campaign.pack_path).bind(campaign)

    template = Template("{% load seasonal_tags %}{% render_seasonal 'desktop' %}")
    request = rf.get("/")
    pack.ensure_request(request)
    context = Context({"seasonal_packs": [pack], "request": request})

    rendered = template.render(context)
    assert "Sample pack: Sample Campaign" in rendered


@pytest.mark.django_db
def test_render_seasonal_skips_missing_region(rf):
    campaign = _campaign()
    pack = load_pack(campaign.pack_path).bind(campaign)

    template = Template("{% load seasonal_tags %}{% render_seasonal 'mobile' %}")
    request = rf.get("/")
    pack.ensure_request(request)
    context = Context({"seasonal_packs": [pack], "request": request})

    rendered = template.render(context)
    assert rendered.strip() == ""
