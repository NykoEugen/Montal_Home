from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView

from categories.models import Category
from delivery.views import search_city
from furniture.models import Furniture
from store.settings import ITEMS_PER_PAGE


class HomeView(ListView):
    """Home page view with furniture listing and filtering."""

    model = Furniture
    template_name = "shop/home.html"
    context_object_name = "furniture"
    paginate_by = ITEMS_PER_PAGE

    def get_queryset(self):
        """Filter furniture based on category and search query."""
        queryset = Furniture.objects.select_related("sub_category__category").all()

        category_slug = self.request.GET.get("category")
        search_query = self.request.GET.get("q")

        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(sub_category__category=category)

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | Q(description__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "categories": Category.objects.all(),
                "search_query": self.request.GET.get("q"),
                "selected_category": self.request.GET.get("category"),
                "promotional_furniture": Furniture.objects.filter(
                    is_promotional=True, promotional_price__isnull=False
                )[
                    :6
                ],  # Limit to 6 promotional items
            }
        )
        return context


class CartView(TemplateView):
    """Shopping cart view."""

    template_name = "shop/cart.html"

    def get_context_data(self, **kwargs):
        """Calculate cart items and total price."""
        context = super().get_context_data(**kwargs)
        cart = self.request.session.get("cart", {})
        cart_items = []
        total_price = 0.0

        for furniture_id, quantity in cart.items():
            furniture = get_object_or_404(Furniture, id=int(furniture_id))
            item_price = furniture.current_price
            total_price += item_price * quantity
            cart_items.append(
                {
                    "furniture": furniture,
                    "quantity": quantity,
                    "item_price": item_price,
                }
            )

        context.update(
            {
                "cart_items": cart_items,
                "total_price": total_price,
            }
        )
        return context


class PromotionsView(ListView):
    """Promotional furniture listing."""

    model = Furniture
    template_name = "shop/promotions.html"
    context_object_name = "page_obj"
    paginate_by = ITEMS_PER_PAGE

    def get_queryset(self):
        """Get only promotional furniture."""
        return Furniture.objects.filter(
            is_promotional=True, promotional_price__isnull=False
        )


class WhereToBuyView(TemplateView):
    """Where to buy page."""

    template_name = "shop/where_to_buy.html"


class ContactsView(TemplateView):
    """Contacts page."""

    template_name = "shop/contacts.html"


@method_decorator(csrf_exempt, name="dispatch")
class CartActionView(View):
    """Handle cart actions (add/remove items)."""

    def post(self, request: HttpRequest) -> JsonResponse:
        """Handle POST requests for cart actions."""
        action = request.POST.get("action")
        furniture_id = request.POST.get("furniture_id")

        if not furniture_id:
            return JsonResponse({"message": "Furniture ID is required"}, status=400)

        try:
            furniture = get_object_or_404(Furniture, id=furniture_id)
            cart = request.session.get("cart", {})

            if action == "add":
                cart[furniture_id] = cart.get(furniture_id, 0) + 1
                message = f"{furniture.name} додано до кошика!"
            elif action == "remove":
                if furniture_id in cart:
                    del cart[furniture_id]
                    message = "Товар видалено з кошика!"
                else:
                    return JsonResponse(
                        {"message": "Товар не знайдено в кошику!"}, status=400
                    )
            else:
                return JsonResponse({"message": "Invalid action"}, status=400)

            request.session["cart"] = cart
            request.session.modified = True

            return JsonResponse(
                {
                    "message": message,
                    "cart_count": sum(cart.values()),
                }
            )

        except Exception as e:
            return JsonResponse({"message": str(e)}, status=400)


# Legacy function-based views for backward compatibility
@require_POST
def add_to_cart(request: HttpRequest) -> JsonResponse:
    """Add item to cart (legacy function-based view)."""
    request.POST = request.POST.copy()
    request.POST["action"] = "add"
    return CartActionView.as_view()(request)


@require_POST
def remove_from_cart(request: HttpRequest) -> JsonResponse:
    """Remove item from cart (legacy function-based view)."""
    request.POST = request.POST.copy()
    request.POST["action"] = "remove"
    return CartActionView.as_view()(request)


def home(request: HttpRequest) -> HttpResponse:
    """Legacy home view for backward compatibility."""
    return HomeView.as_view()(request)


def view_cart(request: HttpRequest) -> HttpResponse:
    """Legacy cart view for backward compatibility."""
    return CartView.as_view()(request)


def promotions(request: HttpRequest) -> HttpResponse:
    """Legacy promotions view for backward compatibility."""
    return PromotionsView.as_view()(request)


def where_to_buy(request: HttpRequest) -> HttpResponse:
    """Legacy where to buy view for backward compatibility."""
    return WhereToBuyView.as_view()(request)


def contacts(request: HttpRequest) -> HttpResponse:
    """Legacy contacts view for backward compatibility."""
    return ContactsView.as_view()(request)
