from __future__ import annotations

from functools import cached_property
from typing import Any, Optional

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import FieldError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, DetailView, ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView

from checkout.models import Order
from checkout.invoice import generate_and_upload_invoice
from price_parser.models import GoogleSheetConfig, SupplierFeedConfig
from price_parser.services import GoogleSheetsPriceUpdater, SupplierFeedPriceUpdater
from sub_categories.models import SubCategory

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
        context["section_read_only"] = self.section.read_only
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

        if self.section.slug == "furniture":
            sub_category_id = self.request.GET.get("sub_category")
            if sub_category_id:
                try:
                    queryset = queryset.filter(sub_category_id=int(sub_category_id))
                except (TypeError, ValueError):
                    pass

            stock_status = self.request.GET.get("stock_status")
            if stock_status:
                queryset = queryset.filter(stock_status=stock_status)
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
        bulk_action = self._get_bulk_action_context()
        context["bulk_action"] = bulk_action
        has_bulk_actions = bool(bulk_action)
        action_columns = 1 if context["show_actions"] else 0
        if has_bulk_actions:
            action_columns += 1
        context["column_span"] = len(self.section.list_display) + action_columns
        querydict = self.request.GET.copy()
        querydict.pop("page", None)
        context["current_query_string"] = querydict.urlencode()
        context["section_read_only"] = self.section.read_only
        if self.section.slug == "furniture":
            context["filter_options"] = {
                "sub_categories": SubCategory.objects.order_by("name"),
                "selected_sub_category": self.request.GET.get("sub_category", ""),
                "stock_choices": getattr(self.section.model, "STOCK_STATUS_CHOICES", []),
                "selected_stock_status": self.request.GET.get("stock_status", ""),
            }
        return context

    def _get_bulk_action_context(self) -> Optional[dict[str, str]]:
        if self.section.slug == "price-configs":
            return {
                "url": reverse("custom_admin:price_config_bulk_action"),
                "selected_field": "selected_configs",
                "select_all_id": "select-all-configs",
                "checkbox_class": "price-config-checkbox",
                "update_label": "Оновити ціни",
                "test_label": "Тестувати парсер",
                "title": "Групові дії",
                "description": "Виберіть потрібні конфігурації нижче та запустіть дію.",
            }
        if self.section.slug == "supplier-feeds":
            return {
                "url": reverse("custom_admin:supplier_feed_bulk_action"),
                "selected_field": "selected_feeds",
                "select_all_id": "select-all-feeds",
                "checkbox_class": "supplier-feed-checkbox",
                "update_label": "Оновити ціни",
                "test_label": "Перевірити фід",
                "title": "Групові дії",
                "description": "Виберіть потрібні фіди, щоб оновити ціни або протестувати парсер.",
            }
        return None


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
        if self.section.read_only:
            messages.info(self.request, _("Цей розділ доступний лише для перегляду."))
            return redirect(self.get_success_url())
        with transaction.atomic():
            self.object = form.save()
        self._after_object_saved()
        return self._redirect_after_save()

    def form_invalid(self, form):
        messages.error(self.request, _("Будь ласка, виправте помилки у формі."))
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("custom_admin:list", args=[self.section.slug])

    def _after_object_saved(self):
        obj = getattr(self, "object", None)
        if not obj:
            return
        label = getattr(obj, "name", None) or getattr(obj, "title", None) or str(obj)
        edit_url = reverse("custom_admin:edit", args=[self.section.slug, obj.pk])
        message = mark_safe(
            f'Зміни успішно збережено для '
            f'<a href="{edit_url}" class="text-brown-700 underline hover:text-brown-900">{escape(label)}</a>.'
        )
        messages.success(self.request, message)

    def _redirect_after_save(self):
        if "save_continue" in self.request.POST:
            return redirect("custom_admin:edit", section_slug=self.section.slug, pk=self.object.pk)
        return redirect(self.get_success_url())


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
        if self.section.read_only and request.method.lower() != "get":
            messages.info(request, _("Цей розділ доступний лише для перегляду."))
            return redirect("custom_admin:edit", section_slug=self.section.slug, pk=kwargs.get("pk"))
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
            self.object = form.save()
            for formset in formsets.values():
                formset.instance = self.object
                formset.save()
        self._after_object_saved()
        return self._redirect_after_save()

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


