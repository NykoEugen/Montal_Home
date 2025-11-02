import os
from uuid import uuid4

from django.utils import timezone
from django.utils.text import slugify


def _extract_extension(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext:
        return ext
    return ".jpg"


def _build_base_slug(slug_parts) -> str:
    parts = [slugify(part) for part in slug_parts if part]
    return "-".join(parts) or "image"


def _build_filename(slug_parts, filename: str) -> str:
    base_slug = _build_base_slug(slug_parts)
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    random_suffix = uuid4().hex[:6]
    ext = _extract_extension(filename)
    return f"{base_slug}-{timestamp}-{random_suffix}{ext}"


def furniture_main_image_upload_to(instance, filename: str) -> str:
    slug = getattr(instance, "slug", None) or getattr(instance, "name", None)
    folder = _build_base_slug([slug])
    return f"furniture/{folder}/{_build_filename([slug], filename)}"


def furniture_gallery_image_upload_to(instance, filename: str) -> str:
    furniture = getattr(instance, "furniture", None)
    slug = getattr(furniture, "slug", None) or getattr(furniture, "name", None)
    folder = _build_base_slug([slug])
    return f"furniture/{folder}/gallery/{_build_filename([slug, 'gallery'], filename)}"


def furniture_variant_image_upload_to(instance, filename: str) -> str:
    furniture = getattr(instance, "furniture", None)
    furniture_slug = getattr(furniture, "slug", None) or getattr(furniture, "name", None)
    variant_slug = getattr(instance, "name", None)
    folder = _build_base_slug([furniture_slug])
    return f"furniture/{folder}/variants/{_build_filename([furniture_slug, variant_slug], filename)}"
