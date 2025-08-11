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

            for furniture_id, item_data in cart.items():
                furniture: Furniture = get_object_or_404(
                    Furniture, id=int(furniture_id)
                )
                
                # Handle both old format (just quantity) and new format (dict with quantity and size_variant)
                if isinstance(item_data, dict):
                    quantity = item_data.get('quantity', 1)
                    size_variant_id = item_data.get('size_variant_id')
                    fabric_category_id = item_data.get('fabric_category_id')
                    variant_image_id = item_data.get('variant_image_id')
                else:
                    # Legacy format - just quantity
                    quantity = item_data
                    size_variant_id = None
                    fabric_category_id = None
                    variant_image_id = None
                
                # Calculate price based on size variant and fabric
                if size_variant_id:
                    try:
                        from furniture.models import FurnitureSizeVariant
                        size_variant = FurnitureSizeVariant.objects.get(id=size_variant_id)
                        price = float(size_variant.price)
                    except FurnitureSizeVariant.DoesNotExist:
                        price = float(
                            furniture.promotional_price
                            if furniture.is_promotional and furniture.promotional_price
                            else furniture.price
                        )
                else:
                    price = float(
                        furniture.promotional_price
                        if furniture.is_promotional and furniture.promotional_price
                        else furniture.price
                    )
                
                # Add fabric cost if fabric is selected
                if fabric_category_id:
                    try:
                        from fabric_category.models import FabricCategory
                        fabric_category = FabricCategory.objects.get(id=fabric_category_id)
                        fabric_cost = float(fabric_category.price) * float(furniture.fabric_value)
                        price += fabric_cost
                    except FabricCategory.DoesNotExist:
                        pass
                
                OrderItem.objects.create(
                    order=order,
                    furniture=furniture,
                    quantity=quantity,
                    price=price,
                    size_variant_id=size_variant_id,
                    fabric_category_id=fabric_category_id,
                    variant_image_id=variant_image_id,
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
    # Get all fabric categories for display in order history
    from fabric_category.models import FabricCategory
    fabric_categories = FabricCategory.objects.all()
    
    return render(
        request,
        "shop/order_history.html",
        {"orders_data": orders_data, "phone_number": phone_number, "fabric_categories": fabric_categories},
    )
