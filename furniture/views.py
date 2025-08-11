from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from fabric_category.models import FabricCategory
from furniture.models import Furniture


def furniture_detail(request: HttpRequest, furniture_slug: str) -> HttpResponse:
    furniture = get_object_or_404(Furniture, slug=furniture_slug)
    raw_parameters = furniture.parameters.select_related("parameter").all()
    size_variants = furniture.get_size_variants()
    gallery_images = list(getattr(furniture, 'images').all()) if hasattr(furniture, 'images') else []

    # Virtual parameter structure for consistent template access
    class VirtualParameter:
        def __init__(self, key: str, label: str, value: str, base_value: str | None = None):
            self.key = key
            self.label = label
            self.value = value
            self.base_value = base_value or value

    # Process parameters to combine dimensions and normalize others
    parameters: list[VirtualParameter] = []
    dimensions: dict[str, str] = {}

    for param in raw_parameters:
        param_key = getattr(param.parameter, 'key', '')
        param_label = getattr(param.parameter, 'label', '')
        if param_key in ['height', 'width', 'length']:
            dimensions[param_key] = param.value
        else:
            parameters.append(VirtualParameter(param_key, param_label, param.value))

    # Add combined dimensions parameter if dimensions exist
    if dimensions:
        height = dimensions.get('height', '0')
        width = dimensions.get('width', '0')
        length = dimensions.get('length', '0')
        # Ensure integers for display
        try:
            height_i = int(float(height))
            width_i = int(float(width))
            length_i = int(float(length))
        except ValueError:
            height_i, width_i, length_i = height, width, length
        combined_dimensions = f"{height_i}x{width_i}x{length_i} см"
        # Insert dimensions at the beginning with requested label
        parameters.insert(0, VirtualParameter('dimensions', 'Розмір (ВхШхД)', combined_dimensions, combined_dimensions))

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
            "size_variants": size_variants,
            "gallery_images": gallery_images,
            "fabric_categories": fabric_categories,
        },
    )
