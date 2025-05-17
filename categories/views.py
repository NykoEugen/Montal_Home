from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from categories.models import Category
from furniture.models import Furniture


def categories_list(request: HttpRequest) -> HttpResponse:
    categories = Category.objects.all()
    context = {"categories": categories}
    return render(request, "categories/categories_list.html", context)


def category_detail(request: HttpRequest, category_slug: str) -> HttpResponse:
    category = get_object_or_404(Category, slug=category_slug)
    furniture = Furniture.objects.filter(category=category)
    paginator = Paginator(furniture, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"category": category, "page_obj": page_obj}
    return render(request, "categories/category_detail.html", context)
