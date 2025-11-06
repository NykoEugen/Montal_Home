import re

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction

from furniture.models import Furniture, FurnitureCustomOption
from store.connection_utils import resilient_database_operation, save_form_draft, load_form_draft, clear_form_draft

from .forms import CheckoutForm
from .models import Order, OrderItem


def checkout(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            cart = request.session.get("cart", {})
            if not cart:
                messages.error(request, "Кошик порожній!", extra_tags="user")
                return redirect("shop:view_cart")

            try:
                # Use resilient database operation for order creation
                def create_order_operation():
                    # Prepare delivery data based on delivery type
                    delivery_type = form.cleaned_data["delivery_type"]
                    delivery_city = ""
                    delivery_branch = ""
                    delivery_address = ""

                    if delivery_type == "local":
                        delivery_city = "Доставка по місту"
                        delivery_address = form.cleaned_data["delivery_address"]
                    elif delivery_type == "nova_poshta":
                        delivery_city = form.cleaned_data["delivery_city_label"]
                        delivery_branch = form.cleaned_data["delivery_branch_name"]

                    with transaction.atomic():
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
                        return order

                order = resilient_database_operation(create_order_operation)
                
                # Clear any saved drafts after successful order creation
                clear_form_draft(request, 'checkout_form')
                
            except Exception as e:
                # Save form data as draft for retry
                form_data = form.cleaned_data
                save_form_draft(request, form_data, 'checkout_form')
                
                messages.error(
                    request,
                    "Помилка при створенні замовлення. Ваші дані збережено як чернетку. Спробуйте ще раз.",
                    extra_tags="user",
                )
                return render(request, "checkout/checkout.html", {"form": form})

            # Process cart items with resilient database operations
            for cart_key, item_data in cart.items():
                # Extract furniture_id from the cart key
                furniture_id = cart_key.split('_')[0]
                furniture: Furniture = get_object_or_404(
                    Furniture, id=int(furniture_id)
                )
                
                # Handle both old format (just quantity) and new format (dict with quantity and attributes)
                if isinstance(item_data, dict):
                    quantity = item_data.get('quantity', 1)
                    size_variant_id = item_data.get('size_variant_id')
                    fabric_category_id = item_data.get('fabric_category_id')
                    variant_image_id = item_data.get('variant_image_id')
                    custom_option_id = item_data.get('custom_option_id')
                    custom_option_value_session = item_data.get('custom_option_value')
                    custom_option_price_session = item_data.get('custom_option_price')
                else:
                    # Legacy format - just quantity
                    quantity = item_data
                    size_variant_id = None
                    fabric_category_id = None
                    variant_image_id = None
                    custom_option_id = None
                    custom_option_value_session = None
                    custom_option_price_session = None
                
                # Calculate price based on size variant and fabric
                size_variant = None
                if size_variant_id and size_variant_id != 'base':
                    try:
                        from furniture.models import FurnitureSizeVariant
                        size_variant = FurnitureSizeVariant.objects.get(id=size_variant_id)
                        price = float(size_variant.current_price)
                        size_variant_original_price = float(size_variant.price)
                        size_variant_is_promotional = size_variant.is_on_sale
                    except (FurnitureSizeVariant.DoesNotExist, ValueError):
                        price = float(furniture.current_price)
                        size_variant_original_price = None
                        size_variant_is_promotional = False
                else:
                    price = float(furniture.current_price)
                    size_variant_original_price = None
                    size_variant_is_promotional = False
                
                # Add fabric cost if fabric is selected
                if fabric_category_id:
                    try:
                        from fabric_category.models import FabricCategory
                        fabric_category = FabricCategory.objects.get(id=fabric_category_id)
                        fabric_cost = float(fabric_category.price) * float(furniture.fabric_value)
                        price += fabric_cost
                    except FabricCategory.DoesNotExist:
                        pass
                
                custom_option_obj = None
                custom_option_value_final = ""
                custom_option_name = furniture.custom_option_name or ""
                custom_option_price = 0.0

                if custom_option_id:
                    try:
                        option_id_int = int(custom_option_id)
                        custom_option_candidate = FurnitureCustomOption.objects.get(id=option_id_int)
                        if custom_option_candidate.furniture_id == furniture.id:
                            custom_option_obj = custom_option_candidate
                            custom_option_value_final = custom_option_candidate.value
                            custom_option_name = furniture.custom_option_name or ""
                        else:
                            custom_option_obj = None
                    except (ValueError, FurnitureCustomOption.DoesNotExist):
                        custom_option_obj = None

                if not custom_option_value_final and custom_option_value_session:
                    custom_option_value_final = str(custom_option_value_session)

                if custom_option_price_session not in (None, ""):
                    try:
                        custom_option_price = float(custom_option_price_session)
                    except (TypeError, ValueError):
                        custom_option_price = 0.0
                elif custom_option_obj:
                    try:
                        custom_option_price = float(custom_option_obj.price_delta)
                    except (TypeError, ValueError):
                        custom_option_price = 0.0

                if not custom_option_value_final:
                    custom_option_name = ""
                    custom_option_price = 0.0

                price += custom_option_price

                OrderItem.objects.create(
                    order=order,
                    furniture=furniture,
                    quantity=quantity,
                    price=price,
                    original_price=float(furniture.price),
                    is_promotional=furniture.is_promotional,
                    size_variant_original_price=size_variant_original_price,
                    size_variant_is_promotional=size_variant_is_promotional,
                    size_variant_id=None if size_variant_id == 'base' else size_variant_id,
                    fabric_category_id=fabric_category_id,
                    variant_image_id=variant_image_id,
                    custom_option=custom_option_obj,
                    custom_option_name=custom_option_name,
                    custom_option_value=custom_option_value_final,
                    custom_option_price=custom_option_price or None,
                )

            request.session["cart"] = {}
            messages.success(request, "Замовлення успішно оформлено!", extra_tags="user")
            return redirect("shop:home")
    else:
        # Load draft data if available
        draft_data = load_form_draft(request, 'checkout_form')
        if draft_data:
            form = CheckoutForm(initial=draft_data)
            messages.info(
                request,
                "Чернетка замовлення відновлена. Перевірте дані та збережіть.",
                extra_tags="user",
            )
        else:
            form = CheckoutForm()

    return render(request, "shop/checkout.html", {"form": form})


def order_history(request: HttpRequest) -> HttpResponse:
    phone_number = request.GET.get("phone_number", "").strip()
    orders_data = []
    if phone_number:
        if not re.match(r"^0[0-9]{9}$", phone_number):
            messages.error(
                request,
                "Неправильно введений номер телефону! Формат: 0XXXXXXXXX",
                extra_tags="user",
            )
        else:
            orders = (
                Order.objects.filter(customer_phone_number=phone_number)
                .order_by("-created_at")
                .prefetch_related("orderitem_set__furniture", "orderitem_set__custom_option")
            )
            if not orders.exists():
                messages.info(
                    request,
                    "Замовлення не знайдено для цього номера телефону.",
                    extra_tags="user",
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
