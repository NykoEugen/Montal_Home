from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

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

    parameter_filters = []
    for param in sub_category.allowed_params.all():
        param_key = f"param_{param.key}"
        if param_key in request.GET and request.GET[param_key]:
            parameter_filters.append((param_key, request.GET[param_key]))

    # Фільтрація за параметрами
    for param_key, value in parameter_filters:
        key = param_key.replace("param_", "")  # Видаляємо префікс
        furniture = furniture.filter(
            parameters__parameter__key=key, parameters__value=value
        )

    sort = request.GET.get("sort", "")
    if sort == "price_asc":
        furniture = furniture.order_by("price")
    elif sort == "price_desc":
        furniture = furniture.order_by("-price")

    paginator = Paginator(furniture, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

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

    context = {
        "sub_category": sub_category,
        "page_obj": page_obj,
        "filter_options": filter_options,
        "current_filters": parameter_filters,
        "current_sort": sort,
    }
    return render(request, "sub_categories/sub_category_detail.html", context)
