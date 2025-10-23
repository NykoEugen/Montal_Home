from __future__ import annotations

from fnmatch import fnmatch
from typing import Iterable


_COUNTRY_META_KEYS: Iterable[str] = (
    "HTTP_CF_IPCOUNTRY",
    "GEOIP_COUNTRY_CODE",
    "COUNTRY",
)

_DEVICE_META_KEYS: Iterable[str] = (
    "HTTP_X_DEVICE",
    "HTTP_USER_DEVICE",
    "DEVICE",
)


def match_path(request, pattern: str) -> bool:
    path = getattr(request, "path", "") or "/"
    return fnmatch(path, pattern)


def match_country(request, expected: str) -> bool:
    meta = getattr(request, "META", {}) or {}
    value = _extract_first(meta, _COUNTRY_META_KEYS, default="unknown")
    return value.lower() == expected.lower()


def match_device(request, expected: str) -> bool:
    meta = getattr(request, "META", {}) or {}
    value = _extract_first(meta, _DEVICE_META_KEYS, default="unknown")
    return value.lower() == expected.lower()


def _extract_first(meta, keys: Iterable[str], default: str) -> str:
    for key in keys:
        value = meta.get(key)
        if value:
            return str(value)
    return default

