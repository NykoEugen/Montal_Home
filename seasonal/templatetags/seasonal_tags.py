from __future__ import annotations

import logging
from typing import Iterable

from django import template
from django.template import Context
from django.utils.safestring import mark_safe

from seasonal.packs.base import Pack

logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag(takes_context=True)
def render_seasonal(context: Context, region: str) -> str:
    """Render all active seasonal packs for the provided region."""
    packs: Iterable[Pack] = context.get("seasonal_packs", []) or []
    request = context.get("request")

    if hasattr(context, "flatten"):
        extra_context = context.flatten()
    else:  # pragma: no cover - Django < 1.11
        extra_context = dict(context)

    output: list[str] = []
    for pack in packs:
        try:
            rendered = pack.render(region, request=request, extra_context=extra_context)
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to render seasonal pack %s", getattr(pack, "slug", "?"))
            continue

        if rendered:
            output.append(rendered)

    return mark_safe("".join(output))
