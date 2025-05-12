from typing import Any, Dict, List

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Category, Furniture, Order, OrderItem


def home(request: HttpRequest) -> HttpResponse:
    categories = Category.objects.all()
    furniture = Furniture.objects.all()
    category_id: str | None = request.GET.get("category")
    search_query: str | None = request.GET.get("q")

    if category_id:
        furniture = furniture.filter(category_id=category_id)
    if search_query:
        furniture = furniture.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    return render(
        request,
        "shop/home.html",
        {
            "categories": categories,
            "furniture": furniture,
            "search_query": search_query,
        },
    )


def furniture_detail(request: HttpRequest, furniture_id: int) -> HttpResponse:
    furniture: Furniture = get_object_or_404(Furniture, id=furniture_id)
    return render(request, "shop/furniture_detail.html", {"furniture": furniture})


@require_POST
def add_to_cart(request: HttpRequest, furniture_id: int) -> JsonResponse:
    furniture: Furniture = get_object_or_404(Furniture, id=furniture_id)
    cart: Dict[str, int] = request.session.get("cart", {})
    cart[str(furniture_id)] = cart.get(str(furniture_id), 0) + 1
    request.session["cart"] = cart
    return JsonResponse(
        {
            "message": f"{furniture.name} додано до кошика!",
            "cart_count": sum(cart.values()),
        }
    )


@require_POST
def remove_from_cart(request: HttpRequest, furniture_id: int) -> JsonResponse:
    cart: Dict[str, int] = request.session.get("cart", {})
    furniture_id_str: str = str(furniture_id)
    if furniture_id_str in cart:
        del cart[furniture_id_str]
        request.session["cart"] = cart
        return JsonResponse(
            {"message": "Товар видалено з кошика!", "cart_count": sum(cart.values())}
        )
    return JsonResponse({"message": "Товар не знайдено в кошику!"}, status=400)


def view_cart(request: HttpRequest) -> HttpResponse:
    cart: Dict[str, int] = request.session.get("cart", {})
    cart_items: List[Dict[str, Any]] = []
    total_price: float = 0
    for furniture_id, quantity in cart.items():
        furniture: Furniture = get_object_or_404(Furniture, id=int(furniture_id))
        total_price += float(furniture.price) * quantity
        cart_items.append({"furniture": furniture, "quantity": quantity})
    return render(
        request,
        "shop/cart.html",
        {"cart_items": cart_items, "total_price": total_price},
    )


def checkout(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        customer_name: str = request.POST.get("customer_name", "")
        customer_email: str = request.POST.get("customer_email", "")
        cart: Dict[str, int] = request.session.get("cart", {})
        if not cart:
            messages.error(request, "Кошик порожній!")
            return redirect("view_cart")

        order: Order = Order.objects.create(
            customer_name=customer_name, customer_email=customer_email
        )
        for furniture_id, quantity in cart.items():
            furniture: Furniture = get_object_or_404(Furniture, id=int(furniture_id))
            OrderItem.objects.create(
                order=order, furniture=furniture, quantity=quantity
            )

        request.session["cart"] = {}
        messages.success(request, "Замовлення успішно оформлено!")
        return redirect("home")

    return render(request, "shop/checkout.html")


def order_history(request: HttpRequest) -> HttpResponse:
    email: str | None = request.GET.get("email")
    orders: List[Order] = []
    if email:
        orders = Order.objects.filter(customer_email=email).order_by("-created_at")
    return render(
        request, "shop/order_history.html", {"orders": orders, "email": email}
    )
