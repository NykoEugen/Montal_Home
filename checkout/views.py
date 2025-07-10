import re

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from furniture.models import Furniture

from .forms import CheckoutForm
from .models import Order, OrderItem


def checkout(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            cart = request.session.get("cart", {})
            if not cart:
                messages.error(request, "Кошик порожній!")
                return redirect("shop:view_cart")

            # Prepare delivery data based on delivery type
            delivery_type = form.cleaned_data["delivery_type"]
            delivery_city = ""
            delivery_branch = ""
            delivery_address = ""
            
            if delivery_type == "local":
                delivery_city = "Локальна доставка"
                delivery_address = form.cleaned_data["delivery_address"]
            elif delivery_type == "nova_poshta":
                delivery_city = form.cleaned_data["delivery_city_label"]
                delivery_branch = form.cleaned_data["delivery_branch_name"]

            order = Order.objects.create(
                customer_name=form.cleaned_data["customer_name"],
                customer_last_name=form.cleaned_data["customer_last_name"],
                customer_phone_number=form.cleaned_data["customer_phone_number"],
                customer_email=form.cleaned_data["customer_email"],
                delivery_type=delivery_type,
                delivery_city=delivery_city,
                delivery_branch=delivery_branch,
                delivery_address=delivery_address,
                payment_type=form.cleaned_data["payment_type"],
            )

            for furniture_id, quantity in cart.items():
                furniture: Furniture = get_object_or_404(
                    Furniture, id=int(furniture_id)
                )
                price = (
                    furniture.promotional_price
                    if furniture.is_promotional and furniture.promotional_price
                    else furniture.price
                )
                OrderItem.objects.create(
                    order=order,
                    furniture=furniture,
                    quantity=quantity,
                    price=price,
                )

            request.session["cart"] = {}
            messages.success(request, "Замовлення успішно оформлено!")
            return redirect("shop:home")
    else:
        form = CheckoutForm()

    return render(request, "shop/checkout.html", {"form": form})


def order_history(request: HttpRequest) -> HttpResponse:
    phone_number = request.GET.get("phone_number", "").strip()
    orders_data = []
    if phone_number:
        if not re.match(r"^0[0-9]{9}$", phone_number):
            messages.error(
                request, "Неправильно введений номер телефону! Формат: 0XXXXXXXXX"
            )
        else:
            orders = (
                Order.objects.filter(customer_phone_number=phone_number)
                .order_by("-created_at")
                .prefetch_related("orderitem_set__furniture")
            )
            if not orders.exists():
                messages.info(
                    request, "Замовлення не знайдено для цього номера телефону."
                )
            else:
                for order in orders:
                    total_price = sum(
                        item.price * item.quantity for item in order.orderitem_set.all()
                    )
                    orders_data.append(
                        {
                            "order": order,
                            "items": order.orderitem_set.all(),
                            "total_price": float(total_price),
                        }
                    )
    return render(
        request,
        "shop/order_history.html",
        {"orders_data": orders_data, "phone_number": phone_number},
    )
