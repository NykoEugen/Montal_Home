from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import DetailView, ListView, TemplateView
from django.urls import reverse

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
                    is_promotional=True, 
                    promotional_price__isnull=False
                ).order_by('-created_at')[:6],
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

        for cart_key, item_data in cart.items():
            # Extract furniture_id from the cart key
            furniture_id = cart_key.split('_')[0]
            furniture = get_object_or_404(Furniture, id=int(furniture_id))
            
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
            
            # Calculate item price and get size variant
            size_variant = None
            if size_variant_id and size_variant_id != 'base':
                try:
                    size_variant = FurnitureSizeVariant.objects.get(id=size_variant_id)
                    item_price = float(size_variant.current_price)
                except (FurnitureSizeVariant.DoesNotExist, ValueError):
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
                    "size_variant": size_variant,  # Add size variant object for template
                    "fabric_category_id": fabric_category_id,
                    "variant_image_id": variant_image_id,
                    "total_price": item_price * quantity,
                    "cart_key": cart_key,  # Add cart key for removal functionality
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
        """Get only active promotional furniture."""
        from django.db import models
        return Furniture.objects.filter(
            models.Q(
                is_promotional=True, 
                promotional_price__isnull=False
            ) & (
                models.Q(sale_end_date__isnull=True) | models.Q(sale_end_date__gt=timezone.now())
            ) | models.Q(
                size_variants__is_promotional=True,
                size_variants__promotional_price__isnull=False
            ) & (
                models.Q(size_variants__sale_end_date__isnull=True) | models.Q(size_variants__sale_end_date__gt=timezone.now())
            )
        ).distinct()


class WhereToBuyView(TemplateView):
    """Where to buy page."""

    template_name = "shop/where_to_buy.html"


class ContactsView(TemplateView):
    """Contacts page."""

    template_name = "shop/contacts.html"


class WarrantyView(TemplateView):
    """Warranty page."""

    template_name = "shop/warranty.html"


class DeliveryPaymentView(TemplateView):
    """Delivery and payment page."""

    template_name = "shop/delivery_payment.html"


class OfferView(TemplateView):
    """Offer page."""

    template_name = "shop/offer.html"


class SearchView(ListView):
    """Search furniture by name."""
    
    model = Furniture
    template_name = "shop/search_results.html"
    context_object_name = "furniture"
    paginate_by = ITEMS_PER_PAGE

    def get_queryset(self):
        """Filter furniture based on search query."""
        queryset = Furniture.objects.select_related("sub_category__category").all()
        search_query = self.request.GET.get("q", "").strip()
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(article_code__icontains=search_query)
            )
        else:
            queryset = queryset.none()  # Return empty queryset if no search query
            
        return queryset

    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        context.update({
            "search_query": self.request.GET.get("q", "").strip(),
            "categories": Category.objects.all(),
        })
        return context


