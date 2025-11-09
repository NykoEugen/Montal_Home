import json
import logging
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Order

logger = logging.getLogger(__name__)


STATUS_ID_MAP = {
    1: "new",          # Новий
    2: "processing",   # Підтверджено
    3: "processing",   # На відправку
    4: "shipped",      # Відправлено
    5: "completed",    # Продаж
    6: "canceled",     # Відмова
    7: "canceled",     # Повернення
    8: "canceled",     # Видалений
}


def _verify_request(request: HttpRequest) -> bool:
    """Ensure webhook is authorized via X-Api-Key header."""
    secret = getattr(settings, "SALESDRIVE_WEBHOOK_SECRET", "")
    if not secret:
        return True
    return request.headers.get("X-Api-Key") == secret


def _parse_payload(body: bytes) -> Dict[str, Any]:
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc


@csrf_exempt
@require_POST
def salesdrive_order_status_webhook(request: HttpRequest) -> JsonResponse:
    """Handle SalesDrive order status updates."""
    if not _verify_request(request):
        logger.warning("SalesDrive webhook rejected due to invalid API key")
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = _parse_payload(request.body)
    except ValueError as exc:
        logger.warning("SalesDrive webhook received invalid payload: %s", exc)
        return JsonResponse({"error": "invalid_json", "details": str(exc)}, status=400)

    info = payload.get("info") or {}
    if info.get("webhookType") != "order":
        return JsonResponse({"status": "ignored", "reason": "unsupported_type"})

    event = info.get("webhookEvent")
    if event not in {"status_change", "new_order"}:
        return JsonResponse({"status": "ignored", "reason": "unsupported_event"})

    data = payload.get("data") or {}
    external_id = data.get("externalId")
    status_id = data.get("statusId")

    if not external_id:
        return JsonResponse({"error": "missing_external_id"}, status=400)

    try:
        order_id = int(external_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid_external_id"}, status=400)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.warning("SalesDrive webhook referenced unknown order ID %s", order_id)
        return JsonResponse({"status": "ignored", "reason": "order_not_found"})

    try:
        status_id_int = int(status_id)
    except (TypeError, ValueError):
        status_id_int = None

    mapped_status = STATUS_ID_MAP.get(status_id_int) if status_id_int is not None else None
    if not mapped_status:
        return JsonResponse({"status": "ignored", "reason": "status_not_mapped"})

    if order.status == mapped_status:
        return JsonResponse({"status": "ok", "updated": False})

    previous_status = order.status
    order.status = mapped_status
    order.save(update_fields=["status"])
    logger.info(
        "Order %s status updated via SalesDrive webhook: %s -> %s",
        order.id,
        previous_status,
        mapped_status,
    )
    return JsonResponse({"status": "ok", "updated": True, "new_status": mapped_status})
