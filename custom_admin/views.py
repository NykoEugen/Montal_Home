from __future__ import annotations

from functools import cached_property
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import FieldError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView

from .forms import (
    FurnitureCustomOptionFormSet,
    FurnitureImageFormSet,
    OrderItemFormSet,
    FurnitureParameterFormSet,
    FurnitureSizeVariantFormSet,
    FurnitureVariantImageFormSet,
)
from .registry import AdminSection, registry


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Ensure the user is authenticated and flagged as staff."""

    login_url = reverse_lazy("custom_admin:login")

    def test_func(self) -> bool:
        return bool(self.request.user and self.request.user.is_staff)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise Http404("Сторінку не знайдено")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("sections", list(registry.all()))
        return context


class CustomAdminLoginView(LoginView):
    template_name = "custom_admin/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse("custom_admin:dashboard")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (
                f"{classes} block w-full border border-beige-300 rounded-lg px-3 py-2 "
                "text-brown-800 focus:outline-none focus:ring-2 focus:ring-brown-500 "
                "focus:border-transparent"
            ).strip()
        return form


class CustomAdminLogoutView(LogoutView):
    next_page = reverse_lazy("custom_admin:login")


class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = "custom_admin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sections = list(registry.all())
        stats = []
        for section in sections:
            count = section.model.objects.count()
            stats.append(
                {
                    "section": section,
                    "count": count,
                    "url": reverse("custom_admin:list", args=[section.slug]),
                }
            )
        context.update(
            {
                "sections": sections,
                "stats": stats,
            }
        )
        return context


class SectionMixin(StaffRequiredMixin):
    section_slug_kwarg = "section_slug"

    @cached_property
    def section(self) -> AdminSection:
        slug = self.kwargs.get(self.section_slug_kwarg)
        try:
            return registry.get(slug)
        except KeyError as exc:
            raise Http404("Розділ не знайдено") from exc

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["section"] = self.section
        context["list_url"] = reverse("custom_admin:list", args=[self.section.slug])
        context["create_url"] = reverse("custom_admin:create", args=[self.section.slug])
        context["can_create"] = self.section.allow_create
        context["can_edit"] = self.section.allow_edit
        context["can_delete"] = self.section.allow_delete
        return context


class SectionListView(SectionMixin, ListView):
    template_name = "custom_admin/list.html"
    context_object_name = "objects"
    paginate_by = 20

    def get_queryset(self):
        queryset = self.section.model.objects.all()
        ordering = self.section.ordering or self.section.model._meta.ordering
        if ordering:
            queryset = queryset.order_by(*ordering)

        search_query = self.request.GET.get("q")
        if search_query and self.section.search_fields:
            q_object = Q()
            for field in self.section.search_fields:
                lookup = f"{field}__icontains"
                try:
                    q_object |= Q(**{lookup: search_query})
                except FieldError:
                    try:
                        q_object |= Q(**{f"{field}__exact": search_query})
                    except FieldError:
                        continue
            queryset = queryset.filter(q_object)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        headers = []
        if self.section.list_display_labels:
            headers = list(self.section.list_display_labels)
        else:
            for column in self.section.list_display:
                verbose = None
                try:
                    field = self.section.model._meta.get_field(column)
                    verbose = field.verbose_name
                except Exception:
                    verbose = column.replace("_", " ")
                headers.append(str(verbose).capitalize())

        context["list_display"] = self.section.list_display
        context["list_headers"] = headers
        context["search_query"] = self.request.GET.get("q", "")
        context["show_actions"] = self.section.allow_edit or self.section.allow_delete
        context["column_span"] = len(self.section.list_display) + (1 if context["show_actions"] else 0)
        return context


class SectionFormMixin(SectionMixin):
    template_name = "custom_admin/form.html"
    section_templates = {
        "furniture": "custom_admin/furniture_form.html",
        "orders": "custom_admin/order_form.html",
    }

    def get_form_class(self):
        return self.section.form_class

    def get_template_names(self):
        return [self.section_templates.get(self.section.slug, self.template_name)]

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Зміни успішно збережено."))
        return response

    def form_invalid(self, form):
        messages.error(self.request, _("Будь ласка, виправте помилки у формі."))
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("custom_admin:list", args=[self.section.slug])


class SectionCreateView(SectionFormMixin, CreateView):
    template_name = "custom_admin/form.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.section.allow_create:
            raise Http404("Створення у цьому розділі недоступне.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return self.section.form_class

    def get_queryset(self):
        return self.section.model.objects.all()


class SectionUpdateView(SectionFormMixin, UpdateView):
    template_name = "custom_admin/form.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.section.allow_edit:
            raise Http404("Редагування у цьому розділі недоступне.")
        return super().dispatch(request, *args, **kwargs)

    def _uses_formsets(self) -> bool:
        return self.section.slug in {"furniture", "orders"}

    def _init_formsets(self, data=None, files=None):
        if not self._uses_formsets():
            return {}
        if data is None and hasattr(self, "_formsets_cache"):
            return self._formsets_cache

        instance = getattr(self, "object", None)
        formsets: dict[str, Any] = {}

        if self.section.slug == "furniture":
            formsets = {
                "size_variant_formset": FurnitureSizeVariantFormSet(
                    data=data,
                    files=files,
                    instance=instance,
                    prefix="size_variants",
                ),
                "custom_option_formset": FurnitureCustomOptionFormSet(
                    data=data,
                    files=files,
                    instance=instance,
                    prefix="custom_options",
                ),
                "parameter_formset": FurnitureParameterFormSet(
                    data=data,
                    files=files,
                    instance=instance,
                    prefix="parameters",
                ),
                "variant_image_formset": FurnitureVariantImageFormSet(
                    data=data,
                    files=files,
                    instance=instance,
                    prefix="variant_images",
                ),
                "image_formset": FurnitureImageFormSet(
                    data=data,
                    files=files,
                    instance=instance,
                    prefix="gallery_images",
                ),
            }
        elif self.section.slug == "orders":
            formsets = {
                "order_item_formset": OrderItemFormSet(
                    data=data,
                    files=files,
                    instance=instance,
                    prefix="order_items",
                )
            }

        if data is None and files is None:
            self._formsets_cache = formsets
        return formsets

    def get(self, request, *args, **kwargs):
        if self._uses_formsets():
            self.object = self.get_object()
            form = self.get_form()
            self._init_formsets()
            return self.render_to_response(self.get_context_data(form=form))
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self._uses_formsets():
            return super().post(request, *args, **kwargs)

        self.object = self.get_object()
        form = self.get_form()
        formsets = self._init_formsets(data=request.POST, files=request.FILES)
        if form.is_valid() and all(fs.is_valid() for fs in formsets.values()):
            return self._formsets_valid(form, formsets)
        return self._formsets_invalid(form, formsets)

    def _formsets_valid(self, form, formsets):
        with transaction.atomic():
            response = super().form_valid(form)
            for formset in formsets.values():
                formset.instance = self.object
                formset.save()
        return response

    def _formsets_invalid(self, form, formsets):
        self._formsets_cache = formsets
        return self.render_to_response(self.get_context_data(form=form))

    def get_form_class(self):
        return self.section.form_class

    def get_queryset(self):
        return self.section.model.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self._uses_formsets():
            context.update(self._init_formsets())
        return context


class SectionDeleteView(SectionMixin, DeleteView):
    template_name = "custom_admin/confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.section.allow_delete:
            raise Http404("Видалення у цьому розділі недоступне.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        queryset = queryset or self.section.model.objects.all()
        return super().get_object(queryset=queryset)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Обʼєкт успішно видалено."))
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("custom_admin:list", args=[self.section.slug])


def redirect_to_dashboard(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("custom_admin:dashboard")
    return redirect("custom_admin:login")
