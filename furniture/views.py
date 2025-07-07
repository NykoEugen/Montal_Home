from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from furniture.models import Furniture


def furniture_detail(request: HttpRequest, furniture_slug: str) -> HttpResponse:
    furniture = get_object_or_404(Furniture, slug=furniture_slug)
    parameters = furniture.parameters.select_related("parameter").all()
    return render(
        request,
        "furniture/furniture_detail.html",
        {"furniture": furniture, "parameters": parameters},
    )
