import logging
import re
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from fabric_category.models import FabricCategory
from furniture.models import Furniture, FurnitureCustomOption, FurnitureSizeVariant
from store.connection_utils import resilient_database_operation, save_form_draft, load_form_draft, clear_form_draft

from .forms import CheckoutForm
from .liqpay import (
    LiqPayConfigurationError,
    LiqPaySignatureMismatch,
    get_liqpay_client,
)
from .models import LiqPayReceipt, Order, OrderItem, OrderStatus
from .salesdrive import push_order_to_salesdrive

logger = logging.getLogger(__name__)

LIQPAY_ENDPOINT = "https://www.liqpay.ua/api/3/checkout"
SUCCESS_STATUSES = {"success", "sandbox", "wait_accept"}


def _ensure_liqpay_available() -> None:
    """Raise if LiqPay credentials are missing."""
    try:
        get_liqpay_client()
    except LiqPayConfigurationError:
        raise


def _format_amount(value: float | Decimal) -> Decimal:
    """Return LiqPay-friendly amount with 2 decimals."""
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError):
        raise ValueError("Сума замовлення некоректна")

    amount = amount.quantize(Decimal("0.01"))
    if amount <= 0:
        raise ValueError("Сума для оплати повинна бути більшою за нуль")
    return amount


def _build_liqpay_checkout_payload(order: Order, request: HttpRequest) -> dict[str, str]:
    """Prepare LiqPay data/signature payload."""
    client = get_liqpay_client()
    amount = _format_amount(order.total_amount)
    description = f"Замовлення #{order.id} на Montal Home"
    result_url = request.build_absolute_uri(reverse("checkout:liqpay_result"))
    server_url = request.build_absolute_uri(reverse("checkout:liqpay_callback"))

    data, signature = client.build_checkout(
        {
            "action": "pay",
            "amount": str(amount),
            "currency": getattr(settings, "LIQPAY_DEFAULT_CURRENCY", "UAH"),
            "description": description[:250],
            "order_id": f"MONTAL-{order.id}",
            "result_url": result_url,
            "server_url": server_url,
            "language": "uk",
            "sandbox": 1 if getattr(settings, "LIQPAY_SANDBOX", True) else 0,
            "paytypes": getattr(settings, "LIQPAY_PAYMENT_METHODS", "card,privat24,applepay"),
        }
    )
    return {
        "liqpay_data": data,
        "liqpay_signature": signature,
        "liqpay_endpoint": LIQPAY_ENDPOINT,
    }


def _extract_order_id(raw_order_id: str | None) -> int | None:
    """Convert LiqPay order_id (e.g. MONTAL-123) back to numeric ID."""
    if not raw_order_id:
        return None
    match = re.search(r"(\d+)$", str(raw_order_id))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _mark_order_paid(order: Order) -> None:
    """Mark order as confirmed and switch status to 'confirmed' if available."""
    update_fields: list[str] = []
    if not order.is_confirmed:
        order.is_confirmed = True
        update_fields.append("is_confirmed")

    confirmed_status = OrderStatus.objects.filter(slug="confirmed").first()
    if confirmed_status and order.status_id != confirmed_status.id:
        order.status = confirmed_status
        update_fields.append("status")

    if update_fields:
        order.save(update_fields=update_fields)


def _build_items_snapshot(order: Order) -> list[dict[str, object]]:
    items = []
    queryset = order.orderitem_set.select_related("furniture")
    for item in queryset:
        furniture_name = item.furniture.name if item.furniture_id else ""
        items.append(
            {
                "name": furniture_name,
                "quantity": item.quantity,
                "price": float(item.price),
                "total": float(item.price * item.quantity),
            }
        )
    return items


def _store_liqpay_receipt(order: Order, payload: dict) -> None:
    """Persist LiqPay receipt payload for auditing."""
    payment_id = payload.get("payment_id") or payload.get("order_id")
    receipt_url = payload.get("receipt_url") or payload.get("download_url") or ""
    amount_raw = payload.get("amount")
    try:
        amount = _format_amount(amount_raw)
    except Exception:
        amount = _format_amount(order.total_amount)

    defaults = {
        "payment_id": payment_id or "",
        "status": payload.get("status", ""),
        "amount": amount,
        "currency": payload.get("currency") or getattr(settings, "LIQPAY_DEFAULT_CURRENCY", "UAH"),
        "receipt_url": receipt_url,
        "items_snapshot": _build_items_snapshot(order),
        "raw_response": payload,
    }

    LiqPayReceipt.objects.update_or_create(order=order, defaults=defaults)


