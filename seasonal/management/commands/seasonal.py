from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent
from typing import Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from seasonal.models import SeasonalCampaign

SLUG_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class Command(BaseCommand):
    help = "Manage seasonal campaign packs."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="seasonal_command")

        create_parser = subparsers.add_parser(
            "create", help="Scaffold a new seasonal pack and campaign."
        )
        create_parser.add_argument("slug", type=str, help="Identifier for the pack module.")
        create_parser.add_argument(
            "--title",
            required=True,
            help="Human friendly campaign title.",
        )
        create_parser.add_argument(
            "--start",
            dest="starts_at",
            help="ISO date or datetime when campaign starts (e.g. 2025-10-01 or 2025-10-01T08:00).",
        )
        create_parser.add_argument(
            "--end",
            dest="ends_at",
            help="ISO date or datetime when campaign ends.",
        )
        create_parser.add_argument(
            "--priority",
            type=int,
            default=0,
            help="Display priority (higher shows first).",
        )

    def handle(self, *args, **options):
        command = options.pop("seasonal_command", None)
        if command == "create":
            return self._handle_create(**options)
        raise CommandError("Please provide a valid subcommand (e.g. `seasonal create`).")

    def _handle_create(
        self,
        *,
        slug: str,
        title: str,
        starts_at: Optional[str] = None,
        ends_at: Optional[str] = None,
        priority: int = 0,
        **_: object,
    ):
        if not SLUG_PATTERN.match(slug):
            raise CommandError(
                "Slug must be a valid Python identifier (letters, numbers, underscores, not starting with a digit)."
            )

        base_dir = Path(settings.BASE_DIR)
        pack_dir = base_dir / "seasonal" / "packs" / slug
        static_dir = base_dir / "static" / "seasonal" / slug
        template_dir = base_dir / "templates" / "seasonal" / slug / "partials"
        pack_module_path = pack_dir / "pack.py"
        pack_init_path = pack_dir / "__init__.py"

        if pack_module_path.exists():
            raise CommandError(f"Pack module already exists at {pack_module_path}.")

        if SeasonalCampaign.objects.filter(slug=slug).exists():
            raise CommandError(f"A SeasonalCampaign with slug '{slug}' already exists.")

        starts_at_dt = self._parse_dt(starts_at) if starts_at else None
        ends_at_dt = self._parse_dt(ends_at) if ends_at else None

        if starts_at_dt and ends_at_dt and ends_at_dt <= starts_at_dt:
            raise CommandError("End date must be after start date.")

        pack_dir.mkdir(parents=True, exist_ok=True)
        (static_dir / "css").mkdir(parents=True, exist_ok=True)
        (static_dir / "js").mkdir(parents=True, exist_ok=True)
        template_dir.mkdir(parents=True, exist_ok=True)

        pack_class_name = "PackImpl"
        pack_path = f"seasonal.packs.{slug}.pack:{pack_class_name}"

        self._write_file(
            pack_module_path,
            self._render_pack_py(slug=slug, title=title, priority=priority, class_name=pack_class_name),
        )
        self._write_file(
            pack_init_path,
            dedent(
                f"""\
                from .pack import {pack_class_name}, pack

                __all__ = ["{pack_class_name}", "pack"]
                """
            ),
        )

        css_path = static_dir / "css" / "pack.css"
        js_path = static_dir / "js" / "pack.js"
        header_tpl = template_dir / "header.html"
        sidebar_tpl = template_dir / "sidebar.html"
        footer_tpl = template_dir / "footer.html"

        self._write_file(
            css_path,
            dedent(
                f"""\
                /* Seasonal pack styles for '{title}' */
                .seasonal-pack--{slug} {{
                    /* TODO: theme your seasonal block */
                }}
                """
            ),
        )
        self._write_file(
            js_path,
            dedent(
                """\
                (function () {
                  // TODO: enhance your seasonal experience here.
                })();
                """
            ),
        )

        for tpl_path, region in (
            (header_tpl, "header"),
            (sidebar_tpl, "sidebar"),
            (footer_tpl, "footer"),
        ):
            self._write_file(
                tpl_path,
                dedent(
                    f"""\
                    <div class="seasonal-pack seasonal-pack--{slug}" data-seasonal-pack="{{{{ campaign.slug|default:'{slug}' }}}}">
                      <p>Stub {region} content for {title}. Update this template.</p>
                    </div>
                    """
                ),
            )

        with transaction.atomic():
            campaign = SeasonalCampaign.objects.create(
                slug=slug,
                title=title,
                enabled=False,
                starts_at=starts_at_dt or timezone.now(),
                ends_at=ends_at_dt or (timezone.now() + timedelta(days=30)),
                priority=priority,
                pack_path=pack_path,
                percentage_rollout=100,
            )

        self.stdout.write(self.style.SUCCESS(f"Seasonal pack '{slug}' created."))
        self.stdout.write(f"  Pack module: {pack_module_path.relative_to(base_dir)}")
        self.stdout.write(f"  Static CSS:  {css_path.relative_to(base_dir)}")
        self.stdout.write(f"  Static JS:   {js_path.relative_to(base_dir)}")
        self.stdout.write(f"  Templates:   {template_dir.relative_to(base_dir)}")
        self.stdout.write(f"  Campaign ID: {campaign.id}")

        self.stdout.write("")
        self.stdout.write("Next steps:")
        self.stdout.write("  1. Implement your pack context, bundles, and templates.")
        self.stdout.write("  2. Enable the campaign in Django admin when ready.")
        self.stdout.write("  3. Consider adding tests for the new pack.")

        self.stdout.write("")
        self.stdout.write("Sample stubs created:")
        self.stdout.write(f"  - CSS ({css_path.name}): .seasonal-pack--{slug} {{ ... }}")
        self.stdout.write(f"  - JS ({js_path.name}): IIFE placeholder.")
        self.stdout.write("  - Templates: header.html, sidebar.html, footer.html.")

    def _parse_dt(self, value: str) -> timezone.datetime:
        dt = parse_datetime(value)
        if dt is None:
            try:
                dt = datetime.fromisoformat(value)
            except ValueError as exc:  # pragma: no cover - invalid handled by caller
                raise CommandError(f"Could not parse datetime '{value}'.") from exc
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        return dt

    def _write_file(self, path: Path, content: str) -> None:
        if path.exists():
            raise CommandError(f"Refusing to overwrite existing file: {path}")
        path.write_text(content.strip() + "\n", encoding="utf-8")

    def _render_pack_py(self, *, slug: str, title: str, priority: int, class_name: str) -> str:
        return dedent(
            f"""\
            from __future__ import annotations

            from dataclasses import dataclass
            from typing import Dict, Iterable, Optional

            from seasonal.packs.base import Pack


            @dataclass
            class {class_name}(Pack):
                slug: str = "{slug}"
                name: str = "{title}"
                version: str = "0.1.0"
                priority: int = {priority}

                def get_context(self, request) -> Dict[str, object]:
                    return {{}}

                def get_static_bundles(self) -> Dict[str, Iterable[str]]:
                    return {{
                        "css": ["seasonal/{slug}/css/pack.css"],
                        "js": ["seasonal/{slug}/js/pack.js"],
                    }}

                def get_partial_template(self, region: str) -> Optional[str]:
                    region_key = region.replace(" ", "_").lower()
                    mapping = {{
                        "header": "seasonal/{slug}/partials/header.html",
                        "sidebar": "seasonal/{slug}/partials/sidebar.html",
                        "footer": "seasonal/{slug}/partials/footer.html",
                    }}
                    return mapping.get(region_key)


            pack = {class_name}()
            """
        )
