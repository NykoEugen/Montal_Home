import logging
import re
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _clean_phone(phone: str) -> str:
    """Leave only digits to match SalesDrive expectations."""
    digits = re.sub(r"\D", "", phone or "")
    return digits


class SalesDriveClient:
    """Minimal client wrapper for SalesDrive order submission."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: int = 10,
    ) -> None:
        self.api_key = api_key or getattr(settings, "SALESDRIVE_API_KEY", "")
        self.endpoint = endpoint or getattr(
            settings, "SALESDRIVE_API_ENDPOINT", "https://montal.salesdrive.me/handler/"
        )
        self.timeout = timeout

    @property
    def is_enabled(self) -> bool:
        return bool(self.api_key and self.endpoint)

    def submit_order(
        self,
        order,
        products: List[Dict[str, Any]],
        form_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send order payload to SalesDrive API."""
        if not self.is_enabled:
            logger.debug("SalesDrive integration skipped: API key or endpoint missing")
            return None

        if not products:
            logger.info("SalesDrive payload skipped: order %s has no products", order.id)
            return None

        payload = self._build_payload(order, products, form_data or {})
        headers = {"X-Api-Key": self.api_key}

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("SalesDrive order sync failed for order %s: %s", order.id, exc)
            return None

        try:
            body = response.json()
        except ValueError:
            logger.error(
                "SalesDrive response is not valid JSON for order %s: %s",
                order.id,
                response.text[:500],
            )
            return None

        if not body.get("success"):
            logger.error("SalesDrive responded with an error for order %s: %s", order.id, body)
            return body

        logger.info("SalesDrive order %s synced successfully: %s", order.id, body)
        return body

    def _build_payload(
        self,
        order,
        products: List[Dict[str, Any]],
        form_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Assemble SalesDrive payload from order and form data."""
        shipping_method_map = {
            "nova_poshta": "novaposhta",
            "local": "local",
        }
        payment_method_map = {
            "iban": "IBAN",
        }

        shipping_method = shipping_method_map.get(order.delivery_type, order.delivery_type)
        payment_method = payment_method_map.get(order.payment_type, order.payment_type)

        shipping_address = ""
        if order.delivery_type == "local":
            shipping_address = order.delivery_address
        elif order.delivery_type == "nova_poshta":
            shipping_address = ", ".join(
                part for part in [order.delivery_city, order.delivery_branch] if part
            )

        payload: Dict[str, Any] = {
            "getResultData": 1,
            "fName": order.customer_name,
            "lName": order.customer_last_name,
            "phone": _clean_phone(order.customer_phone_number),
            "email": order.customer_email,
            "products": products,
            "payment_method": payment_method,
            "shipping_method": shipping_method,
            "shipping_address": shipping_address,
            "externalId": str(order.id),
            "sajt": getattr(settings, "SITE_BASE_URL", ""),
            "comment": self._build_comment(order),
        }

        if not order.customer_email:
            payload.pop("email")

        if order.delivery_type == "nova_poshta":
            payload["novaposhta"] = self._nova_poshta_payload(order, form_data)

        return payload

    def _nova_poshta_payload(self, order, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare Nova Poshta specific data block."""
        return {
            "ServiceType": "Warehouse",
            "city": form_data.get("delivery_city") or order.delivery_city,
            "cityNameFormat": "short",
            "WarehouseNumber": form_data.get("delivery_branch") or order.delivery_branch,
            "payer": "recipient",
            "ttn": "",
        }

    def _build_comment(self, order) -> str:
        """Generate short comment with delivery/payment summary."""
        delivery = "Нова Пошта" if order.delivery_type == "nova_poshta" else "Доставка по місту"
        payment = "IBAN" if order.payment_type == "iban" else order.payment_type
        return f"Замовлення з сайту {getattr(settings, 'SITE_DOMAIN', '')}. Доставка: {delivery}. Оплата: {payment}."


salesdrive_client = SalesDriveClient()


def push_order_to_salesdrive(
    order,
    products: List[Dict[str, Any]],
    form_data: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Helper for views to submit orders without importing the class."""
    return salesdrive_client.submit_order(order, products, form_data=form_data)
