"""Checkout app signals."""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .invoice import generate_and_upload_invoice
from .models import Order

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def create_invoice_after_confirmation(sender, instance: Order, created: bool, **kwargs) -> None:
    """Generate invoice PDF once the order is confirmed."""
    if not instance.is_confirmed:
        return

    if instance.invoice_pdf_url:
        return

    try:
        pdf_path, pdf_url = generate_and_upload_invoice(instance)
        instance.mark_invoice_generated(pdf_path, pdf_url)
        instance.refresh_from_db(fields=["invoice_pdf_path", "invoice_pdf_url", "invoice_generated_at"])
    except Exception:
        logger.exception("Failed to generate invoice for order %s", instance.pk)
