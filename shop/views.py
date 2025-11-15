import random
import json
from collections import defaultdict

from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import DetailView, ListView, TemplateView
from django.urls import reverse
from django.templatetags.static import static

from categories.models import Category
from delivery.views import search_city
from fabric_category.models import FabricCategory, FabricColor
from furniture.models import Furniture, FurnitureCustomOption, FurnitureSizeVariant
from store.settings import ITEMS_PER_PAGE

PROMOTIONAL_CACHE_TIMEOUT = 180


def fetch_active_promotional_furniture():
    """Return queryset with all active promotional furniture records."""
    cache_key = "promotional_furniture_ids"
    promotional_ids = cache.get(cache_key)

    if promotional_ids is None:
        now = timezone.now()
        promotional_ids = list(
            Furniture.objects.filter(
                (
                    Q(is_promotional=True, promotional_price__isnull=False)
                    & (Q(sale_end_date__isnull=True) | Q(sale_end_date__gt=now))
                )
                |
                (
                    Q(size_variants__is_promotional=True, size_variants__promotional_price__isnull=False)
                    & (
                        Q(size_variants__sale_end_date__isnull=True)
                        | Q(size_variants__sale_end_date__gt=now)
                    )
                )
            )
            .order_by("-updated_at")
            .distinct()
            .values_list("id", flat=True)
        )
        cache.set(cache_key, promotional_ids, PROMOTIONAL_CACHE_TIMEOUT)

    if not promotional_ids:
        return Furniture.objects.none()

    order_expression = models.Case(
        *[
            models.When(pk=pk, then=pos)
            for pos, pk in enumerate(promotional_ids)
        ],
        output_field=models.IntegerField(),
    )

    return (
        Furniture.objects.filter(id__in=promotional_ids)
        .select_related("sub_category__category")
        .prefetch_related("size_variants")
        .annotate(_promotional_order=order_expression)
        .order_by("_promotional_order")
    )


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
                # Show only categories that have subcategories with at least one furniture item
                "categories": Category.objects.filter(
                    sub_categories__furniture__isnull=False
                ).distinct(),
                "search_query": self.request.GET.get("q"),
                "selected_category": self.request.GET.get("category"),
                "promotional_furniture": self._get_promotional_furniture(),
                "meta_title": "Montal Home — інтернет-магазин меблів та декору",
                "meta_description": (
                    "Обирайте стильні та якісні меблі для дому й офісу у Montal Home. "
                    "Акційні пропозиції, зручні фільтри та доставка по всій Україні."
                ),
                "meta_keywords": "меблі Montal, купити меблі онлайн, українські меблі, декор для дому",
                "og_type": "website",
            }
        )
        return context

    def _get_promotional_furniture(self) -> list[Furniture]:
        """Return promotional items shuffled to interleave categories."""
        promotional_items = list(fetch_active_promotional_furniture())
        if not promotional_items:
            return promotional_items

        items_by_category: dict[object, list[Furniture]] = defaultdict(list)
        uncategorised_key = object()

        for item in promotional_items:
            category = getattr(getattr(item, "sub_category", None), "category", None)
            category_key = category.id if category else uncategorised_key
            items_by_category[category_key].append(item)

        # Shuffle within each category to avoid predictable ordering
        for item_list in items_by_category.values():
            random.shuffle(item_list)

        shuffled_items: list[Furniture] = []
        while items_by_category:
            category_keys = list(items_by_category.keys())
            random.shuffle(category_keys)

            for key in category_keys:
                item_list = items_by_category.get(key)
                if not item_list:
                    items_by_category.pop(key, None)
                    continue

                shuffled_items.append(item_list.pop())
                if not item_list:
                    items_by_category.pop(key, None)

        return shuffled_items


def _summarize(text: str, length: int = 160) -> str:
    """Trim HTML-heavy text down to a sensible length for meta descriptions."""
    clean_text = strip_tags(text or "")
    return Truncator(clean_text).chars(length, truncate="…")


