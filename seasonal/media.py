from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.templatetags.static import static


def get_media_url(asset_path: str, *, secure: bool = True) -> str:
    """Return a URL for a seasonal asset.

    If Cloudinary storage is configured and the library is available, this will
    build a Cloudinary URL for the provided ``asset_path`` (which should omit
    the leading ``seasonal/`` prefix). Otherwise the function falls back to the
    standard ``static`` helper so assets can be served locally during
    development.
    """

    normalized = (asset_path or "").strip().lstrip("/")
    if not normalized:
        raise ValueError("asset_path must be a non-empty string")

    cloudinary_url = _resolve_cloudinary_url(normalized, secure=secure)
    if cloudinary_url:
        return cloudinary_url

    static_path = normalized
    if not static_path.startswith("seasonal/"):
        static_path = f"seasonal/{static_path}"
    return static(static_path)


def _resolve_cloudinary_url(asset_path: str, *, secure: bool) -> Optional[str]:
    storage_config = getattr(settings, "CLOUDINARY_STORAGE", None)
    if not storage_config:
        return None

    try:
        from cloudinary.utils import cloudinary_url
    except ImportError:  # pragma: no cover - optional dependency
        return None

    url, _ = cloudinary_url(asset_path, secure=secure)
    return url

