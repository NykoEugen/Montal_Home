from __future__ import annotations

import threading
import traceback
from typing import Callable, Optional

from django.db import close_old_connections
from django.utils import timezone

from .models import CatalogUpdateJob


def _run_job(job_id: int, callable_fn: Callable[[], dict]) -> None:
    close_old_connections()
    job = CatalogUpdateJob.objects.get(pk=job_id)
    try:
        result = callable_fn()
        if isinstance(result, dict) and not result.get("success", True):
            job.status = "error"
            job.detail = result.get("error", "Невідома помилка")
        else:
            job.status = "success"
            job.detail = _format_result(result)
    except Exception:
        job.status = "error"
        job.detail = traceback.format_exc(limit=3)
    finally:
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "detail", "finished_at"])
        close_old_connections()


def _format_result(result: Optional[dict]) -> str:
    if not result:
        return "Завершено."
    parts = [
        f"{key}: {value}"
        for key, value in result.items()
        if key not in ("success", "error", "errors")
        and not isinstance(value, (list, dict))
    ]
    errors = result.get("errors")
    text = ", ".join(parts) if parts else "Завершено."
    if errors:
        preview = "; ".join(str(e) for e in errors[:5])
        text += f" | Помилки ({len(errors)}): {preview}"
    return text


def start_job(
    request,
    supplier: str,
    action: str,
    callable_fn: Callable[[], dict],
    catalog_key: str = "",
) -> Optional[CatalogUpdateJob]:
    """Start a background thread running callable_fn, tracked via CatalogUpdateJob.

    Returns None (and does nothing) if a job with the same supplier/action/catalog_key
    is already running, to avoid duplicate concurrent runs.
    """
    already_running = CatalogUpdateJob.objects.filter(
        supplier=supplier, action=action, catalog_key=catalog_key, status="running"
    ).exists()
    if already_running:
        return None

    job = CatalogUpdateJob.objects.create(
        supplier=supplier,
        action=action,
        catalog_key=catalog_key,
        status="running",
        started_by=request.user if request.user.is_authenticated else None,
    )
    thread = threading.Thread(target=_run_job, args=(job.id, callable_fn), daemon=True)
    thread.start()
    return job