class SectionDetailView(SectionMixin, DetailView):
    template_name = "custom_admin/form.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.section.read_only:
            return redirect("custom_admin:edit", section_slug=self.section.slug, pk=kwargs.get("pk"))
        if not self.section.form_class:
            raise Http404("Детальний перегляд недоступний.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.section.model.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.section.form_class(instance=self.object)
        context.update(
            {
                "form": form,
                "object": self.object,
                "section_read_only": True,
                "list_url": reverse("custom_admin:list", args=[self.section.slug]),
            }
        )
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


@login_required
@require_POST
def generate_iban_invoice(request, pk: int):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    order = get_object_or_404(Order, pk=pk)
    redirect_url = reverse("custom_admin:edit", kwargs={"section_slug": "orders", "pk": order.pk})

    if order.payment_type != "iban":
        messages.error(request, "Це замовлення не потребує рахунку IBAN.")
        return redirect(redirect_url)

    try:
        pdf_path, pdf_url = generate_and_upload_invoice(order)
        order.mark_invoice_generated(pdf_path, pdf_url)
        order.iban_invoice_generated = True
        order.save(update_fields=["iban_invoice_generated"])
        messages.success(request, "Рахунок IBAN згенеровано успішно.")
    except Exception as exc:
        messages.error(request, f"Не вдалося згенерувати рахунок: {exc}")

    return redirect(redirect_url)


@login_required
@require_POST
def update_price_config_prices(request, pk: int):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    config = get_object_or_404(GoogleSheetConfig, pk=pk)
    redirect_url = reverse("custom_admin:list", kwargs={"section_slug": "price-configs"})

    try:
        updater = GoogleSheetsPriceUpdater(config)
        result = updater.update_prices()
    except Exception as exc:
        messages.error(request, f"Не вдалося оновити ціни: {exc}")
        return redirect(redirect_url)

    if result.get("success"):
        messages.success(
            request,
            f"Оновлено {result.get('updated_count', 0)} товарів з {result.get('processed_count', 0)}.",
        )
    else:
        messages.error(request, f"Помилка оновлення: {result.get('error', 'Невідома помилка')}")
    return redirect(redirect_url)


@login_required
@require_POST
def test_price_config_parse(request, pk: int):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    config = get_object_or_404(GoogleSheetConfig, pk=pk)
    redirect_url = reverse("custom_admin:list", kwargs={"section_slug": "price-configs"})

    try:
        updater = GoogleSheetsPriceUpdater(config)
        result = updater.test_parse()
    except Exception as exc:
        messages.error(request, f"Не вдалося виконати тестовий парсинг: {exc}")
        return redirect(redirect_url)

    if result.get("success"):
        messages.success(
            request,
            f"Тестовий парсинг успішний. Знайдено {len(result.get('data', []))} рядків.",
        )
    else:
        messages.error(request, f"Помилка тестового парсингу: {result.get('error', 'Невідома помилка')}")
    return redirect(redirect_url)


@login_required
@require_POST
def price_config_bulk_action(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    action = request.POST.get("action")
    selected_ids = request.POST.getlist("selected_configs")
    redirect_url = reverse("custom_admin:list", kwargs={"section_slug": "price-configs"})

    if not selected_ids:
        messages.warning(request, "Будь ласка, виберіть хоча б одну конфігурацію.")
        return redirect(redirect_url)

    configs = GoogleSheetConfig.objects.filter(pk__in=selected_ids)
    if not configs.exists():
        messages.error(request, "Обрані конфігурації не знайдено.")
        return redirect(redirect_url)

    success_count = 0
    errors: list[str] = []
    action_label = "оновлення" if action == "update" else "тестування"

    for config in configs:
        try:
            updater = GoogleSheetsPriceUpdater(config)
            if action == "update":
                result = updater.update_prices()
            elif action == "test":
                result = updater.test_parse()
            else:
                messages.error(request, "Невідома дія.")
                return redirect(redirect_url)

            if result.get("success"):
                success_count += 1
            else:
                errors.append(f"{config.name}: {result.get('error', 'невідома помилка')}")
        except Exception as exc:
            errors.append(f"{config.name}: {exc}")

    if success_count:
        messages.success(request, f"Успішно виконано {action_label} для {success_count} конфігурацій.")
    if errors:
        preview = " ; ".join(errors[:3])
        if len(errors) > 3:
            preview += " ..."
        messages.error(request, preview)

    return redirect(redirect_url)


@login_required
@require_POST
def update_supplier_feed_prices(request, pk: int):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    config = get_object_or_404(SupplierFeedConfig, pk=pk)
    redirect_url = reverse("custom_admin:list", kwargs={"section_slug": "supplier-feeds"})

    try:
        updater = SupplierFeedPriceUpdater(config)
        result = updater.update_prices()
    except Exception as exc:
        messages.error(request, f"Не вдалося оновити ціни: {exc}")
        return redirect(redirect_url)

    if result.get("success"):
        messages.success(
            request,
            "Оновлено {updated} товарів (збігів {matched}).".format(
                updated=result.get("items_updated", 0),
                matched=result.get("items_matched", 0),
            ),
        )
    else:
        messages.error(request, f"Помилка оновлення: {result.get('error', 'Невідома помилка')}")
    return redirect(redirect_url)


@login_required
@require_POST
def test_supplier_feed_parse(request, pk: int):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    config = get_object_or_404(SupplierFeedConfig, pk=pk)
    redirect_url = reverse("custom_admin:list", kwargs={"section_slug": "supplier-feeds"})

    try:
        updater = SupplierFeedPriceUpdater(config)
        result = updater.test_parse()
    except Exception as exc:
        messages.error(request, f"Не вдалося виконати тестовий парсинг: {exc}")
        return redirect(redirect_url)

    if result.get("success"):
        messages.success(
            request,
            f"Тестовий парсинг успішний. Знайдено {result.get('offers_total', 0)} оферів.",
        )
    else:
        messages.error(request, f"Помилка тестового парсингу: {result.get('error', 'Невідома помилка')}")
    return redirect(redirect_url)


@login_required
@require_POST
def supplier_feed_bulk_action(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    action = request.POST.get("action")
    selected_ids = request.POST.getlist("selected_feeds")
    redirect_url = reverse("custom_admin:list", kwargs={"section_slug": "supplier-feeds"})

    if not selected_ids:
        messages.warning(request, "Будь ласка, виберіть хоча б один фід.")
        return redirect(redirect_url)

    configs = SupplierFeedConfig.objects.filter(pk__in=selected_ids)
    if not configs.exists():
        messages.error(request, "Обрані фіди не знайдено.")
        return redirect(redirect_url)

    success_count = 0
    errors: list[str] = []
    action_label = "оновлення" if action == "update" else "тестування"

    for config in configs:
        try:
            updater = SupplierFeedPriceUpdater(config)
            if action == "update":
                result = updater.update_prices()
            elif action == "test":
                result = updater.test_parse()
            else:
                messages.error(request, "Невідома дія.")
                return redirect(redirect_url)

            if result.get("success"):
                success_count += 1
            else:
                errors.append(f"{config.name}: {result.get('error', 'невідома помилка')}")
        except Exception as exc:
            errors.append(f"{config.name}: {exc}")

    total = configs.count()
    if errors:
        messages.warning(
            request,
            f"{action_label.capitalize()} виконано частково — успішно {success_count} з {total}.",
        )
        preview = " ; ".join(errors[:3])
        if len(errors) > 3:
            preview += " ..."
        messages.error(request, preview)
    else:
        messages.success(
            request,
            f"{action_label.capitalize()} успішно для {success_count} конфігурацій.",
        )
    return redirect(redirect_url)


def redirect_to_dashboard(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("custom_admin:dashboard")
    return redirect("custom_admin:login")
