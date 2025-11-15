import json
import logging
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Order, OrderStatus

logger = logging.getLogger(__name__)


def _get_status_by_salesdrive_id(status_id: Any) -> OrderStatus | None:
    """Return status mapped to SalesDrive status id."""
    try:
        status_id_int = int(status_id)
    except (TypeError, ValueError):
        return None
    return OrderStatus.objects.filter(salesdrive_status_id=status_id_int).first()


def _verify_request(request: HttpRequest) -> bool:
    """
    Ensure webhook is authorized via request metadata.

    SalesDrive не дозволяє вказати кастомний заголовок, тому, окрім X-Api-Key,
    підтримуємо `?token=<SECRET>` у URL.
    """
    secret = getattr(settings, "SALESDRIVE_WEBHOOK_SECRET", "")
    header_name = "X-Api-Key"

    if not secret:
        # Fail closed in production but keep local DX when secret intentionally unset.
        return settings.DEBUG

    provided_header = request.headers.get(header_name, "")
    provided_token = request.GET.get("token", "")

    if provided_header and constant_time_compare(provided_header, secret):
        return True
    if provided_token and constant_time_compare(provided_token, secret):
        return True
    return False


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

    mapped_status = _get_status_by_salesdrive_id(status_id)
    if not mapped_status:
        return JsonResponse({"status": "ignored", "reason": "status_not_mapped"})

    if order.status_id == mapped_status.id:
        return JsonResponse({"status": "ok", "updated": False})

    previous_status = order.status
    order.status = mapped_status
    order.save(update_fields=["status"])
    logger.info(
        "Order %s status updated via SalesDrive webhook: %s -> %s",
        order.id,
        previous_status.name if previous_status else None,
        mapped_status.name,
    )
    return JsonResponse(
        {"status": "ok", "updated": True, "new_status": mapped_status.slug, "label": mapped_status.name}
    )
