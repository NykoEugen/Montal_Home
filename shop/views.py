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
from furniture.models import Furniture, FurnitureSizeVariant
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

        for furniture_id, item_data in cart.items():
            furniture = get_object_or_404(Furniture, id=int(furniture_id))
            
            # Handle both old format (just quantity) and new format (dict with quantity and size_variant)
            if isinstance(item_data, dict):
                quantity = item_data.get('quantity', 1)
                size_variant_id = item_data.get('size_variant_id')
                fabric_category_id = item_data.get('fabric_category_id')
            else:
                # Legacy format - just quantity
                quantity = item_data
                size_variant_id = None
                fabric_category_id = None
            
            # Calculate item price
            if size_variant_id:
                try:
                    size_variant = FurnitureSizeVariant.objects.get(id=size_variant_id)
                    item_price = float(size_variant.price)
                except FurnitureSizeVariant.DoesNotExist:
                    item_price = furniture.current_price
            else:
                item_price = furniture.current_price
            
            # Add fabric cost if fabric is selected
            if fabric_category_id:
                from fabric_category.models import FabricCategory
                try:
                    fabric_category = FabricCategory.objects.get(id=fabric_category_id)
                    fabric_cost = float(fabric_category.price) * float(furniture.fabric_value)
                    item_price += fabric_cost
                except FabricCategory.DoesNotExist:
                    pass
            
            total_price += item_price * quantity
            cart_items.append(
                {
                    "furniture": furniture,
                    "quantity": quantity,
                    "item_price": item_price,
                    "size_variant_id": size_variant_id,
                    "fabric_category_id": fabric_category_id,
                    "total_price": item_price * quantity,
                }
            )

        # Get all fabric categories for display in cart
        from fabric_category.models import FabricCategory
        fabric_categories = FabricCategory.objects.all()
        
        context.update(
            {
                "cart_items": cart_items,
                "total_price": total_price,
                "fabric_categories": fabric_categories,
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        """Redirect to home if cart is empty."""
        cart = request.session.get("cart", {})
        if not cart:
            return redirect('shop:home')
        return super().get(request, *args, **kwargs)


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
        size_variant_id = request.POST.get("size_variant_id")
        fabric_category_id = request.POST.get("fabric_category_id")

        if not furniture_id:
            return JsonResponse({"message": "Furniture ID is required"}, status=400)

        try:
            furniture = get_object_or_404(Furniture, id=furniture_id)
            cart = request.session.get("cart", {})

            if action == "add":
                # Create cart item data
                cart_item_data = {
                    'quantity': cart.get(furniture_id, {}).get('quantity', 0) + 1
                }
                
                # Add size variant if provided
                if size_variant_id:
                    cart_item_data['size_variant_id'] = size_variant_id
                
                # Add fabric category if provided
                if fabric_category_id:
                    cart_item_data['fabric_category_id'] = fabric_category_id
                
                cart[furniture_id] = cart_item_data
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

            # Calculate cart count
            cart_count = sum(
                item.get('quantity', 1) if isinstance(item, dict) else item 
                for item in cart.values()
            )

            return JsonResponse(
                {
                    "message": message,
                    "cart_count": cart_count,
                }
            )

        except Exception as e:
            return JsonResponse({"message": str(e)}, status=400)


@require_POST
def add_to_cart_from_detail(request: HttpRequest):
    """Add item to cart from furniture detail page with size variants and fabric."""
    furniture_id = request.POST.get("furniture_id")
    size_variant_id = request.POST.get("size_variant_id")
    fabric_category_id = request.POST.get("fabric_category_id")
    quantity = int(request.POST.get("quantity", 1))

    if not furniture_id:
        messages.error(request, "Furniture ID is required")
        return redirect('furniture:furniture_detail', furniture_slug=request.POST.get("furniture_slug"))

    try:
        furniture = get_object_or_404(Furniture, id=furniture_id)
        cart = request.session.get("cart", {})

        # Create cart item data
        cart_item_data = {
            'quantity': quantity
        }
        
        # Add size variant if provided
        if size_variant_id:
            cart_item_data['size_variant_id'] = size_variant_id
        
        # Add fabric category if provided
        if fabric_category_id:
            cart_item_data['fabric_category_id'] = fabric_category_id
        
        cart[furniture_id] = cart_item_data
        request.session["cart"] = cart
        request.session.modified = True

        messages.success(request, f"{furniture.name} додано до кошика!")
        return redirect('furniture:furniture_detail', furniture_slug=furniture.slug)

    except Exception as e:
        messages.error(request, str(e))
        return redirect('furniture:furniture_detail', furniture_slug=request.POST.get("furniture_slug"))


# Legacy function-based views for backward compatibility
@require_POST
def add_to_cart(request: HttpRequest) -> JsonResponse:
    """Add item to cart (legacy function-based view)."""
    request.POST = request.POST.copy()
    request.POST["action"] = "add"
    return CartActionView.as_view()(request)


@require_POST
def remove_from_cart(request: HttpRequest):
    """Remove item from cart and redirect appropriately."""
    furniture_id = request.POST.get("furniture_id")
    
    if not furniture_id:
        messages.error(request, "Furniture ID is required")
        return redirect('shop:view_cart')
    
    try:
        furniture = get_object_or_404(Furniture, id=furniture_id)
        cart = request.session.get("cart", {})
        
        if furniture_id in cart:
            del cart[furniture_id]
            request.session["cart"] = cart
            request.session.modified = True
            messages.success(request, "Товар видалено з кошика!")
        else:
            messages.error(request, "Товар не знайдено в кошику!")
        
        # If cart is empty, redirect to home
        if not cart:
            return redirect('shop:home')
        
        return redirect('shop:view_cart')
        
    except Exception as e:
        messages.error(request, str(e))
        return redirect('shop:view_cart')


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