def checkout(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            cart = request.session.get("cart", {})
            if not cart:
                messages.error(request, "Кошик порожній!", extra_tags="user")
                return redirect("shop:view_cart")

            payment_type = form.cleaned_data["payment_type"]
            iban_invoice_requested = payment_type == "iban"
            if payment_type == "liqpay":
                try:
                    _ensure_liqpay_available()
                except LiqPayConfigurationError:
                    form.add_error(
                        "payment_type",
                        "Онлайн-оплата тимчасово недоступна. Оберіть інший спосіб.",
                    )
                    return render(request, "shop/checkout.html", {"form": form})

            try:
                # Use resilient database operation for order creation
                def create_order_operation():
                    # Prepare delivery data based on delivery type
                    delivery_type = form.cleaned_data["delivery_type"]
                    delivery_city = ""
                    delivery_branch = ""
                    delivery_address = ""

                    if delivery_type == "local":
                        delivery_city = "Доставка по місту"
                        delivery_address = form.cleaned_data["delivery_address"]
                    elif delivery_type == "nova_poshta":
                        delivery_city = form.cleaned_data["delivery_city_label"]
                        delivery_branch = form.cleaned_data["delivery_branch_name"]

                    with transaction.atomic():
                        order = Order.objects.create(
                            customer_name=form.cleaned_data["customer_name"],
                            customer_last_name=form.cleaned_data["customer_last_name"],
                            customer_phone_number=form.cleaned_data["customer_phone_number"],
                            customer_email=form.cleaned_data["customer_email"],
                            delivery_type=delivery_type,
                            delivery_city=delivery_city,
                            delivery_branch=delivery_branch,
                            delivery_address=delivery_address,
                            payment_type=form.cleaned_data["payment_type"],
                            iban_invoice_requested=iban_invoice_requested,
                        )
                        return order

                order = resilient_database_operation(create_order_operation)
                
                # Clear any saved drafts after successful order creation
                clear_form_draft(request, 'checkout_form')
                
            except Exception as e:
                # Save form data as draft for retry
                form_data = form.cleaned_data
                save_form_draft(request, form_data, 'checkout_form')
                
                messages.error(
                    request,
                    "Помилка при створенні замовлення. Ваші дані збережено як чернетку. Спробуйте ще раз.",
                    extra_tags="user",
                )
                return render(request, "shop/checkout.html", {"form": form})

            salesdrive_products = []

            # Process cart items with resilient database operations
            for cart_key, item_data in cart.items():
                # Extract furniture_id from the cart key
                furniture_id = cart_key.split('_')[0]
                furniture: Furniture = get_object_or_404(
                    Furniture, id=int(furniture_id)
                )
                
                # Handle both old format (just quantity) and new format (dict with quantity and attributes)
                if isinstance(item_data, dict):
                    quantity = item_data.get('quantity', 1)
                    size_variant_id = item_data.get('size_variant_id')
                    fabric_category_id = item_data.get('fabric_category_id')
                    variant_image_id = item_data.get('variant_image_id')
                    custom_option_id = item_data.get('custom_option_id')
                    custom_option_value_session = item_data.get('custom_option_value')
                    custom_option_price_session = item_data.get('custom_option_price')
                    color_id = item_data.get('color_id')
                    color_name_session = item_data.get('color_name')
                    color_palette_name_session = item_data.get('color_palette_name')
                    color_hex_session = item_data.get('color_hex')
                    color_image_session = item_data.get('color_image')
                else:
                    # Legacy format - just quantity
                    quantity = item_data
                    size_variant_id = None
                    fabric_category_id = None
                    variant_image_id = None
                    custom_option_id = None
                    custom_option_value_session = None
                    custom_option_price_session = None
                    color_id = None
                    color_name_session = ""
                    color_palette_name_session = ""
                    color_hex_session = ""
                    color_image_session = ""
                
                # Calculate price based on size variant and fabric
                size_variant = None
                size_variant_description = ""
                if size_variant_id and size_variant_id != 'base':
                    try:
                        size_variant = FurnitureSizeVariant.objects.get(id=size_variant_id)
                        price = float(size_variant.current_price)
                        size_variant_original_price = float(size_variant.price)
                        size_variant_is_promotional = size_variant.is_on_sale
                    except (FurnitureSizeVariant.DoesNotExist, ValueError):
                        price = float(furniture.current_price)
                        size_variant_original_price = None
                        size_variant_is_promotional = False
                else:
                    price = float(furniture.current_price)
                    size_variant_original_price = None
                    size_variant_is_promotional = False
                
                if size_variant:
                    if size_variant.parameter_value:
                        size_variant_description = size_variant.parameter_value
                    else:
                        size_variant_description = size_variant.dimensions

                # Add fabric cost if fabric is selected
                fabric_category = None
                if fabric_category_id:
                    try:
                        fabric_category = FabricCategory.objects.get(id=fabric_category_id)
                        fabric_cost = float(fabric_category.price) * float(furniture.fabric_value)
                        price += fabric_cost
                    except FabricCategory.DoesNotExist:
                        pass
                
                custom_option_obj = None
                custom_option_value_final = ""
                custom_option_name = furniture.custom_option_name or ""
                custom_option_price = 0.0

                if custom_option_id:
                    try:
                        option_id_int = int(custom_option_id)
                        custom_option_candidate = FurnitureCustomOption.objects.get(id=option_id_int)
                        if custom_option_candidate.furniture_id == furniture.id:
                            custom_option_obj = custom_option_candidate
                            custom_option_value_final = custom_option_candidate.value
                            custom_option_name = furniture.custom_option_name or ""
                        else:
                            custom_option_obj = None
                    except (ValueError, FurnitureCustomOption.DoesNotExist):
                        custom_option_obj = None

                if not custom_option_value_final and custom_option_value_session:
                    custom_option_value_final = str(custom_option_value_session)

                if custom_option_price_session not in (None, ""):
                    try:
                        custom_option_price = float(custom_option_price_session)
                    except (TypeError, ValueError):
                        custom_option_price = 0.0
                elif custom_option_obj:
                    try:
                        custom_option_price = float(custom_option_obj.price_delta)
                    except (TypeError, ValueError):
                        custom_option_price = 0.0

                if not custom_option_value_final:
                    custom_option_name = ""
                    custom_option_price = 0.0

                price += custom_option_price
                color_id_int = None
                color_name_final = color_name_session or ""
                color_palette_name_final = color_palette_name_session or ""
                color_hex_final = color_hex_session or ""
                color_image_final = color_image_session or ""
                if color_id:
                    try:
                        color_id_int = int(color_id)
                    except (TypeError, ValueError):
                        color_id_int = None
                color_label = color_name_final;

                description_parts = []
                if size_variant_description:
                    description_parts.append(f"Розмір: {size_variant_description}")
                if fabric_category:
                    description_parts.append(f"Тканина: {fabric_category.name}")
                if custom_option_value_final:
                    label = custom_option_name or "Опція"
                    description_parts.append(f"{label}: {custom_option_value_final}")
                if color_label:
                    description_parts.append(f"Колір: {color_label}")

                salesdrive_product = {
                    "id": furniture.article_code or str(furniture.id),
                    "name": furniture.name,
                    "costPerItem": round(price, 2),
                    "amount": quantity,
                }

                if furniture.article_code:
                    salesdrive_product["sku"] = furniture.article_code
                if description_parts:
                    salesdrive_product["description"] = "; ".join(description_parts)
                salesdrive_products.append(salesdrive_product)

                OrderItem.objects.create(
                    order=order,
                    furniture=furniture,
                    quantity=quantity,
                    price=price,
                    original_price=float(furniture.price),
                    is_promotional=furniture.is_promotional,
                    size_variant_original_price=size_variant_original_price,
                    size_variant_is_promotional=size_variant_is_promotional,
                    size_variant_id=None if size_variant_id == 'base' else size_variant_id,
                    fabric_category_id=fabric_category_id,
                    variant_image_id=variant_image_id,
                    custom_option=custom_option_obj,
                    custom_option_name=custom_option_name,
                    custom_option_value=custom_option_value_final,
                    custom_option_price=custom_option_price or None,
                    color_id=color_id_int,
                    color_name=color_name_final,
                    color_palette_name=color_palette_name_final,
                    color_hex=color_hex_final,
                    color_image_url=color_image_final,
                )

            push_order_to_salesdrive(order, salesdrive_products, form.cleaned_data)

            request.session["cart"] = {}
            request.session.modified = True

            if payment_type == "liqpay":
                try:
                    liqpay_context = _build_liqpay_checkout_payload(order, request)
                except (ValueError, LiqPayConfigurationError) as exc:
                    logger.exception("Не вдалося ініціювати LiqPay для замовлення %s: %s", order.id, exc)
                    messages.warning(
                        request,
                        "Замовлення створено, але онлайн-оплата недоступна. Менеджер зв'яжеться для уточнення оплати.",
                        extra_tags="user",
                    )
                    return redirect("shop:home")

                request.session["pending_liqpay_order_id"] = order.id
                return render(
                    request,
                    "checkout/liqpay_redirect.html",
                    {"order": order, **liqpay_context},
                )

            messages.success(request, "Замовлення успішно оформлено!", extra_tags="user")
            return redirect("shop:home")
    else:
        # Load draft data if available
        draft_data = load_form_draft(request, 'checkout_form')
        form = CheckoutForm(initial=draft_data or None)

        if draft_data:
            messages.info(
                request,
                "Чернетка замовлення відновлена. Перевірте дані та збережіть.",
                extra_tags="user",
            )

    return render(request, "shop/checkout.html", {"form": form})


def order_history(request: HttpRequest) -> HttpResponse:
    phone_number = request.GET.get("phone_number", "").strip()
    orders_data = []
    if phone_number:
        if not re.match(r"^0[0-9]{9}$", phone_number):
            messages.error(
                request,
                "Неправильно введений номер телефону! Формат: 0XXXXXXXXX",
                extra_tags="user",
            )
        else:
            orders = (
                Order.objects.filter(customer_phone_number=phone_number)
                .order_by("-created_at")
                .prefetch_related("orderitem_set__furniture", "orderitem_set__custom_option")
            )
            if not orders.exists():
                messages.info(
                    request,
                    "Замовлення не знайдено для цього номера телефону.",
                    extra_tags="user",
                )
            else:
                for order in orders:
                    total_price = sum(
                        item.price * item.quantity for item in order.orderitem_set.all()
                    )
                    orders_data.append(
                        {
                            "order": order,
                            "items": order.orderitem_set.all(),
                            "total_price": float(total_price),
                        }
                    )
    # Get all fabric categories for display in order history
    fabric_categories = FabricCategory.objects.all()
    
    return render(
        request,
        "shop/order_history.html",
        {"orders_data": orders_data, "phone_number": phone_number, "fabric_categories": fabric_categories},
    )


@csrf_exempt
@require_POST
def liqpay_callback(request: HttpRequest) -> JsonResponse:
    """Server-to-server LiqPay webhook."""
    try:
        client = get_liqpay_client()
    except LiqPayConfigurationError:
        logger.warning("LiqPay callback received but integration is not configured")
        return JsonResponse({"status": "disabled"}, status=503)

    data = request.POST.get("data")
    signature = request.POST.get("signature")
    if not data or not signature:
        return JsonResponse({"status": "error", "reason": "missing_fields"}, status=400)

    try:
        payload = client.decode(data, signature)
    except LiqPaySignatureMismatch:
        logger.warning("LiqPay callback signature mismatch")
        return JsonResponse({"status": "error", "reason": "signature"}, status=400)

    order_id = _extract_order_id(payload.get("order_id"))
    if not order_id:
        return JsonResponse({"status": "error", "reason": "order_id"}, status=400)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.warning("LiqPay callback referenced unknown order %s", order_id)
        return JsonResponse({"status": "error", "reason": "not_found"}, status=404)

    status = (payload.get("status") or "").lower()
    if status in SUCCESS_STATUSES:
        _mark_order_paid(order)
        _store_liqpay_receipt(order, payload)
        logger.info("Order %s marked as paid via LiqPay callback (%s)", order_id, status)
    else:
        logger.info("LiqPay callback for order %s with status %s", order_id, status)

    return JsonResponse({"status": "ok"})


@csrf_exempt
def liqpay_result(request: HttpRequest) -> HttpResponse:
    """Handle customer redirect after LiqPay payment."""
    data = request.POST.get("data") or request.GET.get("data")
    signature = request.POST.get("signature") or request.GET.get("signature")
    pending_order_id = request.session.get("pending_liqpay_order_id")
    payload = {}

    if data and signature:
        try:
            client = get_liqpay_client()
            payload = client.decode(data, signature)
        except (LiqPayConfigurationError, LiqPaySignatureMismatch) as exc:
            logger.warning("Failed to decode LiqPay result: %s", exc)
            payload = {}
    if not payload:
        fallback_status = request.POST.get("status") or request.GET.get("status")
        fallback_order = request.POST.get("order_id") or request.GET.get("order_id")
        if fallback_status or fallback_order:
            payload = {
                "status": fallback_status,
                "order_id": fallback_order,
            }

    order_id = _extract_order_id(payload.get("order_id"))
    status = (payload.get("status") or "").lower()
    resolved_order_id = order_id or pending_order_id
    payment_confirmed = False
    order = None

    if resolved_order_id:
        try:
            order = Order.objects.get(id=resolved_order_id)
        except Order.DoesNotExist:
            logger.warning("LiqPay result referenced unknown order %s", resolved_order_id)
        else:
            if status in SUCCESS_STATUSES:
                _mark_order_paid(order)
                if payload:
                    _store_liqpay_receipt(order, payload)
                payment_confirmed = True
            elif order.is_confirmed:
                payment_confirmed = True

    request.session.pop("pending_liqpay_order_id", None)
    request.session.modified = True

    if payment_confirmed:
        messages.success(
            request,
            "Оплату отримано. Дякуємо за замовлення!",
            extra_tags="user",
        )
    elif order:
        messages.info(
            request,
            "Платіж обробляється платіжною системою. Як тільки отримаємо підтвердження, менеджер повідомить про статус замовлення.",
            extra_tags="user",
        )
    else:
        messages.warning(
            request,
            "Не вдалося підтвердити оплату. Якщо кошти були списані, зв'яжіться з менеджером.",
            extra_tags="user",
        )

    return redirect("shop:home")
