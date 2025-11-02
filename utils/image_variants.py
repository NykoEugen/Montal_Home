from __future__ import annotations

import logging
import threading

from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from typing import Iterable, List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, default_storage
from django.db import transaction

from PIL import Image, ImageOps

# Image.ANTIALIAS is deprecated in Pillow>=10, use Image.Resampling.LANCZOS instead
RESAMPLE = Image.Resampling.LANCZOS
log = logging.getLogger(__name__)


def _get_variant_format(fmt: Optional[str] = None) -> str:
    return (fmt or getattr(settings, "IMAGE_VARIANT_FORMAT", "webp")).lower()


def _get_variant_widths(widths: Optional[Sequence[int]] = None) -> List[int]:
    if widths:
        return [int(w) for w in widths]
    return list(getattr(settings, "IMAGE_VARIANT_WIDTHS", [400, 800, 1200]))


def _strip_leading_slash(value: str) -> str:
    return value[1:] if value.startswith("/") else value


def build_variant_name(name: str, width: int, fmt: Optional[str] = None) -> str:
    """
    Returns a storage key for the responsive variant, e.g.
    pictures/photo.jpg -> pictures/photo_800w.webp
    """
    if not name:
        return ""
    fmt = _get_variant_format(fmt)
    path = PurePosixPath(name)
    base = str(path.with_suffix(""))
    return f"{base}_{int(width)}w.{fmt}"


def build_media_url(name: str) -> str:
    """
    Builds an absolute media URL that respects MEDIA_URL (including CDN domains).
    """
    media_url = getattr(settings, "MEDIA_URL", "")
    if not media_url:
        return name
    return f"{media_url.rstrip('/')}/{_strip_leading_slash(name)}"


def build_variant_urls(name: str, widths: Optional[Sequence[int]] = None, fmt: Optional[str] = None) -> List[Tuple[int, str]]:
    """
    Returns a list of (width, url) tuples for srcset construction.
    """
    fmt = _get_variant_format(fmt)
    urls = []
    for width in _get_variant_widths(widths):
        variant_name = build_variant_name(name, width, fmt)
        urls.append((width, build_media_url(variant_name)))
    return urls


@dataclass(frozen=True)
class GeneratedVariant:
    width: int
    name: str
    size_bytes: int


def _prepare_image(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation and ensure compatible mode."""
    img = ImageOps.exif_transpose(img)
    if img.mode in ("P", "CMYK"):
        img = img.convert("RGBA" if "transparency" in img.info else "RGB")
    elif img.mode not in ("L", "LA", "RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.mode else "RGB")
    return img


def _resize_image(source: Image.Image, width: int) -> Image.Image:
    """Create a resized copy with the desired width preserving aspect ratio."""
    width = int(width)
    if width <= 0:
        raise ValueError("Variant width must be positive")
    if source.width <= width:
        return source.copy()
    ratio = width / float(source.width)
    height = max(1, int(round(source.height * ratio)))
    return source.resize((width, height), RESAMPLE)


def _save_webp(image: Image.Image, quality: int, lossless: bool = False) -> BytesIO:
    buffer = BytesIO()
    save_kwargs = {
        "format": "WEBP",
        "quality": quality,
        "method": 6,
    }
    if lossless:
        save_kwargs.update({"lossless": True, "quality": 100})
    image.save(buffer, **save_kwargs)
    buffer.seek(0)
    return buffer


def generate_variants_for_storage_key(
    name: str,
    *,
    storage: Optional[Storage] = None,
    widths: Optional[Sequence[int]] = None,
    fmt: Optional[str] = None,
    quality: Optional[int] = None,
    force: bool = False,
    assume_exists: Optional[bool] = None,
    dry_run: bool = False,
) -> List[GeneratedVariant]:
    """
    Generates responsive variants for a given storage key and uploads them to storage.

    Args:
        name: Original storage key.
        storage: Optional custom storage (defaults to default_storage).
        widths: Variant widths to generate (defaults to settings.IMAGE_VARIANT_WIDTHS).
        fmt: Target image format (defaults to settings.IMAGE_VARIANT_FORMAT).
        quality: Quality for the encoder (defaults to settings.IMAGE_VARIANT_QUALITY).
        force: Recreate variants even if they exist.
        assume_exists: If True, skip storage existence checks (defaults to settings.IMAGE_VARIANT_ASSUME_EXISTS).
        dry_run: When True, does not upload files and returns the planned variants.
    """
    if not name:
        return []

    storage = storage or default_storage
    fmt = _get_variant_format(fmt)
    quality = quality or getattr(settings, "IMAGE_VARIANT_QUALITY", 82)
    widths = _get_variant_widths(widths)
    assume_exists = (
        getattr(settings, "IMAGE_VARIANT_ASSUME_EXISTS", True)
        if assume_exists is None
        else assume_exists
    )

    generated: List[GeneratedVariant] = []

    if force:
        existing_variants = {width: False for width in widths}
    elif assume_exists:
        existing_variants = {width: False for width in widths}
    else:
        existing_variants = {
            width: storage.exists(build_variant_name(name, width, fmt)) for width in widths
        }

    with storage.open(name, "rb") as original_file:
        with Image.open(original_file) as img:
            prepared = _prepare_image(img)

            for width in widths:
                variant_name = build_variant_name(name, width, fmt)
                if existing_variants.get(width) and not force:
                    continue

                resized = _resize_image(prepared, width)
                # Preserve alpha transparency when present.
                if resized.mode not in ("RGB", "RGBA"):
                    resized = resized.convert("RGBA" if "A" in resized.getbands() else "RGB")

                buffer = BytesIO()
                if fmt == "webp":
                    buffer = _save_webp(resized, quality=quality, lossless=False)
                else:
                    resized.save(buffer, format=fmt.upper(), quality=quality, optimize=True)
                    buffer.seek(0)

                data = buffer.getvalue()
                if not dry_run:
                    content = ContentFile(data, name=variant_name)
                    storage.save(variant_name, content)
                generated.append(
                    GeneratedVariant(
                        width=width,
                        name=variant_name,
                        size_bytes=len(data),
                    )
                )

    return generated


def schedule_variant_generation_for_field(
    image_field,
    *,
    widths: Optional[Sequence[int]] = None,
    fmt: Optional[str] = None,
    quality: Optional[int] = None,
    force: bool = False,
    assume_exists: Optional[bool] = None,
) -> None:
    """
    Відкладає генерацію responsive-варіантів у фоновому потоці після успішного коміту.
    """
    if not image_field:
        return

    name = getattr(image_field, "name", "")
    if not name:
        return

    storage = getattr(image_field, "storage", None) or default_storage

    def _worker():
        try:
            generate_variants_for_storage_key(
                name,
                storage=storage,
                widths=widths,
                fmt=fmt,
                quality=quality,
                force=force,
                assume_exists=assume_exists,
            )
        except FileNotFoundError:
            log.warning("Responsive variants skipped: '%s' not found in storage", name)
        except Exception as exc:
            log.exception("Failed to generate responsive variants for '%s': %s", name, exc)

    def _schedule():
        thread = threading.Thread(
            target=_worker,
            daemon=True,
            name=f"img-variants-{PurePosixPath(name).name}",
        )
        thread.start()

    transaction.on_commit(_schedule)
