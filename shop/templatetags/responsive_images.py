from __future__ import annotations

from typing import Iterable, Optional, Sequence

from django import template
from django.conf import settings
from django.core.files.storage import Storage, default_storage

from utils.image_variants import build_media_url, build_variant_name

register = template.Library()


def _get_storage(image_field) -> Storage:
    storage = getattr(image_field, "storage", None)
    return storage or default_storage


def _get_name(image_field) -> str:
    return getattr(image_field, "name", "") or ""


def _should_check_exists() -> bool:
    return not getattr(settings, "IMAGE_VARIANT_ASSUME_EXISTS", True)


def _variant_widths(widths: Optional[Sequence[int]]) -> Iterable[int]:
    if widths:
        return [int(w) for w in widths]
    return getattr(settings, "IMAGE_VARIANT_WIDTHS", [400, 800, 1200])


@register.filter
def image_variant(image_field, width: Optional[int] = None) -> str:
    """
    Повертає URL responsive-варіанту для заданої ширини.
    """
    if not image_field:
        return ""
    name = _get_name(image_field)
    if not name:
        return ""

    width = int(width or getattr(settings, "IMAGE_VARIANT_DEFAULT_WIDTH", 800))
    fmt = getattr(settings, "IMAGE_VARIANT_FORMAT", "webp")
    variant_name = build_variant_name(name, width, fmt)

    if _should_check_exists():
        storage = _get_storage(image_field)
        if not storage.exists(variant_name):
            # Fallback на оригінальне зображення
            return getattr(image_field, "url", build_media_url(name))

    return build_media_url(variant_name)


@register.simple_tag
def responsive_srcset(image_field, widths: Optional[Sequence[int]] = None) -> str:
    """
    Будує srcset значення у форматі "url 400w, url 800w, ...".
    """
    if not image_field:
        return ""
    name = _get_name(image_field)
    if not name:
        return ""

    parts = []
    for width in _variant_widths(widths):
        url = image_variant(image_field, width)
        if url:
            parts.append(f"{url} {int(width)}w")
    return ", ".join(parts)


@register.simple_tag
def responsive_sizes(default: Optional[str] = None) -> str:
    """
    Повертає значення для атрибуту sizes (можна перевизначити у шаблоні).
    """
    return default or getattr(
        settings,
        "IMAGE_VARIANT_SIZES_ATTR",
        "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 1200px",
    )
