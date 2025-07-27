from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from fabric_category.models import FabricCategory
from furniture.models import Furniture


def furniture_detail(request: HttpRequest, furniture_slug: str) -> HttpResponse:
    furniture = get_object_or_404(Furniture, slug=furniture_slug)
    parameters = furniture.parameters.select_related("parameter").all()
    fabric_categories = []
    if furniture.selected_fabric_brand:
        fabric_categories = FabricCategory.objects.filter(
            brand=furniture.selected_fabric_brand
        )
    return render(
        request,
        "furniture/furniture_detail.html",
        {
            "furniture": furniture,
            "parameters": parameters,
            "fabric_categories": fabric_categories,
        },
    )
