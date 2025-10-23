from __future__ import annotations

import io
import shutil
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command

from seasonal.models import SeasonalCampaign


@pytest.mark.django_db
def test_seasonal_create_scaffolds_assets_and_campaign():
    slug = "autumn_pack"
    base_dir = Path(settings.BASE_DIR)
    pack_dir = base_dir / "seasonal" / "packs" / slug
    static_dir = base_dir / "static" / "seasonal" / slug
    template_partial_dir = base_dir / "templates" / "seasonal" / slug / "partials"

    # Ensure a clean slate for the slug in case of prior runs
    for path in (pack_dir, static_dir, template_partial_dir.parent):
        if path.exists():
            shutil.rmtree(path)

    out = io.StringIO()
    call_command(
        "seasonal",
        "create",
        slug,
        "--title",
        "Autumn Pack",
        "--start",
        "2025-09-01",
        "--end",
        "2025-10-01",
        "--priority",
        "5",
        stdout=out,
        stderr=out,
    )

    output = out.getvalue()
    assert "Seasonal pack 'autumn_pack' created." in output

    pack_py = pack_dir / "pack.py"
    assert pack_py.exists()
    assert (pack_dir / "__init__.py").exists()
    css_file = static_dir / "css" / "pack.css"
    js_file = static_dir / "js" / "pack.js"
    assert css_file.exists()
    assert js_file.exists()
    for snippet in ("header.html", "sidebar.html", "footer.html"):
        assert (template_partial_dir / snippet).exists()

    pack_content = pack_py.read_text(encoding="utf-8")
    assert "class PackImpl" in pack_content
    assert f"seasonal/{slug}/css/pack.css" in pack_content

    campaign = SeasonalCampaign.objects.get(slug=slug)
    assert campaign.title == "Autumn Pack"
    assert campaign.priority == 5
    assert campaign.pack_path == f"seasonal.packs.{slug}.pack:PackImpl"

    # Clean up generated artifacts to keep the repository tidy
    for path in (pack_dir, static_dir, template_partial_dir.parent):
        if path.exists():
            shutil.rmtree(path)

