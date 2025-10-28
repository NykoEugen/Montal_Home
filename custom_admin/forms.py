from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from categories.models import Category
from checkout.models import Order, OrderItem
from fabric_category.models import FabricBrand, FabricCategory
from furniture.models import (
    Furniture,
    FurnitureCustomOption,
    FurnitureImage,
    FurnitureSizeVariant,
    FurnitureVariantImage,
)
from params.models import Parameter, FurnitureParameter
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


class OrderItemInlineForm(OrderItemForm):
    class Meta(OrderItemForm.Meta):
        fields = [field for field in OrderItemForm.Meta.fields if field != "order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "order" in self.fields:
            self.fields["order"].widget = forms.HiddenInput()
            self.fields["order"].required = False


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


class FurnitureSizeVariantForm(StyledModelForm):
    class Meta:
        model = FurnitureSizeVariant
        fields = [
            "furniture",
            "height",
            "width",
            "length",
            "is_foldable",
            "unfolded_length",
            "price",
            "promotional_price",
            "is_promotional",
            "sale_end_date",
            "parameter",
            "parameter_value",
        ]
        widgets = {
            "sale_end_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.sale_end_date:
            self.initial["sale_end_date"] = self.instance.sale_end_date.strftime("%Y-%m-%dT%H:%M")


class FurnitureSizeVariantInlineForm(FurnitureSizeVariantForm):
    class Meta(FurnitureSizeVariantForm.Meta):
        fields = [field for field in FurnitureSizeVariantForm.Meta.fields if field != "furniture"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "furniture" in self.fields:
            self.fields["furniture"].widget = forms.HiddenInput()
            self.fields["furniture"].required = False


class FurnitureCustomOptionForm(StyledModelForm):
    class Meta:
        model = FurnitureCustomOption
        fields = [
            "furniture",
            "value",
            "price_delta",
            "position",
            "is_active",
        ]


class FurnitureVariantImageForm(StyledModelForm):
    class Meta:
        model = FurnitureVariantImage
        fields = [
            "furniture",
            "name",
            "stock_status",
            "image",
            "link",
            "is_default",
            "position",
        ]


class FurnitureImageForm(StyledModelForm):
    class Meta:
        model = FurnitureImage
        fields = [
            "furniture",
            "image",
            "alt_text",
            "position",
        ]


class FurnitureCustomOptionInlineForm(FurnitureCustomOptionForm):
    class Meta(FurnitureCustomOptionForm.Meta):
        fields = [field for field in FurnitureCustomOptionForm.Meta.fields if field != "furniture"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "furniture" in self.fields:
            self.fields["furniture"].widget = forms.HiddenInput()
            self.fields["furniture"].required = False


class FurnitureVariantImageInlineForm(FurnitureVariantImageForm):
    class Meta(FurnitureVariantImageForm.Meta):
        fields = [field for field in FurnitureVariantImageForm.Meta.fields if field != "furniture"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "furniture" in self.fields:
            self.fields["furniture"].widget = forms.HiddenInput()
            self.fields["furniture"].required = False


class FurnitureImageInlineForm(FurnitureImageForm):
    class Meta(FurnitureImageForm.Meta):
        fields = [field for field in FurnitureImageForm.Meta.fields if field != "furniture"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "furniture" in self.fields:
            self.fields["furniture"].widget = forms.HiddenInput()
            self.fields["furniture"].required = False


class OrderItemInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "order" in self.form.base_fields:
            self.form.base_fields["order"].widget = forms.HiddenInput()
            self.form.base_fields["order"].required = False


class FurnitureParameterForm(StyledModelForm):
    class Meta:
        model = FurnitureParameter
        fields = ["parameter", "value"]


class FurnitureParameterInlineForm(FurnitureParameterForm):
    class Meta(FurnitureParameterForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parameter"].label = "Параметр"
        self.fields["value"].label = "Значення"


class FurnitureParameterInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed_params = (
            self.instance.sub_category.allowed_params.all()
            if getattr(self.instance, "sub_category_id", None)
            else Parameter.objects.none()
        )
        for form in self.forms:
            if "parameter" in form.fields:
                form.fields["parameter"].queryset = allowed_params
        if "parameter" in self.empty_form.fields:
            self.empty_form.fields["parameter"].queryset = allowed_params


FurnitureSizeVariantFormSet = inlineformset_factory(
    Furniture,
    FurnitureSizeVariant,
    form=FurnitureSizeVariantInlineForm,
    extra=0,
    can_delete=True,
)

FurnitureCustomOptionFormSet = inlineformset_factory(
    Furniture,
    FurnitureCustomOption,
    form=FurnitureCustomOptionInlineForm,
    extra=0,
    can_delete=True,
)

FurnitureVariantImageFormSet = inlineformset_factory(
    Furniture,
    FurnitureVariantImage,
    form=FurnitureVariantImageInlineForm,
    extra=0,
    can_delete=True,
)

FurnitureImageFormSet = inlineformset_factory(
    Furniture,
    FurnitureImage,
    form=FurnitureImageInlineForm,
    extra=0,
    can_delete=True,
)

OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemInlineForm,
    formset=OrderItemInlineFormSet,
    extra=0,
    can_delete=True,
)

FurnitureParameterFormSet = inlineformset_factory(
    Furniture,
    FurnitureParameter,
    form=FurnitureParameterInlineForm,
    formset=FurnitureParameterInlineFormSet,
    extra=0,
    can_delete=True,
)
