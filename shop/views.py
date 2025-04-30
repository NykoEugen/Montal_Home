from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Category, Furniture, Order, OrderItem


def home(request):
    categories = Category.objects.all()
    furniture = Furniture.objects.all()
    return render(
        request, "shop/home.html", {"categories": categories, "furniture": furniture}
    )


def furniture_detail(request, furniture_id):
    furniture = get_object_or_404(Furniture, id=furniture_id)
    return render(request, "shop/furniture_detail.html", {"furniture": furniture})


@require_POST
def add_to_cart(request, furniture_id):
    furniture = get_object_or_404(Furniture, id=furniture_id)
    cart = request.session.get("cart", {})
    cart[furniture_id] = cart.get(furniture_id, 0) + 1
    request.session["cart"] = cart
    return JsonResponse(
        {
            "message": f"{furniture.name} додано до кошика!",
            "cart_count": sum(cart.values()),
        }
    )


def view_cart(request):
    cart = request.session.get("cart", {})
    cart_items = []
    total_price = 0
    for furniture_id, quantity in cart.items():
        furniture = get_object_or_404(Furniture, id=furniture_id)
        total_price += furniture.price * quantity
        cart_items.append({"furniture": furniture, "quantity": quantity})
    return render(
        request,
        "shop/cart.html",
        {"cart_items": cart_items, "total_price": total_price},
    )


def checkout(request):
    if request.method == "POST":
        customer_name = request.POST.get("customer_name")
        customer_email = request.POST.get("customer_email")
        cart = request.session.get("cart", {})
        if not cart:
            messages.error(request, "Кошик порожній!")
            return redirect("view_cart")

        order = Order.objects.create(
            customer_name=customer_name, customer_email=customer_email
        )
        for furniture_id, quantity in cart.items():
            furniture = get_object_or_404(Furniture, id=furniture_id)
            OrderItem.objects.create(
                order=order, furniture=furniture, quantity=quantity
            )

        request.session["cart"] = {}
        messages.success(request, "Замовлення успішно оформлено!")
        return redirect("home")

    return render(request, "shop/checkout.html")
