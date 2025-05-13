from django.core.paginator import Paginator
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
def add_to_cart(request) -> JsonResponse:
    furniture_id: str = request.POST.get('furniture_id')
    try:
        furniture: Furniture = get_object_or_404(Furniture, id=furniture_id)
        cart: Dict[str, int] = request.session.get('cart', {})
        cart[furniture_id] = cart.get(furniture_id, 0) + 1
        request.session['cart'] = cart
        request.session.modified = True
        return JsonResponse({
            'message': f'{furniture.name} додано до кошика!',
            'cart_count': sum(cart.values())
        })
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=400)


@require_POST
def remove_from_cart(request) -> JsonResponse:
    furniture_id: str = request.POST.get('furniture_id')
    try:
        cart: Dict[str, int] = request.session.get('cart', {})
        if furniture_id in cart:
            del cart[furniture_id]
            request.session['cart'] = cart
            request.session.modified = True
            return JsonResponse({
                'message': 'Товар видалено з кошика!',
                'cart_count': sum(cart.values())
            })
        return JsonResponse({'message': 'Товар не знайдено в кошику!'}, status=400)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=400)

def view_cart(request) -> HttpResponse:
    cart = request.session.get('cart', {})
    cart_items = []
    total_price: float = 0
    for furniture_id, quantity in cart.items():
        furniture: Furniture = get_object_or_404(Furniture, id=int(furniture_id))
        item_price = float(
            furniture.promotional_price if furniture.is_promotional and furniture.promotional_price else furniture.price)
        total_price += item_price * quantity
        cart_items.append({
            'furniture': furniture,
            'quantity': quantity,
            'item_price': item_price,
        })
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
            return redirect('shop:view_cart')

        order: Order = Order.objects.create(customer_name=customer_name, customer_email=customer_email)
        for furniture_id, quantity in cart.items():
            furniture: Furniture = get_object_or_404(Furniture, id=int(furniture_id))
            price = furniture.promotional_price if furniture.is_promotional and furniture.promotional_price else furniture.price
            OrderItem.objects.create(
                order=order,
                furniture=furniture,
                quantity=quantity,
                price=price,
            )

        request.session['cart'] = {}
        messages.success(request, "Замовлення успішно оформлено!")
        return redirect('shop:home')

    return render(request, 'shop/checkout.html')


def order_history(request) -> HttpResponse:
    email = request.GET.get('email')
    orders_data = []
    if email:
        orders = Order.objects.filter(customer_email=email).order_by('-created_at').prefetch_related('orderitem_set__furniture')
        for order in orders:
            total_price = sum(item.price * item.quantity for item in order.orderitem_set.all())
            orders_data.append({
                'order': order,
                'items': order.orderitem_set.all(),
                'total_price': float(total_price)
            })
        return render(request, 'shop/order_history.html', {
            'orders_data': orders_data,
            'email': email
        })
    return render(request, 'shop/order_history.html')

def catalog(request) -> HttpResponse:
    categories: List[Category] = Category.objects.all()
    context: Dict[str, Any] = {'categories': categories}
    return render(request, 'shop/catalog.html', context)

def category_detail(request, category_slug: str) -> HttpResponse:
    category = get_object_or_404(Category, slug=category_slug)
    furniture: List[Furniture] = Furniture.objects.filter(category=category)
    paginator = Paginator(furniture, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context: Dict[str, Any] = {'category': category, 'page_obj': page_obj}
    return render(request, 'shop/category_detail.html', context)

def promotions(request) -> HttpResponse:
    promotional_furniture: List[Furniture] = Furniture.objects.filter(is_promotional=True, promotional_price__isnull=False)
    paginator = Paginator(promotional_furniture, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context: Dict[str, Any] = {'page_obj': page_obj}
    return render(request, 'shop/promotions.html', context)

def where_to_buy(request) -> HttpResponse:
    return render(request, 'shop/where_to_buy.html')

def contacts(request) -> HttpResponse:
    return render(request, 'shop/contacts.html')
