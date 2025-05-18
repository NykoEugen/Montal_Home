from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from furniture.models import Furniture
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
    paginator = Paginator(furniture, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"sub_category": sub_category, "page_obj": page_obj}
    return render(request, "sub_categories/sub_category_detail.html", context)
