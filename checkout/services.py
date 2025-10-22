import logging
from contextlib import contextmanager

import requests
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _get_notification_recipients():
    recipients = getattr(settings, "ORDER_NOTIFICATION_RECIPIENTS", None)
    if not recipients:
        return []
    if isinstance(recipients, str):
        recipients = [item.strip() for item in recipients.split(",")]
    return [email for email in recipients if email]


def notify_staff_about_new_order(order):
    recipients = _get_notification_recipients()
    if not recipients:
        return

    context = {
        "order": order,
        "items": order.orderitem_set.select_related("furniture").all(),
    }
    subject = f"Нове замовлення #{order.id}"
    body = render_to_string("emails/new_order_notification.txt", context)
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=recipients,
    )
    try:
        email.send(fail_silently=False)
    except Exception as exc:
        logger.warning("Failed to send staff notification for order %s: %s", order.id, exc)

    _send_telegram_message(context)


def _send_telegram_message(context):
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return

    order = context["order"]
    items = context["items"]
    item_lines = "\n".join(
        f"• {item.furniture.name} x{item.quantity}" for item in items
    )
    message = (
        f"Нове замовлення #{order.id}\n"
        f"Клієнт: {order.customer_name} {order.customer_last_name}\n"
        f"Телефон: {order.customer_phone_number}\n"
        f"Оплата: {order.get_payment_type_display()}\n"
        f"Доставка: {order.get_delivery_type_display()}\n"
        f"Сума: {order.total_amount:.2f} грн\n"
        f"Товари:\n{item_lines}"
    )
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    try:
        requests.post(url, data=data, timeout=10)
    except requests.RequestException as exc:
        logger.warning("Failed to send Telegram notification for order %s: %s", order.id, exc)


def send_payment_request_to_customer(order, comment: str | None = None):
    if not order.customer_email:
        return False

    subject = f"Оплата замовлення #{order.id}"
    template_name = (
        "emails/payment_request_iban.txt"
        if order.payment_type == "iban"
        else "emails/payment_request_liqpay.txt"
    )
    context = {
        "order": order,
        "items": order.orderitem_set.select_related("furniture").all(),
        "comment": comment if comment is not None else order.customer_message,
        "payment_link": order.payment_link,
        "iban_details": getattr(settings, "PAYMENT_IBAN_DETAILS", ""),
    }
    body = render_to_string(template_name, context)
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[order.customer_email],
    )

    @contextmanager
    def maybe_attachment():
        if order.payment_instructions_file:
            file = order.payment_instructions_file.open("rb")
            try:
                yield file
            finally:
                file.close()
        else:
            yield None

    with maybe_attachment() as attachment:
        if attachment:
            email.attach(
                order.payment_instructions_file.name.split("/")[-1],
                attachment.read(),
            )
        try:
            email.send(fail_silently=False)
        except Exception as exc:
            logger.warning("Failed to send payment request for order %s: %s", order.id, exc)
            return False

    return True
