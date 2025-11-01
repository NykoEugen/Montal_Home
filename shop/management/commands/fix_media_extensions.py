# shop/management/commands/fix_media_extensions.py

import sys
import logging
from pathlib import Path
from typing import Iterable, List, Optional

import boto3
from botocore.exceptions import ClientError

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, models

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

DEFAULT_EXTS = ["jpg", "jpeg", "png", "webp", "gif", "svg", "pdf", "mp4", "webm"]


def get_s3_client():
    endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", None)
    key = getattr(settings, "AWS_ACCESS_KEY_ID", None)
    secret = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
    if not all([endpoint, key, secret]):
        raise CommandError("AWS_S3_ENDPOINT_URL / AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY відсутні в settings.py/.env")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=key,
        aws_secret_access_key=secret,
    )


def key_exists(s3, bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        code = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code == 404:
            return False
        raise


def find_existing_with_ext(s3, bucket: str, base_key: str, exts: Iterable[str]) -> Optional[str]:
    """Пробуємо base_key + .ext у заданому порядку. Повертає повний ключ (base_key.ext), якщо знайдено в R2."""
    for ext in exts:
        key_with_ext = f"{base_key}.{ext}"
        if key_exists(s3, bucket, key_with_ext):
            return key_with_ext
    return None


def iter_target_fields(app_label: Optional[str], model_name: Optional[str], field_name: Optional[str]):
    """Генерує (model, field) для всіх FileField/ImageField згідно фільтрів."""
    for model in apps.get_models():
        if app_label and model._meta.app_label != app_label:
            continue
        if model_name and model._meta.model_name != model_name.lower():
            continue
        for f in model._meta.get_fields():
            if isinstance(f, (models.FileField,)):
                if field_name and f.name != field_name:
                    continue
                yield model, f


def has_real_ext(name: str, allowed_exts: Iterable[str]) -> bool:
    """
    Повертає True, якщо фінальний суфікс дорівнює одному з дозволених розширень.
    Приклади:
      - "a/b/3.png"        -> True
      - "3.jpg_xf0vit"     -> False  (фальшивий суфікс)
      - "photo.webpV2"     -> False
      - "clip.mp4"         -> True
    """
    suffix = Path(name).suffix.lstrip(".").lower()
    return bool(suffix) and suffix in set(e.lower() for e in allowed_exts)


class Command(BaseCommand):
    help = (
        "Звіряє імена файлів у БД з об'єктами в R2 та додає розширення там, де воно відсутнє. "
        "Оновлює лише ім'я файлу в полі (інші поля запису не змінює). "
        "Також обробляє кейси на кшталт '3.jpg_xxxxx' → шукає '3.jpg_xxxxx.<ext>'."
    )

    def add_arguments(self, parser):
        parser.add_argument("--app", dest="app_label", help="Обмежити конкретним app_label (наприклад, furniture)")
        parser.add_argument("--model", dest="model_name", help="Обмежити конкретною моделлю (наприклад, productimage)")
        parser.add_argument("--field", dest="field_name", help="Обмежити конкретним полем (наприклад, image)")
        parser.add_argument("--limit", type=int, default=None, help="Ліміт записів для обробки")
        parser.add_argument(
            "--extensions",
            nargs="+",
            default=DEFAULT_EXTS,
            help=f"Порядок розширень для перевірки (дефолт: {', '.join(DEFAULT_EXTS)})",
        )
        parser.add_argument("--dry-run", action="store_true", help="Лише показати зміни, БД не оновлювати")
        parser.add_argument(
            "--bucket",
            dest="bucket",
            default=getattr(settings, "AWS_STORAGE_BUCKET_NAME", None),
            help="Назва R2 bucket (за замовчуванням з settings.AWS_STORAGE_BUCKET_NAME)",
        )

    def handle(self, *args, **opts):
        app_label = opts.get("app_label")
        model_name = opts.get("model_name")
        field_name = opts.get("field_name")
        limit = opts.get("limit")
        dry = opts.get("dry_run")
        exts: List[str] = [e.lstrip(".").lower() for e in (opts.get("extensions") or DEFAULT_EXTS)]
        bucket = opts.get("bucket")

        if not bucket:
            raise CommandError("Не вказано bucket. Передай --bucket або налаштуй AWS_STORAGE_BUCKET_NAME у settings.py")

        s3 = get_s3_client()

        total_checked = total_fixed = total_skipped = 0

        for model, f in iter_target_fields(app_label, model_name, field_name):
            q = model.objects.all()
            fname = f.name
            q = q.exclude(**{f"{fname}": ""}).exclude(**{f"{fname}__isnull": True})

            if limit:
                q = q[:limit]

            self.stdout.write(self.style.MIGRATE_HEADING(
                f"Модель {model._meta.label} • поле {fname} • перевіряємо…"
            ))

            for obj in q.iterator():
                file_field = getattr(obj, fname)
                if not file_field:
                    continue
                rel_path = file_field.name  # відносний шлях у стореджі (ключ у R2)
                if not rel_path:
                    continue

                total_checked += 1

                # якщо ФАКТИЧНЕ розширення вже є (напр., .jpg / .png / …) — пропускаємо
                if has_real_ext(rel_path, exts):
                    total_skipped += 1
                    continue

                # тут або взагалі немає крапки, або суфікс «фальшивий» (типу ".jpg_hash")
                base_key = rel_path

                found_key = find_existing_with_ext(s3, bucket, base_key, exts)

                if not found_key:
                    self.stdout.write(self.style.WARNING(
                        f"[NO MATCH] {model._meta.label} id={obj.pk} {fname}='{rel_path}' — не знайшли *.{{{','.join(exts)}}} у R2"
                    ))
                    total_skipped += 1
                    continue

                new_rel = found_key

                # захист від переповнення стовпця (varchar(N))
                max_len = getattr(f, "max_length", None)
                if max_len and len(new_rel) > max_len:
                    self.stdout.write(self.style.WARNING(
                        f"[SKIP-LONG] {model._meta.label} id={obj.pk} {fname}: '{new_rel}' довжина={len(new_rel)} > max_length={max_len}"
                    ))
                    total_skipped += 1
                    continue

                self.stdout.write(self.style.SUCCESS(
                    f"[FIX] {model._meta.label} id={obj.pk} {fname}: '{rel_path}' → '{new_rel}'"
                ))
                if not dry:
                    with transaction.atomic():
                        file_field.name = new_rel  # не тригеримо перезапис у сторедж
                        obj.save(update_fields=[fname])

                total_fixed += 1

        self.stdout.write(self.style.HTTP_INFO(
            f"ГОТОВО: перевірено={total_checked} • виправлено={total_fixed} • пропущено={total_skipped} • dry_run={dry}"
        ))
