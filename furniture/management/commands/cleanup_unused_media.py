from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from django.apps import apps
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import models


class Command(BaseCommand):
    help = (
        "Сканує медіа-сховище та видаляє файли, які більше не згадуються в жодному FileField/ImageField."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--prefix",
            default="",
            help="Обмежити перевірку префіксом у сховищі (наприклад, 'furniture/').",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Фактично видалити невикористовувані файли (за замовчуванням лише звіт).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Видалити лише перші N знайдених невикористовуваних файлів.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Скільки ключів видаляти за один запит у S3/R2.",
        )

    def handle(self, *args, **options):
        prefix = options["prefix"].lstrip("/")
        delete_files = options["delete"]
        limit = options["limit"]
        batch_size = options["batch_size"]

        storage_type = self._detect_storage_type()
        self.stdout.write(self.style.NOTICE(f"Використовується storage: {storage_type}"))

        referenced = self._collect_referenced_paths()
        referenced_bases = {self._canonical_key(path) for path in referenced}
        self.stdout.write(f"Знайдено {len(referenced)} унікальних файлів у базі даних (без урахування розширення).")

        storage_files = self._list_storage_files(prefix)
        self.stdout.write(
            f"Отримано {len(storage_files)} файлів зі сховища{f' (префікс {prefix})' if prefix else ''}."
        )

        unused = sorted(
            key
            for key in storage_files
            if self._canonical_key(key) not in referenced_bases
        )
        if limit is not None:
            unused = unused[:limit]

        if not unused:
            self.stdout.write(self.style.SUCCESS("Невикористовуваних файлів не знайдено."))
            return

        self.stdout.write(
            self.style.WARNING(
                f"Виявлено {len(unused)} файлів без посилань у базі. "
                f"{'Видаляємо...' if delete_files else 'Список буде наведений нижче.'}"
            )
        )

        for key in unused[:10]:
            self.stdout.write(f" - {key}")
        if len(unused) > 10:
            self.stdout.write(f"... (ще {len(unused) - 10} файлів)")

        if not delete_files:
            self.stdout.write(self.style.WARNING("Запустіть із --delete, щоб видалити перераховані файли."))
            return

        deleted = self._delete_files(unused, storage_type, batch_size)
        self.stdout.write(self.style.SUCCESS(f"Видалено {deleted} файлів."))

    def _detect_storage_type(self) -> str:
        storage = default_storage
        if hasattr(storage, "bucket"):
            return "s3"
        if getattr(settings, "MEDIA_ROOT", None):
            return "filesystem"
        return "unknown"

    def _normalize_path(self, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip()
        if not value:
            return None
        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            value = parsed.path
        value = value.lstrip("/")
        return value or None

    def _canonical_key(self, path: str | None) -> str:
        """
        Зрізає розширення та варіантні суфікси типу '_400w', '_800w', '_1200w'.
        """
        if not path:
            return ""

        clean = path.rstrip("/")
        if not clean:
            return ""

        stem, _ = os.path.splitext(clean)
        parts = stem.split("/")
        filename = parts[-1]
        prefix = "/".join(parts[:-1])

        variant_suffixes = ("_400w", "_800w", "_1200w", "_default")
        for suffix in variant_suffixes:
            if filename.endswith(suffix):
                filename = filename[: -len(suffix)]
                break

        canonical = "/".join(filter(None, [prefix, filename])) if filename else prefix
        return canonical or stem

    def _collect_referenced_paths(self) -> set[str]:
        referenced: set[str] = set()
        for model in apps.get_models():
            file_fields = [
                field for field in model._meta.get_fields() if isinstance(field, models.FileField)
            ]
            if not file_fields:
                continue
            qs = model.objects.all()
            for field in file_fields:
                values = (
                    qs.exclude(**{f"{field.name}__isnull": True})
                    .exclude(**{field.name: ""})
                    .values_list(field.name, flat=True)
                )
                for path in values.iterator(chunk_size=1000):
                    normalized = self._normalize_path(path)
                    if normalized:
                        referenced.add(normalized)
        return referenced

    def _list_storage_files(self, prefix: str) -> set[str]:
        storage = default_storage
        normalized_prefix = prefix.rstrip("/")

        if hasattr(storage, "bucket"):
            bucket = storage.bucket
            objects = bucket.objects.filter(Prefix=normalized_prefix) if normalized_prefix else bucket.objects.all()
            files = {obj.key.lstrip("/") for obj in objects}
            return files

        media_root = getattr(settings, "MEDIA_ROOT", None)
        if not media_root:
            raise RuntimeError("MEDIA_ROOT не заданий та storage не підтримує перелік файлів.")

        media_root_path = Path(media_root)
        files: set[str] = set()
        target_root = media_root_path / normalized_prefix if normalized_prefix else media_root_path
        if not target_root.exists():
            return files

        for root, _, filenames in os.walk(target_root):
            for filename in filenames:
                full = Path(root) / filename
                rel = full.relative_to(media_root_path)
                files.add(str(rel).replace("\\", "/"))
        return files

    def _delete_files(self, keys: list[str], storage_type: str, batch_size: int) -> int:
        storage = default_storage
        if storage_type == "s3" and hasattr(storage, "bucket"):
            bucket = storage.bucket
            deleted = 0
            for i in range(0, len(keys), batch_size):
                chunk = keys[i : i + batch_size]
                if not chunk:
                    continue
                bucket.delete_objects(Delete={"Objects": [{"Key": key} for key in chunk]})
                deleted += len(chunk)
            return deleted

        media_root = getattr(settings, "MEDIA_ROOT", None)
        if not media_root:
            raise RuntimeError("MEDIA_ROOT не заданий, не вдалося видалити локальні файли.")

        deleted = 0
        for key in keys:
            path = Path(media_root) / key
            if path.exists():
                path.unlink()
                deleted += 1
        return deleted