@method_decorator(csrf_exempt, name="dispatch")
class CartActionView(View):
    """Handle cart actions (add/remove items)."""

    def post(self, request: HttpRequest) -> JsonResponse:
        """Handle POST requests for cart actions."""
        action = request.POST.get("action")
        furniture_id = request.POST.get("furniture_id")
        size_variant_id = request.POST.get("size_variant_id")
        fabric_category_id = request.POST.get("fabric_category_id")
        variant_image_id = request.POST.get("variant_image_id")

        if not furniture_id:
            return JsonResponse({"message": "Furniture ID is required"}, status=400)

        try:
            furniture = get_object_or_404(Furniture, id=furniture_id)
            cart = request.session.get("cart", {})

            if action == "add":
                # Create a unique key for this cart item that includes variant information
                cart_key_parts = [furniture_id]
                if size_variant_id:
                    cart_key_parts.append(f"size_{size_variant_id}")
                if fabric_category_id:
                    cart_key_parts.append(f"fabric_{fabric_category_id}")
                if variant_image_id:
                    cart_key_parts.append(f"variant_{variant_image_id}")
                
                cart_key = "_".join(cart_key_parts)
                
                # Create cart item data
                cart_item_data = {
                    'quantity': cart.get(cart_key, {}).get('quantity', 0) + 1
                }
                
                # Add size variant if provided
                if size_variant_id:
                    cart_item_data['size_variant_id'] = size_variant_id
                
                # Add fabric category if provided
                if fabric_category_id:
                    cart_item_data['fabric_category_id'] = fabric_category_id
                
                # Add variant image if provided
                if variant_image_id:
                    cart_item_data['variant_image_id'] = variant_image_id
                
                cart[cart_key] = cart_item_data
                message = f"{furniture.name} додано до кошика!"
            elif action == "remove":
                cart_key = request.POST.get("cart_key")
                if cart_key and cart_key in cart:
                    del cart[cart_key]
                    message = "Товар видалено з кошика!"
                elif furniture_id:
                    # Fallback to furniture_id for backward compatibility
                    keys_to_remove = [key for key in cart.keys() if key.startswith(f"{furniture_id}_") or key == furniture_id]
                    if keys_to_remove:
                        for key in keys_to_remove:
                            del cart[key]
                        message = "Товар видалено з кошика!"
                    else:
                        return JsonResponse(
                            {"message": "Товар не знайдено в кошику!"}, status=400
                        )
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
    variant_image_id = request.POST.get("variant_image_id")
    quantity = int(request.POST.get("quantity", 1))
    

    if not furniture_id:
        messages.error(request, "Furniture ID is required")
        return redirect('furniture:furniture_detail', furniture_slug=request.POST.get("furniture_slug"))

    try:
        furniture = get_object_or_404(Furniture, id=furniture_id)
        cart = request.session.get("cart", {})

        # Create a unique key for this cart item that includes variant information
        cart_key_parts = [furniture_id]
        if size_variant_id:
            cart_key_parts.append(f"size_{size_variant_id}")
        if fabric_category_id:
            cart_key_parts.append(f"fabric_{fabric_category_id}")
        if variant_image_id:
            cart_key_parts.append(f"variant_{variant_image_id}")
        
        cart_key = "_".join(cart_key_parts)

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
        
        # Add variant image if provided
        if variant_image_id:
            cart_item_data['variant_image_id'] = variant_image_id
        
        cart[cart_key] = cart_item_data
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
    cart_key = request.POST.get("cart_key")
    furniture_id = request.POST.get("furniture_id")  # Keep for backward compatibility
    
    if not cart_key and not furniture_id:
        messages.error(request, "Cart key or Furniture ID is required")
        return redirect('shop:view_cart')
    
    try:
        cart = request.session.get("cart", {})
        
        # If cart_key is provided, use it directly
        if cart_key and cart_key in cart:
            del cart[cart_key]
            request.session["cart"] = cart
            request.session.modified = True
            messages.success(request, "Товар видалено з кошика!")
        # Fallback to furniture_id for backward compatibility
        elif furniture_id:
            # Find and remove items with this furniture_id
            keys_to_remove = [key for key in cart.keys() if key.startswith(f"{furniture_id}_") or key == furniture_id]
            if keys_to_remove:
                for key in keys_to_remove:
                    del cart[key]
                request.session["cart"] = cart
                request.session.modified = True
                messages.success(request, "Товар видалено з кошика!")
            else:
                messages.error(request, "Товар не знайдено в кошику!")
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


def warranty(request: HttpRequest) -> HttpResponse:
    """Legacy warranty view for backward compatibility."""
    return WarrantyView.as_view()(request)


def delivery_payment(request: HttpRequest) -> HttpResponse:
    """Legacy delivery and payment view for backward compatibility."""
    return DeliveryPaymentView.as_view()(request)


def offer(request: HttpRequest) -> HttpResponse:
    """Legacy offer view for backward compatibility."""
    return OfferView.as_view()(request)


@require_http_methods(["GET"])
def search_suggestions(request):
    """Return search suggestions for AJAX dropdown."""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:  # Only search if query is at least 2 characters
        return JsonResponse({'suggestions': []})
    
    # Search in furniture names, descriptions, and article codes
    furniture_results = Furniture.objects.filter(
        Q(name__icontains=query) | 
        Q(description__icontains=query) |
        Q(article_code__icontains=query)
    ).select_related('sub_category__category')[:10]  # Limit to 10 results
    
    suggestions = []
    for furniture in furniture_results:
        suggestions.append({
            'id': furniture.id,
            'name': furniture.name,
            'article_code': furniture.article_code,
            'category': f"{furniture.sub_category.category.name} → {furniture.sub_category.name}",
            'price': str(furniture.current_price),
            'image_url': furniture.image.url if furniture.image else None,
            'url': reverse('furniture:furniture_detail', kwargs={'furniture_slug': furniture.slug}),
            'is_promotional': furniture.is_promotional,
            'promotional_price': str(furniture.promotional_price) if furniture.promotional_price else None
        })
    
    return JsonResponse({'suggestions': suggestions})
