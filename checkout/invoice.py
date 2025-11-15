"""Utilities for building and uploading order invoices."""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.html import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Order

logger = logging.getLogger(__name__)


def _candidate_font_paths() -> Iterable[Path]:
    configured = getattr(settings, "INVOICE_FONT_PATH", "")
    if configured:
        yield Path(configured).expanduser()

    base_dir = Path(getattr(settings, "BASE_DIR", "."))
    defaults = [
        base_dir / "static" / "fonts" / "DejaVuSans.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in defaults:
        yield path


def _ensure_font() -> str:
    for candidate in _candidate_font_paths():
        try:
            if candidate.exists():
                pdfmetrics.registerFont(TTFont("InvoiceFont", str(candidate)))
                return "InvoiceFont"
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Unable to register font at %s", candidate)
    logger.warning(
        "Falling back to Helvetica for invoices; configure INVOICE_FONT_PATH for Cyrillic support."
    )
    return "Helvetica"


def _format_currency(value: Decimal | float) -> str:
    quantized = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


def _load_logo_flowable() -> Image | None:
    logo_source = getattr(settings, "INVOICE_LOGO_URL", "")
    if not logo_source:
        return None

    try:
        if logo_source.startswith(("http://", "https://")):
            import requests

            response = requests.get(logo_source, timeout=5)
            response.raise_for_status()
            image_stream = BytesIO(response.content)
            image_stream.seek(0)
            source_for_image = image_stream
        else:
            image_path = Path(logo_source).expanduser()
            if not image_path.exists():
                logger.warning("Invoice logo not found at %s", image_path)
                return None
            source_for_image = str(image_path)

        reader = ImageReader(source_for_image)
        width_px, height_px = reader.getSize()
        if width_px == 0 or height_px == 0:
            logger.warning("Invoice logo has invalid dimensions: %s", logo_source)
            return None

        max_width = 60 * mm
        max_height = 30 * mm
        scale = min(max_width / width_px, max_height / height_px, 1)
        display_width = width_px * scale
        display_height = height_px * scale

        if isinstance(source_for_image, BytesIO):
            source_for_image.seek(0)

        logo = Image(source_for_image, width=display_width, height=display_height)
        logo.hAlign = "LEFT"
        return logo
    except Exception:
        logger.exception("Unable to load invoice logo from %s", logo_source)
        return None


def _build_document(order: Order, font_name: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=25 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    styles["Normal"].fontName = font_name
    styles["Normal"].fontSize = 10
    styles["Heading1"].fontName = font_name
    styles["Heading1"].fontSize = 16
    styles["Heading1"].leading = 20
    styles.add(
        ParagraphStyle(
            name="InfoSmall",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=9,
            leading=11,
        )
    )

    elements: list = []

    logo = _load_logo_flowable()
    if logo:
        elements.append(logo)
        elements.append(Spacer(1, 8))

    generated_at = timezone.localtime(timezone.now())
    invoice_title = f"<b>Рахунок-фактура № {order.id:06d}</b>"
    elements.append(Paragraph(invoice_title, styles["Heading1"]))
    elements.append(
        Paragraph(
            f"Дата формування: {generated_at.strftime('%d.%m.%Y %H:%M')}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 10))

    company_lines = [
        settings.INVOICE_COMPANY_NAME or "",
        settings.INVOICE_COMPANY_ADDRESS or "",
    ]
    contact_parts = [
        part
        for part in (
            settings.INVOICE_COMPANY_PHONE,
            settings.INVOICE_COMPANY_EMAIL,
        )
        if part
    ]
    if contact_parts:
        company_lines.append(", ".join(contact_parts))

    elements.append(Paragraph("<b>Продавець:</b>", styles["Normal"]))
    for line in filter(None, company_lines):
        elements.append(Paragraph(escape(line), styles["InfoSmall"]))
    if settings.INVOICE_IBAN:
        elements.append(
            Paragraph(f"IBAN: {escape(settings.INVOICE_IBAN)}", styles["InfoSmall"])
        )
    if settings.INVOICE_EDRPOU:
        elements.append(
            Paragraph(f"ЄДРПОУ: {escape(settings.INVOICE_EDRPOU)}", styles["InfoSmall"])
        )
    elements.append(Spacer(1, 8))

    buyer_lines = [order.customer_full_name, order.customer_phone_number or ""]
    if order.customer_email:
        buyer_lines.append(order.customer_email)
    delivery_parts = [
        order.get_delivery_type_display() if hasattr(order, "get_delivery_type_display") else "",
        order.delivery_city or "",
        order.delivery_branch or "",
        order.delivery_address or "",
    ]

    elements.append(Paragraph("<b>Покупець:</b>", styles["Normal"]))
    for line in filter(None, buyer_lines):
        elements.append(Paragraph(escape(line), styles["InfoSmall"]))
    delivery_text = ", ".join(filter(None, delivery_parts))
    if delivery_text:
        elements.append(Paragraph(escape(delivery_text), styles["InfoSmall"]))
    elements.append(Spacer(1, 12))

    table_data = [["№", "Товар", "Кількість", "Ціна, грн", "Сума, грн"]]
    items = order.orderitem_set.select_related("furniture").all()
    for idx, item in enumerate(items, start=1):
        name_parts = [item.furniture.name if item.furniture_id else "Товар"]
        if item.custom_option_name and item.custom_option_value:
            name_parts.append(f"{item.custom_option_name}: {item.custom_option_value}")
        if item.size_variant_display:
            name_parts.append(f"Розмір: {item.size_variant_display}")
        if item.variant_image_display:
            name_parts.append(f"Варіант: {item.variant_image_display}")
        if item.fabric_category_display:
            name_parts.append(f"Тканина: {item.fabric_category_display}")
        if item.color_display:
            name_parts.append(f"Колір: {item.color_display}")
        item_name = "; ".join(name_parts)

        table_data.append(
            [
                str(idx),
                item_name,
                str(item.quantity),
                _format_currency(item.price),
                _format_currency(item.price * item.quantity),
            ]
        )

    table = Table(
        table_data,
        colWidths=[12 * mm, 80 * mm, 25 * mm, 30 * mm, 30 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5efe6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#333333")),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0c7ba")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fbf7f2")]),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 12))

    total_amount = order.total_amount
    elements.append(
        Paragraph(
            f"<b>Разом до сплати:</b> {_format_currency(total_amount)} грн",
            styles["Normal"],
        )
    )

    payment_terms_days = getattr(settings, "INVOICE_PAYMENT_TERMS_DAYS", 3)
    note_lines = [
        "Оплата здійснюється на рахунок IBAN, якщо інше не погоджено.",
    ]
    if payment_terms_days:
        note_lines.append(
            f"Оплатити протягом {payment_terms_days} днів з моменту виставлення рахунку."
        )
    note_lines.append("Доставка виконується після підтвердження замовлення.")
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>Примітка:</b>", styles["Normal"]))
    for line in note_lines:
        elements.append(Paragraph(escape(line), styles["InfoSmall"]))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def generate_and_upload_invoice(order: Order) -> tuple[str, str]:
    """Create invoice PDF, upload it to the configured storage and return path/url."""
    font_name = _ensure_font()
    pdf_bytes = _build_document(order, font_name)

    timestamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
    filename = f"order_{order.id}_invoice_{timestamp}.pdf"
    storage_path = f"invoices/{filename}"

    if order.invoice_pdf_path:
        try:
            default_storage.delete(order.invoice_pdf_path)
        except Exception:  # pragma: no cover - best effort cleanup
            logger.exception("Unable to delete previous invoice %s", order.invoice_pdf_path)

    saved_path = default_storage.save(storage_path, ContentFile(pdf_bytes))
    file_url = default_storage.url(saved_path)
    return saved_path, file_url
