from __future__ import annotations

import pytest

from seasonal.matchers import match_country, match_device, match_path


class DummyRequest:
    def __init__(self, path="/", meta=None):
        self.path = path
        self.META = meta or {}


@pytest.mark.parametrize(
    "path,pattern,expected",
    [
        ("/promo/halloween/", "/promo/*", True),
        ("/decor/autumn", "/promo/*", False),
        ("/halloween", "*halloween", True),
    ],
)
def test_match_path(path, pattern, expected):
    request = DummyRequest(path=path)
    assert match_path(request, pattern) is expected


def test_match_country_uses_meta_with_fallback():
    request = DummyRequest(meta={"HTTP_CF_IPCOUNTRY": "UA"})
    assert match_country(request, "ua")

    other = DummyRequest(meta={})
    assert not match_country(other, "UA")


def test_match_device_uses_meta_keys():
    request = DummyRequest(meta={"HTTP_X_DEVICE": "mobile"})
    assert match_device(request, "MOBILE")

    other = DummyRequest(meta={})
    assert not match_device(other, "desktop")

