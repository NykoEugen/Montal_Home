import logging
import sys
from typing import Iterable, Optional, Sequence, Tuple

from django.apps import apps
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, close_old_connections, models

from utils.image_variants import (
    GeneratedVariant,
    build_variant_name,
    generate_variants_for_storage_key,
)

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def iter_image_fields(
    app_label: Optional[str] = None,
    model_name: Optional[str] = None,
    field_name: Optional[str] = None,
) -> Iterable[Tuple[models.Model, models.ImageField]]:
    """
    Yield (model, field) tuples for ImageField instances across installed apps.
    """
    for model in apps.get_models():
        if app_label and model._meta.app_label != app_label:
            continue
        if model_name and model._meta.model_name != model_name.lower():
            continue
        for field in model._meta.get_fields():
            if not isinstance(field, models.ImageField):
                continue
            if field_name and field.name != field_name:
                continue
            yield model, field


def batched_queryset(queryset, *, chunk_size: int = 200):
    """
    Iterate over queryset in chunks ordered by primary key.
    """
    model = queryset.model
    pk_name = model._meta.pk.name
    ordered_qs = queryset.order_by(pk_name)
    last_pk = None

    while True:
        batch = ordered_qs
        if last_pk is not None:
            batch = batch.filter(**{f"{pk_name}__gt": last_pk})
        try:
            batch_list = list(batch[:chunk_size])
        except OperationalError:
            close_old_connections()
            continue
        if not batch_list:
            break
        for obj in batch_list:
            yield obj
            last_pk = getattr(obj, pk_name)
        # Ensure Django closes stale connections between batches.
        close_old_connections()


class Command(BaseCommand):
    help = (
        "Генерує responsive-варіанти (WebP) для усіх ImageField у проєкті. "
        "Створює копії файлів в R2/Bunny з суфіксами типу '_800w.webp' і т.д."
    )

    def add_arguments(self, parser):
        parser.add_argument("--app", dest="app_label", help="Обмежити конкретним app_label (наприклад, furniture)")
        parser.add_argument("--model", dest="model_name", help="Обмежити конкретною моделлю (наприклад, furnitureimage)")
        parser.add_argument("--field", dest="field_name", help="Обмежити конкретним полем (наприклад, image)")
        parser.add_argument("--limit", type=int, default=None, help="Ліміт записів на модель для обробки")
        parser.add_argument(
            "--widths",
            type=int,
            nargs="+",
            default=None,
            help="Кастомний список ширин для генерації (default: settings.IMAGE_VARIANT_WIDTHS)",
        )
        parser.add_argument(
            "--format",
            dest="fmt",
            default=None,
            help="Формат виводу (default: settings.IMAGE_VARIANT_FORMAT, зазвичай webp)",
        )
        parser.add_argument(
            "--quality",
            type=int,
            default=None,
            help="Якість кодування (default: settings.IMAGE_VARIANT_QUALITY)",
        )
        parser.add_argument("--force", action="store_true", help="Перегенерувати файли навіть якщо вони вже існують")
        parser.add_argument("--dry-run", action="store_true", help="Не записувати файли, лише показати що буде зроблено")
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=200,
            help="Скільки записів обробляти за раз (default: 200)",
        )
        parser.add_argument(
            "--assume-existing",
            action="store_true",
            help="Не перевіряти наявність файлів у стореджі (швидше, але завжди перезаписує варіанти)",
        )

    def handle(self, *args, **options):
        app_label = options.get("app_label")
        model_name = options.get("model_name")
        field_name = options.get("field_name")
        limit = options.get("limit")
        widths: Optional[Sequence[int]] = options.get("widths")
        fmt = options.get("fmt")
        quality = options.get("quality")
        force = options.get("force", False)
        dry_run = options.get("dry_run", False)
        chunk_size = max(1, options.get("chunk_size") or 200)
        assume_exists = options.get("assume_existing", False)

        storage = default_storage
        if not storage:
            raise CommandError("Не вдалося отримати default_storage.")

        total_models = total_processed = total_generated = 0

        for model, field in iter_image_fields(app_label, model_name, field_name):
            total_models += 1
            queryset = model.objects.all()
            fname = field.name
            queryset = queryset.exclude(**{fname: ""}).exclude(**{f"{fname}__isnull": True})
            if limit:
                queryset = queryset[:limit]

            self.stdout.write(self.style.MIGRATE_HEADING(
                f"Модель {model._meta.label} • поле {fname} • обробляємо…"
            ))

            for obj in batched_queryset(queryset, chunk_size=chunk_size):
                image_field = getattr(obj, fname, None)
                if not image_field:
                    continue
                name = getattr(image_field, "name", "")
                if not name:
                    continue

                total_processed += 1

                try:
                    generated_variants = generate_variants_for_storage_key(
                        name,
                        storage=image_field.storage if hasattr(image_field, "storage") else storage,
                        widths=widths,
                        fmt=fmt,
                        quality=quality,
                        force=force,
                        dry_run=dry_run,
                        assume_exists=assume_exists,
                    )
                except FileNotFoundError:
                    self.stdout.write(self.style.WARNING(
                        f"[SKIP] {model._meta.label} id={obj.pk} {fname}='{name}' — файл не знайдено у стореджі"
                    ))
                    continue
                except Exception as exc:
                    log.exception("Помилка при генерації responsive для %s:%s", model._meta.label, obj.pk)
                    self.stdout.write(self.style.WARNING(
                        f"[ERROR] {model._meta.label} id={obj.pk} {fname}='{name}': {exc}"
                    ))
                    continue

                if not generated_variants and not force:
                    self.stdout.write(self.style.NOTICE(
                        f"[SKIP] {model._meta.label} id={obj.pk} {fname}='{name}' — усі варіанти вже існують"
                    ))
                    continue

                total_generated += len(generated_variants)

                for variant in generated_variants:
                    suffix = f"{variant.width}w"
                    size_info = f"{variant.size_bytes / 1024:.1f}KB" if variant.size_bytes else "dry-run"
                    self.stdout.write(self.style.SUCCESS(
                        f"[OK] {model._meta.label} id={obj.pk} {fname}: {build_variant_name(name, variant.width, fmt)} ({suffix}, {size_info})"
                    ))

        self.stdout.write(self.style.HTTP_INFO(
            f"Готово: моделей={total_models}, записів={total_processed}, створено варіантів={total_generated}, dry_run={dry_run}"
        ))
