from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from categories.models import Category
from delivery.views import search_city
from furniture.models import Furniture


def home(request: HttpRequest) -> HttpResponse:
    categories = Category.objects.all()
    furniture = Furniture.objects.all()
    category_slug = request.GET.get("category")
    search_query = request.GET.get("q")

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        furniture = furniture.filter(category=category)
    if search_query:
        furniture = furniture.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    furniture_list = Furniture.objects.all()
    promotional_furniture = Furniture.objects.filter(
        is_promotional=True, promotional_price__isnull=False
    )
    context = {
        "categories": categories,
        "furniture": furniture,
        "search_query": search_query,
        "selected_category": category_slug,
        "furniture_list": furniture_list,
        "promotional_furniture": promotional_furniture,
    }
    return render(request, "shop/home.html", context)


@require_POST
def add_to_cart(request: HttpRequest) -> JsonResponse:
    furniture_id: str = request.POST.get("furniture_id")
    try:
        furniture: Furniture = get_object_or_404(Furniture, id=furniture_id)
        cart = request.session.get("cart", {})
        cart[furniture_id] = cart.get(furniture_id, 0) + 1
        request.session["cart"] = cart
        request.session.modified = True
        return JsonResponse(
            {
                "message": f"{furniture.name} додано до кошика!",
                "cart_count": sum(cart.values()),
            }
        )
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=400)


@require_POST
def remove_from_cart(request: HttpRequest) -> JsonResponse:
    furniture_id: str = request.POST.get("furniture_id")
    try:
        cart = request.session.get("cart", {})
        if furniture_id in cart:
            del cart[furniture_id]
            request.session["cart"] = cart
            request.session.modified = True
            return JsonResponse(
                {
                    "message": "Товар видалено з кошика!",
                    "cart_count": sum(cart.values()),
                }
            )
        return JsonResponse({"message": "Товар не знайдено в кошику!"}, status=400)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=400)


def view_cart(request: HttpRequest) -> HttpResponse:
    cart = request.session.get("cart", {})
    cart_items = []
    total_price: float = 0
    for furniture_id, quantity in cart.items():
        furniture = get_object_or_404(Furniture, id=int(furniture_id))
        item_price = float(
            furniture.promotional_price
            if furniture.is_promotional and furniture.promotional_price
            else furniture.price
        )
        total_price += item_price * quantity
        cart_items.append(
            {
                "furniture": furniture,
                "quantity": quantity,
                "item_price": item_price,
            }
        )
    return render(
        request,
        "shop/cart.html",
        {"cart_items": cart_items, "total_price": total_price},
    )


def promotions(request: HttpRequest) -> HttpResponse:
    promotional_furniture = Furniture.objects.filter(
        is_promotional=True, promotional_price__isnull=False
    )
    paginator = Paginator(promotional_furniture, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"page_obj": page_obj}
    return render(request, "shop/promotions.html", context)


def where_to_buy(request: HttpRequest) -> HttpResponse:
    return render(request, "shop/where_to_buy.html")


def contacts(request: HttpRequest) -> HttpResponse:
    return render(request, "shop/contacts.html")
