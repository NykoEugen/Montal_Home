from __future__ import annotations

from typing import Any

from django import template

register = template.Library()


def _resolve_attr(obj: Any, attr_path: str) -> Any:
    value = obj
    for chunk in attr_path.split("__"):
        if value is None:
            return None
        value = getattr(value, chunk)
        if callable(value):
            value = value()
    return value


@register.filter
def attr(obj: Any, attr_path: str) -> Any:
    """Get attribute value from an object, supporting Django double-underscore traversal."""
    try:
        value = _resolve_attr(obj, attr_path)
        if hasattr(value, "all") and callable(value.all):
            return ", ".join(str(item) for item in value.all())
        if isinstance(value, bool):
            return "Так" if value else "Ні"
        if value in (None, ""):
            return "—"
        return value
    except AttributeError:
        return "—"


@register.filter
def widget_type(bound_field: Any) -> str:
    """Return widget class name for the provided bound field."""
    try:
        return bound_field.field.widget.__class__.__name__
    except AttributeError:
        return ""


@register.filter
def in_list(value: str, csv_values: str) -> bool:
    """Check if the provided value is within a comma-separated list."""
    items = [item.strip() for item in csv_values.split(",") if item.strip()]
    return str(value) in items
