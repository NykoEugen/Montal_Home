from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Type

from django.db.models import Model
from django.forms import ModelForm


@dataclass(frozen=True)
class AdminSection:
    """Configuration describing how a model is managed in the custom admin."""

    slug: str
    model: Type[Model]
    form_class: Type[ModelForm] | None
    list_display: Sequence[str]
    search_fields: Sequence[str] = ()
    ordering: Sequence[str] = ()
    title: str | None = None
    description: str | None = None
    icon: str | None = None  # Font Awesome utility icon name
    list_display_labels: Sequence[str] | None = None
    allow_create: bool = True
    allow_edit: bool = True
    allow_delete: bool = True
    read_only: bool = False

    def get_title(self) -> str:
        if self.title:
            return self.title
        return self.model._meta.verbose_name_plural.title()


class SectionRegistry:
    """A small registry that holds all admin sections."""

    def __init__(self) -> None:
        self._sections: dict[str, AdminSection] = {}

    def register(self, section: AdminSection) -> None:
        self._sections[section.slug] = section

    def unregister(self, slug: str) -> None:
        self._sections.pop(slug, None)

    def get(self, slug: str) -> AdminSection:
        return self._sections[slug]

    def all(self) -> Iterable[AdminSection]:
        return self._sections.values()


registry = SectionRegistry()
