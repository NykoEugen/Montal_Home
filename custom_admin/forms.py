from django import forms

from categories.models import Category
from checkout.models import Order, OrderItem
from fabric_category.models import FabricBrand, FabricCategory
from furniture.models import Furniture
from params.models import Parameter
from price_parser.models import GoogleSheetConfig, FurniturePriceCellMapping
from sub_categories.models import SubCategory


class StyledModelForm(forms.ModelForm):
    """Base form that applies Tailwind-friendly classes to widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            classes = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "h-4 w-4 text-brown-600 border-beige-300 rounded focus:ring-brown-500"
            elif isinstance(field.widget, forms.CheckboxSelectMultiple):
                if not classes:
                    field.widget.attrs["class"] = "grid gap-2"
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs["class"] = (
                    "block w-full text-brown-800 border border-beige-300 rounded-lg "
                    "px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-brown-500 "
                    "focus:border-transparent"
                )
            else:
                field.widget.attrs["class"] = (
                    f"{classes} block w-full border border-beige-300 rounded-lg px-3 py-2 "
                    "text-brown-800 focus:outline-none focus:ring-2 focus:ring-brown-500 "
                    "focus:border-transparent"
                ).strip()


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "image"]


class SubCategoryForm(StyledModelForm):
    class Meta:
        model = SubCategory
        fields = ["name", "slug", "category", "allowed_params", "image"]
        widgets = {
            "allowed_params": forms.CheckboxSelectMultiple(
                attrs={"class": "grid grid-cols-1 md:grid-cols-2 gap-2"}
            ),
        }


class ParameterForm(StyledModelForm):
    class Meta:
        model = Parameter
        fields = ["key", "label"]


class FabricBrandForm(StyledModelForm):
    class Meta:
        model = FabricBrand
        fields = ["name"]


class FabricCategoryForm(StyledModelForm):
    class Meta:
        model = FabricCategory
        fields = ["brand", "name", "price"]


class FurnitureForm(StyledModelForm):
    class Meta:
        model = Furniture
        fields = [
            "name",
            "article_code",
            "stock_status",
            "slug",
            "sub_category",
            "price",
            "is_promotional",
            "promotional_price",
            "sale_end_date",
            "description",
            "image",
            "selected_fabric_brand",
            "fabric_value",
            "custom_option_name",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "sale_end_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "sale_end_date" in self.fields:
            self.fields["sale_end_date"].input_formats = [
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
            ]
        # Ensure the datetime widget renders initial value in HTML5 format
        if self.instance and self.instance.sale_end_date:
            self.initial["sale_end_date"] = self.instance.sale_end_date.strftime("%Y-%m-%dT%H:%M")


class OrderForm(StyledModelForm):
    class Meta:
        model = Order
        fields = [
            "customer_name",
            "customer_last_name",
            "customer_phone_number",
            "customer_email",
            "delivery_type",
            "delivery_city",
            "delivery_branch",
            "delivery_address",
            "payment_type",
        ]
        widgets = {
            "delivery_address": forms.Textarea(attrs={"rows": 3}),
        }


class OrderItemForm(StyledModelForm):
    class Meta:
        model = OrderItem
        fields = [
            "order",
            "furniture",
            "quantity",
            "price",
            "original_price",
            "is_promotional",
            "size_variant_id",
            "size_variant_original_price",
            "size_variant_is_promotional",
            "fabric_category_id",
            "variant_image_id",
            "custom_option",
            "custom_option_name",
            "custom_option_value",
            "custom_option_price",
        ]


class GoogleSheetConfigForm(StyledModelForm):
    class Meta:
        model = GoogleSheetConfig
        fields = [
            "name",
            "sheet_url",
            "sheet_id",
            "xlsx_file",
            "price_multiplier",
            "sheet_name",
            "sheet_gid",
            "is_active",
        ]


class FurniturePriceCellMappingForm(StyledModelForm):
    class Meta:
        model = FurniturePriceCellMapping
        fields = [
            "furniture",
            "config",
            "sheet_row",
            "sheet_column",
            "price_type",
            "size_variant",
            "is_active",
        ]
