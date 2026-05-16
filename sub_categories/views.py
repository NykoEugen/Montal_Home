from django.core.paginator import Paginator
from django.db.models import Min, Max, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.views.decorators.cache import cache_page

from furniture.models import Furniture, FurnitureSizeVariant
from params.models import FurnitureParameter
from sub_categories.models import SubCategory

_SORT_MAP = {
    "price_asc": "price",
    "price_desc": "-price",
    "name_asc": "name",
    "name_desc": "-name",
}


@cache_page(90)
def sub_categories_list(request: HttpRequest) -> HttpResponse:
    sub_categories = SubCategory.objects.filter(furniture__isnull=False).distinct()
    context = {
        "sub_categories": sub_categories,
        "meta_title": "Підкатегорії меблів — Montal Home",
        "meta_description": (
            "Перегляньте підкатегорії меблів Montal Home, щоб швидко знайти потрібні моделі та стилі."
        ),
        "meta_keywords": "підкатегорії меблів, меблі за стилем, Montal каталог",
    }
    return render(request, "sub_categories/sub_categories_list.html", context)


def sub_categories_details(
    request: HttpRequest, sub_categories_slug: str
) -> HttpResponse:
    sub_category = get_object_or_404(SubCategory, slug=sub_categories_slug)

    # Only group leaders visible in listing (variants accessible from product page)
    base_qs = Furniture.objects.filter(
        sub_category=sub_category,
        variant_group_leader__isnull=True,
    )

    # --- Build filter options in 2 queries (not N×2) ---
    fp_rows = (
        FurnitureParameter.objects
        .filter(furniture__sub_category=sub_category)
        .exclude(value="").exclude(value__isnull=True)
        .values("parameter__key", "parameter__label", "value")
        .distinct()
    )
    sv_rows = (
        FurnitureSizeVariant.objects
        .filter(furniture__sub_category=sub_category)
        .exclude(parameter_value="").exclude(parameter_value__isnull=True)
        .exclude(parameter__isnull=True)
        .values("parameter__key", "parameter__label", "parameter_value")
        .distinct()
    )

    raw_options: dict[str, dict] = {}
    for row in fp_rows:
        key = row["parameter__key"]
        if key not in raw_options:
            raw_options[key] = {"label": row["parameter__label"], "values": set()}
        raw_options[key]["values"].add(row["value"])
    for row in sv_rows:
        key = row["parameter__key"]
        if key not in raw_options:
            raw_options[key] = {"label": row["parameter__label"], "values": set()}
        raw_options[key]["values"].add(row["parameter_value"])

    # Only expose params with 2+ distinct values (single-value params useless as filter)
    filter_options = {
        k: {"label": v["label"], "values": sorted(v["values"])}
        for k, v in raw_options.items()
        if len(v["values"]) >= 2
    }

    # --- Read active filters ---
    min_price_raw = request.GET.get("min_price", "").strip()
    max_price_raw = request.GET.get("max_price", "").strip()
    stock_status_list = request.GET.getlist("stock_status")
    promotional_only = bool(request.GET.get("promotional_only", "").strip())
    sort = request.GET.get("sort", "").strip()
    if sort not in _SORT_MAP:
        sort = ""

    active_param_filters: dict[str, str] = {}
    for key in filter_options:
        val = request.GET.get(f"param_{key}", "").strip()
        if val:
            active_param_filters[key] = val

    # --- Price range from full unfiltered queryset ---
    price_range = base_qs.aggregate(min_price=Min("price"), max_price=Max("price"))

    # --- Apply filters ---
    qs = base_qs

    if min_price_raw:
        try:
            qs = qs.filter(price__gte=float(min_price_raw))
        except ValueError:
            min_price_raw = ""

    if max_price_raw:
        try:
            qs = qs.filter(price__lte=float(max_price_raw))
        except ValueError:
            max_price_raw = ""

    if stock_status_list:
        qs = qs.filter(stock_status__in=stock_status_list)

    if promotional_only:
        qs = qs.filter(is_promotional=True, promotional_price__isnull=False)

    for key, value in active_param_filters.items():
        qs = qs.filter(
            Q(parameters__parameter__key=key, parameters__value=value)
            | Q(size_variants__parameter__key=key, size_variants__parameter_value=value)
        )

    if active_param_filters:
        qs = qs.distinct()

    # --- Sort ---
    order = _SORT_MAP.get(sort)
    qs = qs.order_by(order) if order else qs.order_by("-is_promotional", "name")

    # --- Paginate ---
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    def summarize(text: str, length: int = 160) -> str:
        return Truncator(strip_tags(text or "")).chars(length, truncate="…")

    context = {
        "sub_category": sub_category,
        "page_obj": page_obj,
        "filter_options": filter_options,
        "active_param_filters": active_param_filters,
        "current_sort": sort,
        "price_range": price_range,
        "min_price_raw": min_price_raw,
        "max_price_raw": max_price_raw,
        "meta_title": f"{sub_category.name} — меблі Montal Home",
        "meta_description": summarize(
            f"Дивіться меблі у підкатегорії {sub_category.name} від Montal Home. "
            "Фільтруйте товари за параметрами, наявністю та акціями."
        ),
        "meta_keywords": f"{sub_category.name} меблі, купити {sub_category.name.lower()} Montal, меблі онлайн",
    }
    return render(request, "sub_categories/sub_category_detail.html", context)
