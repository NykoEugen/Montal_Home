from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.db.models import Q, Min, Max

from furniture.models import Furniture
from params.models import FurnitureParameter
from sub_categories.models import SubCategory


def sub_categories_list(request: HttpRequest) -> HttpResponse:
    sub_categories = SubCategory.objects.all()
    context = {"sub_categories": sub_categories}
    return render(request, "sub_categories/sub_categories_list.html", context)


def sub_categories_details(
    request: HttpRequest, sub_categories_slug: str
) -> HttpResponse:
    sub_category = get_object_or_404(SubCategory, slug=sub_categories_slug)
    furniture = Furniture.objects.filter(sub_category=sub_category)

    # Price range filtering
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    
    if min_price:
        try:
            min_price = float(min_price)
            furniture = furniture.filter(price__gte=min_price)
        except (ValueError, TypeError):
            pass
    
    if max_price:
        try:
            max_price = float(max_price)
            furniture = furniture.filter(price__lte=max_price)
        except (ValueError, TypeError):
            pass

    # Stock status filtering
    stock_status_list = request.GET.getlist("stock_status")
    if stock_status_list:
        furniture = furniture.filter(stock_status__in=stock_status_list)

    # Promotional items filtering
    promotional_only = request.GET.get("promotional_only")
    if promotional_only:
        furniture = furniture.filter(is_promotional=True, promotional_price__isnull=False)

    # Parameter filtering
    parameter_filters = []
    for param in sub_category.allowed_params.all():
        param_key = f"param_{param.key}"
        if param_key in request.GET and request.GET[param_key]:
            parameter_filters.append((param_key, request.GET[param_key]))

    # Apply parameter filters
    for param_key, value in parameter_filters:
        key = param_key.replace("param_", "")
        furniture = furniture.filter(
            parameters__parameter__key=key, parameters__value=value
        )

    # Sorting
    sort = request.GET.get("sort", "")
    if sort == "price_asc":
        furniture = furniture.order_by("price")
    elif sort == "price_desc":
        furniture = furniture.order_by("-price")
    elif sort == "name_asc":
        furniture = furniture.order_by("name")
    elif sort == "name_desc":
        furniture = furniture.order_by("-name")
    else:
        # Default sorting: promotional items first, then by name
        furniture = furniture.order_by("-is_promotional", "name")

    # Pagination
    paginator = Paginator(furniture, 12)  # Increased items per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Prepare filter options
    filter_options = {}
    for param in sub_category.allowed_params.all():
        values = (
            FurnitureParameter.objects.filter(
                furniture__sub_category=sub_category, parameter__key=param.key
            )
            .values_list("value", flat=True)
            .distinct()
        )
        filter_options[param.key] = {"label": param.label, "values": sorted(values)}

    # Get price range for the category
    price_range = furniture.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )

    context = {
        "sub_category": sub_category,
        "page_obj": page_obj,
        "filter_options": filter_options,
        "current_filters": parameter_filters,
        "current_sort": sort,
        "price_range": price_range,
    }
    return render(request, "sub_categories/sub_category_detail.html", context)