class CartView(TemplateView):
    """Shopping cart view."""

    template_name = "shop/cart.html"

    def get_context_data(self, **kwargs):
        """Calculate cart items and total price."""
        context = super().get_context_data(**kwargs)
        cart = self.request.session.get("cart", {})
        cart_items = []
        total_price = 0.0

        if not cart:
            context.update(
                {
                    "cart_items": [],
                    "total_price": 0.0,
                    "fabric_categories": FabricCategory.objects.all(),
                    "meta_title": "Кошик — Montal Home",
                    "meta_description": (
                        "Перегляньте товари у кошику Montal Home та завершіть оформлення замовлення. "
                        "Зручна оплата, доставка по Україні."
                    ),
                    "meta_keywords": "кошик, замовлення меблів, купити меблі онлайн",
                }
            )
            return context

        # Collect identifiers once to reduce N+1 DB queries.
        furniture_ids: set[int] = set()
        size_variant_ids: set[int] = set()
        fabric_category_ids: set[int] = set()
        color_ids: set[int] = set()

        for cart_key, item_data in cart.items():
            try:
                furniture_ids.add(int(cart_key.split("_")[0]))
            except (TypeError, ValueError):
                continue

            if isinstance(item_data, dict):
                size_variant_id = item_data.get("size_variant_id")
                fabric_category_id = item_data.get("fabric_category_id")
                color_id = item_data.get("color_id")

                if size_variant_id not in (None, "", "base"):
                    try:
                        size_variant_ids.add(int(size_variant_id))
                    except (TypeError, ValueError):
                        pass

                if fabric_category_id:
                    try:
                        fabric_category_ids.add(int(fabric_category_id))
                    except (TypeError, ValueError):
                        pass

                if color_id:
                    try:
                        color_ids.add(int(color_id))
                    except (TypeError, ValueError):
                        pass

        furniture_map = {
            obj.id: obj
            for obj in Furniture.objects.filter(id__in=furniture_ids).prefetch_related("custom_options")
        }
        size_variant_map = FurnitureSizeVariant.objects.in_bulk(size_variant_ids)
        fabric_category_map = FabricCategory.objects.in_bulk(fabric_category_ids)
        fabric_color_map = {
            color.id: color
            for color in FabricColor.objects.select_related("palette").filter(id__in=color_ids)
        }

        for cart_key, item_data in cart.items():
            # Extract furniture_id from the cart key
            try:
                furniture_id = int(cart_key.split('_')[0])
            except (TypeError, ValueError):
                continue
            furniture = furniture_map.get(furniture_id)
            if not furniture:
                continue
            
            # Handle both old format (just quantity) and new format (dict with quantity and size_variant)
            if isinstance(item_data, dict):
                quantity = item_data.get('quantity', 1)
                size_variant_id = item_data.get('size_variant_id')
                fabric_category_id = item_data.get('fabric_category_id')
                variant_image_id = item_data.get('variant_image_id')
                custom_option_id = item_data.get('custom_option_id')
                custom_option_value = item_data.get('custom_option_value')
                custom_option_price_raw = item_data.get('custom_option_price')
                custom_option_name_stored = item_data.get('custom_option_name')
                color_id = item_data.get('color_id')
                color_name = item_data.get('color_name')
                color_palette_name = item_data.get('color_palette_name')
                color_hex = item_data.get('color_hex')
                color_image = item_data.get('color_image')
            else:
                # Legacy format - just quantity
                quantity = item_data
                size_variant_id = None
                fabric_category_id = None
                variant_image_id = None
                custom_option_id = None
                custom_option_value = None
                custom_option_price_raw = None
                custom_option_name_stored = None
                color_id = None
                color_name = ""
                color_palette_name = ""
                color_hex = ""
                color_image = ""
            
            # Calculate item price and get size variant
            size_variant = None
            if size_variant_id and size_variant_id != 'base':
                try:
                    size_variant = size_variant_map.get(int(size_variant_id))
                    if size_variant:
                        item_price = float(size_variant.current_price)
                    else:
                        item_price = float(furniture.current_price)
                except (TypeError, ValueError):
                    item_price = float(furniture.current_price)
            else:
                item_price = float(furniture.current_price)
            
            # Add fabric cost if fabric is selected
            if fabric_category_id:
                fabric_category = None
                try:
                    fabric_category = fabric_category_map.get(int(fabric_category_id))
                except (TypeError, ValueError):
                    fabric_category = None
                if fabric_category:
                    fabric_cost = float(fabric_category.price) * float(furniture.fabric_value)
                    item_price += fabric_cost
            
            custom_option = None
            custom_option_value_resolved = ''
            custom_option_name_resolved = custom_option_name_stored or ''
            custom_option_price = 0.0
            if custom_option_price_raw not in (None, ''):
                try:
                    custom_option_price = float(custom_option_price_raw)
                except (TypeError, ValueError):
                    custom_option_price = 0.0
            if custom_option_id:
                try:
                    option_id_int = int(custom_option_id)
                    custom_option = next(
                        (opt for opt in furniture.custom_options.all() if opt.id == option_id_int),
                        None,
                    )
                except (ValueError, TypeError):
                    custom_option = None
                if custom_option:
                    custom_option_value_resolved = custom_option.value
                    custom_option_name_resolved = furniture.custom_option_name
                    if custom_option_price_raw in (None, ''):
                        try:
                            custom_option_price = float(custom_option.price_delta)
                        except (TypeError, ValueError):
                            custom_option_price = 0.0
                elif custom_option_value:
                    custom_option_value_resolved = str(custom_option_value)
            elif custom_option_value:
                custom_option_value_resolved = str(custom_option_value)

            if not custom_option_value_resolved:
                custom_option_name_resolved = ""

            color_display = color_name or ""
            if color_id and not color_name:
                color_obj = None
                try:
                    color_obj = fabric_color_map.get(int(color_id))
                except (TypeError, ValueError):
                    color_obj = None
                if color_obj:
                    color_name = color_obj.name
                    color_palette_name = color_obj.palette.name if color_obj.palette else ""
                    color_hex = color_hex or (color_obj.hex_code or "")
                    if not color_image and color_obj.image:
                        try:
                            color_image = color_obj.image.url
                        except (ValueError, OSError):
                            color_image = ""
                    color_display = color_name
                else:
                    color_name = color_name or ""
                    color_palette_name = color_palette_name or ""

            item_price += custom_option_price
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
                    "custom_option_id": custom_option.id if custom_option else custom_option_id,
                    "custom_option_value": custom_option_value_resolved,
                    "custom_option_name": custom_option_name_resolved or (furniture.custom_option_name if custom_option_value_resolved else ""),
                    "custom_option_price": custom_option_price,
                    "total_price": item_price * quantity,
                    "color_display": color_display,
                    "color_hex": color_hex,
                    "color_image": color_image,
                    "cart_key": cart_key,  # Add cart key for removal functionality
                }
            )


        # Get all fabric categories for display in cart
        fabric_categories = FabricCategory.objects.all()
        
        context.update(
            {
                "cart_items": cart_items,
                "total_price": total_price,
                "fabric_categories": fabric_categories,
                "meta_title": "Кошик — Montal Home",
                "meta_description": (
                    "Перегляньте товари у кошику Montal Home та завершіть оформлення замовлення. "
                    "Зручна оплата, доставка по Україні."
                ),
                "meta_keywords": "кошик, замовлення меблів, купити меблі онлайн",
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        """Redirect to home if cart is empty."""
        cart = request.session.get("cart", {})
        if not cart:
            return redirect('shop:home')
        return super().get(request, *args, **kwargs)


class PromotionsView(TemplateView):
    """Promotional furniture listing."""

    template_name = "shop/promotions.html"

    def get_context_data(self, **kwargs):
        """Provide full list of active promotional furniture items."""
        context = super().get_context_data(**kwargs)
        context["promotional_items"] = list(
            fetch_active_promotional_furniture().order_by("-created_at")
        )
        context.update(
            {
                "meta_title": "Акції та знижки на меблі — Montal Home",
                "meta_description": (
                    "Знайдіть вигідні пропозиції на меблі в Montal Home. "
                    "Регулярні акції, сезонні знижки та спеціальні комплекти."
                ),
                "meta_keywords": "знижки на меблі, акції Montal, меблі зі знижкою",
            }
        )
        return context


class WhereToBuyView(TemplateView):
    """Where to buy page."""

    template_name = "shop/where_to_buy.html"
    extra_context = {
        "meta_title": "Де купити меблі Montal Home",
        "meta_description": (
            "Адреси салонів та партнерів Montal Home по Україні. "
            "Обирайте зручний формат покупки меблів — онлайн або офлайн."
        ),
        "meta_keywords": "де купити меблі Montal, салони меблів Україна",
    }


class ContactsView(TemplateView):
    """Contacts page."""

    template_name = "shop/contacts.html"
    extra_context = {
        "meta_title": "Контакти Montal Home",
        "meta_description": (
            "Зв’яжіться з командою Montal Home: телефон, email, графік роботи та адреси шоурумів."
        ),
        "meta_keywords": "контакти Montal Home, телефон Montal, меблевий магазин контакти",
    }


class WarrantyView(TemplateView):
    """Warranty page."""

    template_name = "shop/warranty.html"
    extra_context = {
        "meta_title": "Гарантія та сервіс — Montal Home",
        "meta_description": (
            "Дізнайтеся про гарантію, умови обслуговування та обміну меблів у Montal Home."
        ),
        "meta_keywords": "гарантія на меблі, сервіс Montal, обмін меблів",
    }


class DeliveryPaymentView(TemplateView):
    """Delivery and payment page."""

    template_name = "shop/delivery_payment.html"
    extra_context = {
        "meta_title": "Доставка та оплата — Montal Home",
        "meta_description": (
            "Умови доставки та оплати меблів у Montal Home: кур’єр, самовивіз, онлайн-оплата."
        ),
        "meta_keywords": "доставка меблів, оплата меблів, Montal доставка",
    }


class OfferView(TemplateView):
    """Offer page."""

    template_name = "shop/offer.html"
    extra_context = {
        "meta_title": "Публічна оферта Montal Home",
        "meta_description": (
            "Ознайомтеся з умовами покупки меблів у Montal Home у публічній оферті."
        ),
        "meta_keywords": "публічна оферта меблі, Montal оферта",
    }


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
        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            title = f'Пошук "{search_query}" — Montal Home'
            description = _summarize(
                f'Результати пошуку "{search_query}" у каталозі меблів Montal Home. '
                "Знайдіть потрібні меблі за назвою, кодом або описом."
            )
        else:
            title = "Пошук меблів — Montal Home"
            description = (
                "Скористайтеся пошуком по каталогу Montal Home, щоб швидко знайти потрібні меблі."
            )
        context.update({
            "search_query": search_query,
            "categories": Category.objects.all(),
            "meta_title": title,
            "meta_description": description,
            "meta_keywords": "пошук меблів, знайти меблі, каталог меблів Montal",
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
                custom_option_id = request.POST.get("custom_option_id")
                custom_option_value = None
                custom_option_price = 0.0
                custom_option_name = furniture.custom_option_name

                active_options = furniture.custom_options.filter(is_active=True)
                selected_option = None
                if active_options.exists():
                    if not custom_option_id:
                        return JsonResponse({"message": "Оберіть варіант перед додаванням у кошик."}, status=400)
                    try:
                        selected_option = active_options.get(id=int(custom_option_id))
                    except (ValueError, FurnitureCustomOption.DoesNotExist):
                        return JsonResponse({"message": "Обраний варіант недійсний."}, status=400)
                elif custom_option_id:
                    try:
                        selected_option = furniture.custom_options.get(id=int(custom_option_id))
                    except (ValueError, FurnitureCustomOption.DoesNotExist):
                        selected_option = None

                if selected_option:
                    custom_option_value = selected_option.value
                    custom_option_name = furniture.custom_option_name
                    try:
                        custom_option_price = float(selected_option.price_delta)
                    except (TypeError, ValueError):
                        custom_option_price = 0.0

                # Create a unique key for this cart item that includes variant information
                cart_key_parts = [furniture_id]
                if size_variant_id:
                    cart_key_parts.append(f"size_{size_variant_id}")
                if fabric_category_id:
                    cart_key_parts.append(f"fabric_{fabric_category_id}")
                if variant_image_id:
                    cart_key_parts.append(f"variant_{variant_image_id}")
                if selected_option:
                    cart_key_parts.append(f"custom_{selected_option.id}")
                
                cart_key = "_".join(cart_key_parts)
                
                existing_item = cart.get(cart_key, {}) if isinstance(cart.get(cart_key), dict) else {}
                # Create cart item data
                cart_item_data = {
                    'quantity': existing_item.get('quantity', 0) + 1
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

                if selected_option:
                    cart_item_data['custom_option_id'] = str(selected_option.id)
                    cart_item_data['custom_option_value'] = custom_option_value
                    cart_item_data['custom_option_price'] = custom_option_price
                    cart_item_data['custom_option_name'] = custom_option_name

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
    custom_option_id = request.POST.get("custom_option_id")
    color_id = request.POST.get("color_id")
    try:
        quantity = max(1, int(request.POST.get("quantity", 1)))
    except (TypeError, ValueError):
        quantity = 1

    if not furniture_id:
        messages.error(request, "Furniture ID is required", extra_tags="user")
        return redirect('furniture:furniture_detail', furniture_slug=request.POST.get("furniture_slug"))

    try:
        furniture = get_object_or_404(Furniture, id=furniture_id)
        cart = request.session.get("cart", {})

        active_options = furniture.custom_options.filter(is_active=True)
        selected_option = None
        custom_option_value = None
        custom_option_name = furniture.custom_option_name
        custom_option_price = 0.0
        if active_options.exists():
            if not custom_option_id:
                messages.error(request, "Оберіть варіант перед додаванням у кошик.", extra_tags="user")
                return redirect('furniture:furniture_detail', furniture_slug=furniture.slug)
            try:
                selected_option = active_options.get(id=int(custom_option_id))
            except (ValueError, FurnitureCustomOption.DoesNotExist):
                messages.error(request, "Обраний варіант недійсний. Спробуйте знову.", extra_tags="user")
                return redirect('furniture:furniture_detail', furniture_slug=furniture.slug)
        elif custom_option_id:
            # Ignore unexpected value if furniture no longer has active options
            try:
                selected_option = furniture.custom_options.get(id=int(custom_option_id))
            except (ValueError, FurnitureCustomOption.DoesNotExist):
                selected_option = None

        if selected_option:
            custom_option_value = selected_option.value
            custom_option_name = furniture.custom_option_name
            try:
                custom_option_price = float(selected_option.price_delta)
            except (TypeError, ValueError):
                custom_option_price = 0.0

        color_name = ""
        color_palette_name = ""
        color_hex = ""
        color_image_url = ""
        if color_id:
            try:
                color_obj = FabricColor.objects.select_related("palette").get(id=int(color_id))
                color_name = color_obj.name
                color_palette_name = color_obj.palette.name if color_obj.palette else ""
                color_hex = color_obj.hex_code or ""
                try:
                    color_image_url = color_obj.image.url if color_obj.image else ""
                except (ValueError, OSError):
                    color_image_url = ""
            except (ValueError, FabricColor.DoesNotExist):
                color_id = None

        # Create a unique key for this cart item that includes variant information
        cart_key_parts = [furniture_id]
        if size_variant_id:
            cart_key_parts.append(f"size_{size_variant_id}")
        if fabric_category_id:
            cart_key_parts.append(f"fabric_{fabric_category_id}")
        if variant_image_id:
            cart_key_parts.append(f"variant_{variant_image_id}")
        if selected_option:
            cart_key_parts.append(f"custom_{selected_option.id}")
        if color_id:
            cart_key_parts.append(f"color_{color_id}")
        
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
        
        if selected_option:
            cart_item_data['custom_option_id'] = str(selected_option.id)
            cart_item_data['custom_option_value'] = custom_option_value
            cart_item_data['custom_option_price'] = custom_option_price
            cart_item_data['custom_option_name'] = custom_option_name
        
        if color_id:
            cart_item_data['color_id'] = str(color_id)
            cart_item_data['color_name'] = color_name
            cart_item_data['color_palette_name'] = color_palette_name
            cart_item_data['color_hex'] = color_hex
            cart_item_data['color_image'] = color_image_url
        
        cart[cart_key] = cart_item_data
        request.session["cart"] = cart
        request.session.modified = True

        messages.success(request, f"{furniture.name} додано до кошика!", extra_tags="user")
        return redirect('furniture:furniture_detail', furniture_slug=furniture.slug)

    except Exception as e:
        messages.error(request, str(e), extra_tags="user")
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
        messages.error(request, "Cart key or Furniture ID is required", extra_tags="user")
        return redirect('shop:view_cart')
    
    try:
        cart = request.session.get("cart", {})
        
        # If cart_key is provided, use it directly
        if cart_key and cart_key in cart:
            del cart[cart_key]
            request.session["cart"] = cart
            request.session.modified = True
            messages.success(request, "Товар видалено з кошика!", extra_tags="user")
        # Fallback to furniture_id for backward compatibility
        elif furniture_id:
            # Find and remove items with this furniture_id
            keys_to_remove = [key for key in cart.keys() if key.startswith(f"{furniture_id}_") or key == furniture_id]
            if keys_to_remove:
                for key in keys_to_remove:
                    del cart[key]
                request.session["cart"] = cart
                request.session.modified = True
                messages.success(request, "Товар видалено з кошика!", extra_tags="user")
            else:
                messages.error(request, "Товар не знайдено в кошику!", extra_tags="user")
        else:
            messages.error(request, "Товар не знайдено в кошику!", extra_tags="user")
        
        # If cart is empty, redirect to home
        if not cart:
            return redirect('shop:home')
        
        return redirect('shop:view_cart')
        
    except Exception as e:
        messages.error(request, str(e), extra_tags="user")
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
