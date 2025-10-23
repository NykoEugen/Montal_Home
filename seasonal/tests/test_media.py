from __future__ import annotations

import sys
import types

import pytest

from seasonal.media import get_media_url


def test_get_media_url_static(settings):
    if hasattr(settings, "CLOUDINARY_STORAGE"):
        settings.CLOUDINARY_STORAGE = None

    url = get_media_url("halloween_2025/images/spiderweb.svg")
    assert url.endswith("seasonal/halloween_2025/images/spiderweb.svg")


def test_get_media_url_cloudinary(monkeypatch, settings):
    settings.CLOUDINARY_STORAGE = {"CLOUD_NAME": "demo"}

    utils_module = types.ModuleType("cloudinary.utils")

    def fake_cloudinary_url(public_id, **options):
        return (f"https://cdn.example.com/{public_id}", options)

    utils_module.cloudinary_url = fake_cloudinary_url
    cloudinary_module = types.ModuleType("cloudinary")

    monkeypatch.setitem(sys.modules, "cloudinary", cloudinary_module)
    monkeypatch.setitem(sys.modules, "cloudinary.utils", utils_module)

    url = get_media_url("halloween_2025/images/spiderweb.svg")
    assert url == "https://cdn.example.com/halloween_2025/images/spiderweb.svg"
