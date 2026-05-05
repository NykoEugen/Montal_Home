from fabric_category.models import FabricCategory, FabricColor
from furniture.models import Furniture, FurnitureSizeVariant


def build_cart_context(session: dict) -> dict:
    """Return cart_items list, total_price, and fabric_categories from session data."""
    cart = session.get("cart", {})
    if not cart:
        return {"cart_items": [], "total_price": 0.0, "fabric_categories": FabricCategory.objects.none()}

    furniture_ids: set[int] = set()
    size_variant_ids: set[int] = set()
    fabric_category_ids: set[int] = set()
    color_ids: set[int] = set()

    for cart_key, item_data in cart.items():
        try:
            furniture_ids.add(int(cart_key.split("_")[0]))
        except (TypeError, ValueError):
            continue
        if isinstance(item_data, dict):
            sv = item_data.get("size_variant_id")
            fc = item_data.get("fabric_category_id")
            ci = item_data.get("color_id")
            if sv not in (None, "", "base"):
                try:
                    size_variant_ids.add(int(sv))
                except (TypeError, ValueError):
                    pass
            if fc:
                try:
                    fabric_category_ids.add(int(fc))
                except (TypeError, ValueError):
                    pass
            if ci:
                try:
                    color_ids.add(int(ci))
                except (TypeError, ValueError):
                    pass

    furniture_map = {
        obj.id: obj
        for obj in Furniture.objects.filter(id__in=furniture_ids).prefetch_related("custom_options")
    }
    size_variant_map = FurnitureSizeVariant.objects.in_bulk(size_variant_ids)
    fabric_category_map = FabricCategory.objects.in_bulk(fabric_category_ids)
    fabric_color_map = {
        c.id: c
        for c in FabricColor.objects.select_related("palette").filter(id__in=color_ids)
    }

    cart_items = []
    total_price = 0.0

    for cart_key, item_data in cart.items():
        try:
            furniture_id = int(cart_key.split("_")[0])
        except (TypeError, ValueError):
            continue
        furniture = furniture_map.get(furniture_id)
        if not furniture:
            continue

        if isinstance(item_data, dict):
            quantity = item_data.get("quantity", 1)
            size_variant_id = item_data.get("size_variant_id")
            fabric_category_id = item_data.get("fabric_category_id")
            variant_image_id = item_data.get("variant_image_id")
            custom_option_id = item_data.get("custom_option_id")
            custom_option_value = item_data.get("custom_option_value")
            custom_option_price_raw = item_data.get("custom_option_price")
            custom_option_name_stored = item_data.get("custom_option_name")
            color_id = item_data.get("color_id")
            color_name = item_data.get("color_name")
            color_palette_name = item_data.get("color_palette_name")
            color_hex = item_data.get("color_hex")
            color_image = item_data.get("color_image")
        else:
            quantity = item_data
            size_variant_id = fabric_category_id = variant_image_id = None
            custom_option_id = custom_option_value = custom_option_price_raw = None
            custom_option_name_stored = color_id = None
            color_name = color_palette_name = color_hex = color_image = ""

        size_variant = None
        if size_variant_id and size_variant_id != "base":
            try:
                size_variant = size_variant_map.get(int(size_variant_id))
                item_price = float(size_variant.current_price) if size_variant else float(furniture.current_price)
            except (TypeError, ValueError):
                item_price = float(furniture.current_price)
        else:
            item_price = float(furniture.current_price)

        if fabric_category_id:
            try:
                fabric_cat = fabric_category_map.get(int(fabric_category_id))
                if fabric_cat:
                    item_price += float(fabric_cat.price) * float(furniture.fabric_value)
            except (TypeError, ValueError):
                pass

        custom_option = None
        custom_option_value_resolved = ""
        custom_option_name_resolved = custom_option_name_stored or ""
        custom_option_price = 0.0
        if custom_option_price_raw not in (None, ""):
            try:
                custom_option_price = float(custom_option_price_raw)
            except (TypeError, ValueError):
                pass
        if custom_option_id:
            try:
                option_id_int = int(custom_option_id)
                custom_option = next(
                    (opt for opt in furniture.custom_options.all() if opt.id == option_id_int), None
                )
            except (ValueError, TypeError):
                pass
            if custom_option:
                custom_option_value_resolved = custom_option.value
                custom_option_name_resolved = furniture.custom_option_name
                if custom_option_price_raw in (None, ""):
                    try:
                        custom_option_price = float(custom_option.price_delta)
                    except (TypeError, ValueError):
                        pass
            elif custom_option_value:
                custom_option_value_resolved = str(custom_option_value)
        elif custom_option_value:
            custom_option_value_resolved = str(custom_option_value)

        if not custom_option_value_resolved:
            custom_option_name_resolved = ""

        color_display = color_name or ""
        if color_id and not color_name:
            try:
                color_obj = fabric_color_map.get(int(color_id))
                if color_obj:
                    color_name = color_obj.name
                    color_palette_name = color_obj.palette.name if color_obj.palette else ""
                    color_hex = color_hex or (color_obj.hex_code or "")
                    if not color_image and color_obj.image:
                        try:
                            color_image = color_obj.image.url
                        except (ValueError, OSError):
                            color_image = ""
                    color_display = color_name
                else:
                    color_name = color_name or ""
                    color_palette_name = color_palette_name or ""
            except (TypeError, ValueError):
                pass

        item_price += custom_option_price
        total_price += item_price * quantity
        cart_items.append(
            {
                "furniture": furniture,
                "quantity": quantity,
                "item_price": item_price,
                "size_variant_id": size_variant_id,
                "size_variant": size_variant,
                "fabric_category_id": fabric_category_id,
                "variant_image_id": variant_image_id,
                "custom_option_id": custom_option.id if custom_option else custom_option_id,
                "custom_option_value": custom_option_value_resolved,
                "custom_option_name": custom_option_name_resolved or (
                    furniture.custom_option_name if custom_option_value_resolved else ""
                ),
                "custom_option_price": custom_option_price,
                "total_price": item_price * quantity,
                "color_display": color_display,
                "color_hex": color_hex,
                "color_image": color_image,
                "cart_key": cart_key,
            }
        )

    return {
        "cart_items": cart_items,
        "total_price": total_price,
        "fabric_categories": FabricCategory.objects.all(),
    }
