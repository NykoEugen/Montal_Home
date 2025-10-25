from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.html import strip_tags
from django.utils.text import Truncator

from categories.models import Category
from furniture.models import Furniture
from sub_categories.models import SubCategory


def categories_list(request: HttpRequest) -> HttpResponse:
    categories = Category.objects.all()
    context = {
        "categories": categories,
        "meta_title": "Каталог меблів — Montal Home",
        "meta_description": (
            "Перегляньте головні категорії меблів Montal Home: вітальні, спальні, кухні та офіс. "
            "Зручна навігація та вигідні пропозиції."
        ),
        "meta_keywords": "каталог меблів, категорії меблів, Montal каталог",
    }
    return render(request, "categories/categories_list.html", context)


def category_detail(request: HttpRequest, category_slug: str) -> HttpResponse:
    category = get_object_or_404(Category, slug=category_slug)
    # Filter subcategories that have furniture items
    sub_categories = SubCategory.objects.filter(
        category=category, 
        furniture__isnull=False
    ).distinct()
    paginator = Paginator(sub_categories, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    def summarize(text: str, length: int = 160) -> str:
        clean_text = strip_tags(text or "")
        return Truncator(clean_text).chars(length, truncate="…")

    context = {
        "sub_categories": sub_categories,
        "page_obj": page_obj,
        "category": category,
        "meta_title": f"{category.name} — меблі Montal Home",
        "meta_description": summarize(
            f"Оберіть меблі у категорії {category.name} від Montal Home. "
            "Знайдіть відповідні підкатегорії та інтер’єрні рішення."
        ),
        "meta_keywords": f"{category.name} меблі, купити {category.name.lower()} Montal, каталог меблів",
    }
    return render(request, "sub_categories/sub_categories_list.html", context)
