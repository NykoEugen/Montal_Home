from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST
from .models import Furniture, Category, Order, OrderItem
from typing import List, Dict, Any


def home(request) -> HttpResponse:
    categories: List[Category] = Category.objects.all()
    furniture: List[Furniture] = Furniture.objects.all()
    category_slug: str | None = request.GET.get('category')
    search_query: str | None = request.GET.get('q')

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        furniture = furniture.filter(category=category)
    if search_query:
        furniture = furniture.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    furniture_list = Furniture.objects.all()
    promotional_furniture = Furniture.objects.filter(is_promotional=True, promotional_price__isnull=False)
    context: Dict[str, Any] = {
        'categories': categories,
        'furniture': furniture,
        'search_query': search_query,
        'selected_category': category_slug,
        'furniture_list': furniture_list,
        'promotional_furniture': promotional_furniture,
    }
    return render(request, 'shop/home.html', context)


def furniture_detail(request, furniture_slug: str) -> HttpResponse:
    furniture: Furniture = get_object_or_404(Furniture, slug=furniture_slug)
    return render(request, 'shop/furniture_detail.html', {'furniture': furniture})


@require_POST
def add_to_cart(request, furniture_id: int) -> JsonResponse:
    furniture: Furniture = get_object_or_404(Furniture, id=furniture_id)
    cart: Dict[str, int] = request.session.get('cart', {})
    cart[str(furniture_id)] = cart.get(str(furniture_id), 0) + 1
    request.session['cart'] = cart
    return JsonResponse({
        'message': f'{furniture.name} додано до кошика!',
        'cart_count': sum(cart.values())
    })


@require_POST
def remove_from_cart(request, furniture_id: int) -> JsonResponse:
    cart: Dict[str, int] = request.session.get('cart', {})
    furniture_id_str: str = str(furniture_id)
    if furniture_id_str in cart:
        del cart[furniture_id_str]
        request.session['cart'] = cart
        return JsonResponse({
            'message': 'Товар видалено з кошика!',
            'cart_count': sum(cart.values())
        })
    return JsonResponse({'message': 'Товар не знайдено в кошику!'}, status=400)


def view_cart(request) -> HttpResponse:
    cart: Dict[str, int] = request.session.get('cart', {})
    cart_items: List[Dict[str, Any]] = []
    total_price: float = 0
    for furniture_id, quantity in cart.items():
        furniture: Furniture = get_object_or_404(Furniture, id=int(furniture_id))
        total_price += float(furniture.price) * quantity
        cart_items.append({'furniture': furniture, 'quantity': quantity})
    return render(request, 'shop/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price
    })


def checkout(request) -> HttpResponse:
    if request.method == 'POST':
        customer_name: str = request.POST.get('customer_name', '')
        customer_email: str = request.POST.get('customer_email', '')
        cart: Dict[str, int] = request.session.get('cart', {})
        if not cart:
            messages.error(request, "Кошик порожній!")
            return redirect('view_cart')

        order: Order = Order.objects.create(customer_name=customer_name, customer_email=customer_email)
        for furniture_id, quantity in cart.items():
            furniture: Furniture = get_object_or_404(Furniture, id=int(furniture_id))
            OrderItem.objects.create(order=order, furniture=furniture, quantity=quantity)

        request.session['cart'] = {}
        messages.success(request, "Замовлення успішно оформлено!")
        return redirect('home')

    return render(request, 'shop/checkout.html')


def order_history(request) -> HttpResponse:
    email: str | None = request.GET.get('email')
    orders: List[Order] = []
    if email:
        orders = Order.objects.filter(customer_email=email).order_by('-created_at')
    return render(request, 'shop/order_history.html', {'orders': orders, 'email': email})
