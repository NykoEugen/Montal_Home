import json
from types import SimpleNamespace
from typing import List, Set

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator
from fabric_category.models import FabricCategory
from furniture.models import Furniture


def furniture_detail(request: HttpRequest, furniture_slug: str) -> HttpResponse:
    furniture = get_object_or_404(Furniture, slug=furniture_slug)
    raw_parameters = furniture.parameters.select_related("parameter").all()
    size_variants = furniture.get_size_variants()
    variant_images = list(furniture.variant_images.all())
    extra_gallery_images = list(getattr(furniture, "images").all()) if hasattr(furniture, "images") else []

    gallery_images: List[SimpleNamespace] = []
    seen_urls: Set[str] = set()

    def add_gallery_image(image_field, alt_text: str, is_primary: bool = False) -> None:
        if not image_field:
            return
        try:
            image_url = image_field.url
        except Exception:
            return
        if image_url in seen_urls:
            return
        seen_urls.add(image_url)
        gallery_images.append(
            SimpleNamespace(
                image=image_field,
                alt_text=alt_text or furniture.name,
                is_primary=is_primary,
            )
        )

    add_gallery_image(getattr(furniture, "image", None), furniture.name, is_primary=True)

    for img in extra_gallery_images:
        add_gallery_image(getattr(img, "image", None), getattr(img, "alt_text", furniture.name))

    if not gallery_images and variant_images:
        # Ensure at least one image is available by falling back to default variant photo.
        default_variant = next((variant for variant in variant_images if getattr(variant, "is_default", False)), None)
        fallback_variant = default_variant or variant_images[0]
        add_gallery_image(getattr(fallback_variant, "image", None), getattr(fallback_variant, "name", furniture.name), is_primary=True)

    # Determine which stock status label to show by default
    initial_stock_status = furniture.stock_status
    initial_stock_label = furniture.get_stock_status_display()
    if variant_images:
        default_variant = next((variant for variant in variant_images if variant.is_default), None)
        if default_variant is None:
            default_variant = variant_images[0]
        if default_variant and default_variant.stock_status:
            initial_stock_status = default_variant.stock_status
            initial_stock_label = default_variant.get_stock_status_display()
    
    # Debug: Print size variants info
    print(f"Debug: Furniture '{furniture.name}' has {len(size_variants)} size variants")
    for variant in size_variants:
        print(f"  - {variant.dimensions}: Current={variant.current_price}, Original={variant.price}, OnSale={variant.is_on_sale}")

    # Virtual parameter structure for consistent template access
    class VirtualParameter:
        def __init__(self, key: str, label: str, value: str, base_value: str | None = None):
            self.key = key
            self.label = label
            self.value = value
            self.base_value = base_value or value

    # Process parameters to combine dimensions and normalize others
    parameters: list[VirtualParameter] = []
    dimensions: dict[str, str] = {}

    for param in raw_parameters:
        param_key = getattr(param.parameter, 'key', '')
        param_label = getattr(param.parameter, 'label', '')
        if param_key in ['height', 'width', 'length']:
            dimensions[param_key] = param.value
        else:
            parameters.append(VirtualParameter(param_key, param_label, param.value))

    # Add combined dimensions parameter if dimensions exist
    if dimensions:
        height = dimensions.get('height', '0')
        width = dimensions.get('width', '0')
        length = dimensions.get('length', '0')
        # Ensure integers for display
        try:
            height_i = int(float(height))
            width_i = int(float(width))
            length_i = int(float(length))
        except ValueError:
            height_i, width_i, length_i = height, width, length
        combined_dimensions = f"{length_i}x{width_i}x{height_i} см"
        # Insert dimensions at the beginning with requested label
        parameters.insert(0, VirtualParameter('dimensions', 'Розмір (ДхШхВ)', combined_dimensions, combined_dimensions))
    else:
        combined_dimensions = ""

    fabric_categories = []
    if furniture.selected_fabric_brand:
        fabric_categories = FabricCategory.objects.filter(
            brand=furniture.selected_fabric_brand
        )
    # Default to the new (v2) template; allow forcing old via ?v=1
    template_name = "furniture/furniture_detail_alt.html"
    if request.GET.get("v") == "1":
        template_name = "furniture/furniture_detail.html"

    # Determine base size variant if any matches combined dimensions
    base_size_variant_id: int | None = None
    if combined_dimensions and size_variants:
        for variant in size_variants:
            try:
                if variant.dimensions == combined_dimensions:
                    base_size_variant_id = variant.id
                    break
            except Exception:
                continue

    custom_options = list(
        furniture.custom_options.filter(is_active=True).order_by("position", "id")
    )

    absolute_images: list[str] = []
    for gallery_image in gallery_images:
        image_field = getattr(gallery_image, "image", None)
        if not image_field:
            continue
        try:
            absolute_images.append(request.build_absolute_uri(image_field.url))
        except Exception:
            continue

    default_image_url = request.build_absolute_uri(static("images/logo.jpg"))
    if not absolute_images:
        absolute_images.append(default_image_url)

    product_url = request.build_absolute_uri(
        reverse("furniture:furniture_detail", kwargs={"furniture_slug": furniture.slug})
    )
    description_text = Truncator(strip_tags(furniture.description or furniture.name)).chars(
        160, truncate="…"
    )
    keywords = [
        furniture.name,
        getattr(furniture.sub_category, "name", None),
        getattr(getattr(furniture.sub_category, "category", None), "name", None),
        "меблі Montal Home",
    ]
    meta_keywords = ", ".join([word for word in keywords if word])

    availability_map = {
        "in_stock": "https://schema.org/InStock",
        "on_order": "https://schema.org/PreOrder",
    }
    offer_price = (
        furniture.promotional_price
        if furniture.is_promotional and furniture.promotional_price
        else furniture.price
    )
    price_value = format(offer_price, ".2f")
    offers_data = {
        "@type": "Offer",
        "url": product_url,
        "priceCurrency": "UAH",
        "price": price_value,
        "availability": availability_map.get(initial_stock_status, "https://schema.org/InStock"),
        "itemCondition": "https://schema.org/NewCondition",
        "seller": {
            "@type": "Organization",
            "name": "Montal Home",
            "url": getattr(settings, "SITE_BASE_URL", "https://montal.com.ua"),
        },
    }
    if furniture.sale_end_date:
        offers_data["priceValidUntil"] = furniture.sale_end_date.date().isoformat()

    brand_name = getattr(
        getattr(furniture.sub_category, "category", None), "name", "Montal Home"
    )
    product_schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "@id": f"{product_url}#product",
        "name": furniture.name,
        "description": strip_tags(furniture.description or furniture.name),
        "sku": furniture.article_code,
        "image": absolute_images,
        "brand": {
            "@type": "Brand",
            "name": brand_name,
        },
        "category": getattr(furniture.sub_category, "name", ""),
        "offers": offers_data,
    }

    context = {
        "furniture": furniture,
        "parameters": parameters,
        "size_variants": size_variants,
        "variant_images": variant_images,
        "gallery_images": gallery_images,
        "fabric_categories": fabric_categories,
        "base_dimensions": combined_dimensions,
        "base_size_variant_id": base_size_variant_id,
        "initial_stock_status": initial_stock_status,
        "initial_stock_label": initial_stock_label,
        "custom_option_name": furniture.custom_option_name,
        "custom_options": custom_options,
        "meta_title": f"{furniture.name} — купити у Montal Home",
        "meta_description": description_text,
        "meta_keywords": meta_keywords,
        "og_image": absolute_images[0],
        "og_type": "product",
        "twitter_card": "summary_large_image",
        "canonical_url": product_url,
        "og_url": product_url,
        "product_schema": json.dumps(product_schema, ensure_ascii=False),
    }

    return render(request, template_name, context)
