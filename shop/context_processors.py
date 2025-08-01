from django.http import HttpRequest
from django.urls import resolve

from categories.models import Category
from furniture.models import Furniture
from sub_categories.models import SubCategory


def cart_count(request: HttpRequest) -> dict:
    cart = request.session.get("cart", {})
    # Handle both old format (just quantity) and new format (dict with quantity and size_variant)
    cart_count = 0
    for item_data in cart.values():
        if isinstance(item_data, dict):
            cart_count += item_data.get('quantity', 1)
        else:
            # Legacy format - just quantity
            cart_count += item_data
    return {"cart_count": cart_count}


def breadcrumbs(request):
    breadcrumbs = [{"name": "Головна", "url": "/"}]

    # Отримуємо поточний шлях і назву view
    current_path = request.path
    view_name = resolve(current_path).view_name

    # Додаємо breadcrumbs залежно від сторінки
    if view_name == "categories:categories_list":
        breadcrumbs.append({"name": "Каталог", "url": "/catalogue/"})
    elif view_name == "categories:category_detail":
        slug = resolve(current_path).kwargs.get("category_slug")
        try:
            category = Category.objects.get(slug=slug)
            breadcrumbs.append({"name": "Каталог", "url": "/catalogue/"})
            breadcrumbs.append(
                {"name": category.name, "url": f"/catalogue/{category.slug}/"}
            )
        except Category.DoesNotExist:
            pass
    elif view_name == "sub_categories:sub_categories_details":
        slug = resolve(current_path).kwargs.get("sub_categories_slug")
        try:
            sub_category = SubCategory.objects.get(slug=slug)
            breadcrumbs.append({"name": "Каталог", "url": "/catalogue/"})
            if sub_category.category:
                breadcrumbs.append(
                    {
                        "name": sub_category.category.name,
                        "url": f"/catalogue/{sub_category.category.slug}/",
                    }
                )
            breadcrumbs.append(
                {
                    "name": sub_category.name,
                    "url": f"/sub-categories/{sub_category.slug}/",
                }
            )
        except SubCategory.DoesNotExist:
            pass
    elif view_name == "sub_categories:sub_categories_list":
        breadcrumbs.append({"name": "Підкатегорії", "url": "/sub-categories/"})
    elif view_name == "furniture:furniture_detail":
        slug = resolve(current_path).kwargs.get("furniture_slug")
        try:
            furniture = Furniture.objects.get(slug=slug)
            breadcrumbs.append({"name": "Каталог", "url": "/catalogue/"})
            if furniture.sub_category and furniture.sub_category.category:
                breadcrumbs.append(
                    {
                        "name": furniture.sub_category.category.name,
                        "url": f"/catalogue/{furniture.sub_category.category.slug}/",
                    }
                )
                breadcrumbs.append(
                    {
                        "name": furniture.sub_category.name,
                        "url": f"/sub-categories/{furniture.sub_category.slug}/",
                    }
                )
            breadcrumbs.append(
                {"name": furniture.name, "url": f"/furniture/{furniture.slug}/"}
            )
        except Furniture.DoesNotExist:
            pass
    elif view_name == "shop:promotions":
        breadcrumbs.append({"name": "Акції", "url": "/promotions/"})
    elif view_name == "shop:where_to_buy":
        breadcrumbs.append({"name": "Де купити", "url": "/where-to-buy/"})
    elif view_name == "shop:contacts":
        breadcrumbs.append({"name": "Контакти", "url": "/contacts/"})
    elif view_name == "shop:view_cart":
        breadcrumbs.append({"name": "Кошик", "url": "/cart/"})
    elif view_name == "shop:order_history":
        breadcrumbs.append({"name": "Історія замовлень", "url": "/order-history/"})

    return {"breadcrumbs": breadcrumbs}
