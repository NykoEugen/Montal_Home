from __future__ import annotations

from functools import cached_property
from typing import Any, Optional

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import FieldError
from django.db import close_old_connections, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, DetailView, ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView

from checkout.invoice import generate_and_upload_invoice
from checkout.models import Order
from price_parser.andersen_scraper import CATALOG_CONFIGS as ANDERSEN_CATALOG_CONFIGS
from price_parser.management.commands.import_eurosof import (
    CATALOG_CONFIGS as EUROSOF_CATALOG_CONFIGS,
)
from price_parser.management.commands.import_eurosof import (
    DEFAULT_XLSX as EUROSOF_DEFAULT_XLSX,
)
from price_parser.models import GoogleSheetConfig, SupplierFeedConfig, SupplierWebConfig
from price_parser.services import (
    GoogleSheetsPriceUpdater,
    SupplierFeedPriceUpdater,
    SupplierWebPriceUpdater,
)
from sub_categories.models import SubCategory

from .forms import (
    FurnitureCustomOptionFormSet,
    FurnitureImageFormSet,
    FurnitureParameterFormSet,
    FurnitureSizeVariantFormSet,
    FurnitureVariantImageFormSet,
    OrderItemFormSet,
)
from .registry import AdminSection, registry
from .services import start_job


def _bulk_run(configs, updater_cls, method_name: str) -> dict:
    """Run updater_cls(config).<method_name>() for each config, aggregating results."""
    success_count = 0
    errors: list[str] = []
    for config in configs:
        try:
            result = getattr(updater_cls(config), method_name)()
            if result.get("success"):
                success_count += 1
            else:
                errors.append(
                    f"{config.name}: {result.get('error', 'невідома помилка')}"
                )
        except Exception as exc:
            errors.append(f"{config.name}: {exc}")
    return {
        "success": True,
        "updated_configs": success_count,
        "total_configs": configs.count(),
        "errors": errors,
    }


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
                "stock_choices": getattr(
                    self.section.model, "STOCK_STATUS_CHOICES", []
                ),
                "selected_stock_status": self.request.GET.get("stock_status", ""),
            }
            context["furniture_bulk_edit_url"] = reverse(
                "custom_admin:furniture_bulk_edit"
            )
            context["furniture_variants_url"] = reverse(
                "custom_admin:furniture_variants"
            )
            context["furniture_palettes_url"] = reverse(
                "custom_admin:furniture_palettes"
            )
            context["column_span"] += 1
        if self.section.slug == "fabric-color-palettes":
            context["palette_colors_bulk_add_url"] = reverse(
                "custom_admin:palette_colors_bulk_add"
            )
            context["palette_colors_bulk_edit_base_url"] = reverse(
                "custom_admin:palette_colors_bulk_edit"
            )
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
        if self.section.slug == "supplier-web":
            return {
                "url": reverse("custom_admin:supplier_web_bulk_action"),
                "selected_field": "selected_web_configs",
                "select_all_id": "select-all-web-configs",
                "checkbox_class": "supplier-web-config-checkbox",
                "update_label": "Оновити ціни",
                "test_label": "Тестувати парсер",
                "title": "Групові дії",
                "description": "Виберіть потрібні веб-конфігурації для оновлення цін або тестового запуску.",
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
            f"Зміни успішно збережено для "
            f'<a href="{edit_url}" class="text-brown-700 underline hover:text-brown-900">{escape(label)}</a>.'
        )
        messages.success(self.request, message)

    def _redirect_after_save(self):
        if "save_continue" in self.request.POST:
            return redirect(
                "custom_admin:edit", section_slug=self.section.slug, pk=self.object.pk
            )
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
            return redirect(
                "custom_admin:edit", section_slug=self.section.slug, pk=kwargs.get("pk")
            )
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
            return redirect(
                "custom_admin:edit", section_slug=self.section.slug, pk=kwargs.get("pk")
            )
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
    redirect_url = reverse(
        "custom_admin:edit", kwargs={"section_slug": "orders", "pk": order.pk}
    )

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
    redirect_url = reverse(
        "custom_admin:list", kwargs={"section_slug": "price-configs"}
    )

    def run():
        return GoogleSheetsPriceUpdater(config).update_prices()

    job = start_job(request, "google_sheet", "update_prices", run, catalog_key=str(pk))
    if job is None:
        messages.warning(request, f"Оновлення «{config.name}» вже виконується.")
    else:
        messages.info(request, f"Запущено оновлення «{config.name}» у фоні.")
    return redirect(redirect_url)


@login_required
@require_POST
def test_price_config_parse(request, pk: int):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    config = get_object_or_404(GoogleSheetConfig, pk=pk)
    redirect_url = reverse(
        "custom_admin:list", kwargs={"section_slug": "price-configs"}
    )

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
        messages.error(
            request,
            f"Помилка тестового парсингу: {result.get('error', 'Невідома помилка')}",
        )
    return redirect(redirect_url)


@login_required
@require_POST
def price_config_bulk_action(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    action = request.POST.get("action")
    selected_ids = request.POST.getlist("selected_configs")
    redirect_url = reverse(
        "custom_admin:list", kwargs={"section_slug": "price-configs"}
    )

    if not selected_ids:
        messages.warning(request, "Будь ласка, виберіть хоча б одну конфігурацію.")
        return redirect(redirect_url)

    configs = GoogleSheetConfig.objects.filter(pk__in=selected_ids)
    if not configs.exists():
        messages.error(request, "Обрані конфігурації не знайдено.")
        return redirect(redirect_url)

    if action not in ("update", "test"):
        messages.error(request, "Невідома дія.")
        return redirect(redirect_url)

    if action == "update":
        config_ids = sorted(configs.values_list("pk", flat=True))
        catalog_key = "bulk:" + ",".join(str(i) for i in config_ids)

        def run():
            return _bulk_run(configs, GoogleSheetsPriceUpdater, "update_prices")

        job = start_job(
            request, "google_sheet", "update_prices", run, catalog_key=catalog_key
        )
        if job is None:
            messages.warning(request, "Масове оновлення вже виконується.")
        else:
            messages.info(
                request,
                f"Запущено масове оновлення для {configs.count()} конфігурацій у фоні.",
            )
        return redirect(redirect_url)

    success_count = 0
    errors: list[str] = []
    for config in configs:
        try:
            result = GoogleSheetsPriceUpdater(config).test_parse()
            if result.get("success"):
                success_count += 1
            else:
                errors.append(
                    f"{config.name}: {result.get('error', 'невідома помилка')}"
                )
        except Exception as exc:
            errors.append(f"{config.name}: {exc}")

    if success_count:
        messages.success(
            request,
            f"Успішно виконано тестування для {success_count} конфігурацій.",
        )
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
    redirect_url = reverse(
        "custom_admin:list", kwargs={"section_slug": "supplier-feeds"}
    )

    def run():
        return SupplierFeedPriceUpdater(config).update_prices()

    job = start_job(request, "supplier_feed", "update_prices", run, catalog_key=str(pk))
    if job is None:
        messages.warning(request, f"Оновлення «{config.name}» вже виконується.")
    else:
        messages.info(request, f"Запущено оновлення «{config.name}» у фоні.")
    return redirect(redirect_url)


@login_required
@require_POST
def test_supplier_feed_parse(request, pk: int):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    config = get_object_or_404(SupplierFeedConfig, pk=pk)
    redirect_url = reverse(
        "custom_admin:list", kwargs={"section_slug": "supplier-feeds"}
    )

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
        messages.error(
            request,
            f"Помилка тестового парсингу: {result.get('error', 'Невідома помилка')}",
        )
    return redirect(redirect_url)


@login_required
@require_POST
def supplier_feed_bulk_action(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    action = request.POST.get("action")
    selected_ids = request.POST.getlist("selected_feeds")
    redirect_url = reverse(
        "custom_admin:list", kwargs={"section_slug": "supplier-feeds"}
    )

    if not selected_ids:
        messages.warning(request, "Будь ласка, виберіть хоча б один фід.")
        return redirect(redirect_url)

    configs = SupplierFeedConfig.objects.filter(pk__in=selected_ids)
    if not configs.exists():
        messages.error(request, "Обрані фіди не знайдено.")
        return redirect(redirect_url)

    if action not in ("update", "test"):
        messages.error(request, "Невідома дія.")
        return redirect(redirect_url)

    if action == "update":
        config_ids = sorted(configs.values_list("pk", flat=True))
        catalog_key = "bulk:" + ",".join(str(i) for i in config_ids)

        def run():
            return _bulk_run(configs, SupplierFeedPriceUpdater, "update_prices")

        job = start_job(
            request, "supplier_feed", "update_prices", run, catalog_key=catalog_key
        )
        if job is None:
            messages.warning(request, "Масове оновлення вже виконується.")
        else:
            messages.info(
                request,
                f"Запущено масове оновлення для {configs.count()} фідів у фоні.",
            )
        return redirect(redirect_url)

    success_count = 0
    errors: list[str] = []
    for config in configs:
        try:
            result = SupplierFeedPriceUpdater(config).test_parse()
            if result.get("success"):
                success_count += 1
            else:
                errors.append(
                    f"{config.name}: {result.get('error', 'невідома помилка')}"
                )
        except Exception as exc:
            errors.append(f"{config.name}: {exc}")

    if success_count:
        messages.success(
            request,
            f"Успішно виконано тестування для {success_count} фідів.",
        )
    if errors:
        preview = " ; ".join(errors[:3])
        if len(errors) > 3:
            preview += " ..."
        messages.error(request, preview)
    return redirect(redirect_url)


@login_required
@require_POST
def update_supplier_web_prices(request, pk: int):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    config = get_object_or_404(SupplierWebConfig, pk=pk)
    redirect_url = reverse("custom_admin:list", kwargs={"section_slug": "supplier-web"})

    def run():
        return SupplierWebPriceUpdater(config).update_prices()

    job = start_job(request, "supplier_web", "update_prices", run, catalog_key=str(pk))
    if job is None:
        messages.warning(request, f"Оновлення «{config.name}» вже виконується.")
    else:
        messages.info(request, f"Запущено оновлення «{config.name}» у фоні.")
    return redirect(redirect_url)


@login_required
@require_POST
def test_supplier_web_parse(request, pk: int):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    config = get_object_or_404(SupplierWebConfig, pk=pk)
    redirect_url = reverse("custom_admin:list", kwargs={"section_slug": "supplier-web"})

    try:
        updater = SupplierWebPriceUpdater(config)
        result = updater.test_parse()
    except Exception as exc:
        messages.error(request, f"Не вдалося виконати тестовий парсинг: {exc}")
        return redirect(redirect_url)
    finally:
        close_old_connections()

    if result.get("success"):
        messages.success(
            request,
            f"Тестовий парсинг успішний. Зібрано URL: {result.get('urls_total', 0)}.",
        )
    else:
        messages.error(
            request,
            f"Помилка тестового парсингу: {result.get('error', 'Невідома помилка')}",
        )
    return redirect(redirect_url)


@login_required
@require_POST
def supplier_web_bulk_action(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    action = request.POST.get("action")
    selected_ids = request.POST.getlist("selected_web_configs")
    redirect_url = reverse("custom_admin:list", kwargs={"section_slug": "supplier-web"})

    if not selected_ids:
        messages.warning(request, "Будь ласка, виберіть хоча б одну веб-конфігурацію.")
        return redirect(redirect_url)

    configs = SupplierWebConfig.objects.filter(pk__in=selected_ids)
    if not configs.exists():
        messages.error(request, "Обрані веб-конфігурації не знайдено.")
        return redirect(redirect_url)

    if action not in ("update", "test"):
        messages.error(request, "Невідома дія.")
        return redirect(redirect_url)

    if action == "update":
        config_ids = sorted(configs.values_list("pk", flat=True))
        catalog_key = "bulk:" + ",".join(str(i) for i in config_ids)

        def run():
            return _bulk_run(configs, SupplierWebPriceUpdater, "update_prices")

        job = start_job(
            request, "supplier_web", "update_prices", run, catalog_key=catalog_key
        )
        if job is None:
            messages.warning(request, "Масове оновлення вже виконується.")
        else:
            messages.info(
                request,
                f"Запущено масове оновлення для {configs.count()} веб-конфігурацій у фоні.",
            )
        return redirect(redirect_url)

    success_count = 0
    errors: list[str] = []
    for config in configs:
        try:
            result = SupplierWebPriceUpdater(config).test_parse()
            if result.get("success"):
                success_count += 1
            else:
                errors.append(
                    f"{config.name}: {result.get('error', 'невідома помилка')}"
                )
        except Exception as exc:
            errors.append(f"{config.name}: {exc}")
        finally:
            close_old_connections()

    if success_count:
        messages.success(
            request,
            f"Успішно виконано тестування для {success_count} веб-конфігурацій.",
        )
    if errors:
        preview = " ; ".join(errors[:3])
        if len(errors) > 3:
            preview += " ..."
        messages.error(request, preview)
    return redirect(redirect_url)


@login_required
def furniture_bulk_edit(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from furniture.models import Furniture
    from params.models import FurnitureParameter

    if request.method != "POST" or "selected_furniture" not in request.POST:
        return redirect("custom_admin:list", section_slug="furniture")

    selected_ids = request.POST.getlist("selected_furniture")
    if not selected_ids:
        messages.warning(request, "Будь ласка, виберіть хоча б один товар.")
        return redirect("custom_admin:list", section_slug="furniture")

    furniture_qs = (
        Furniture.objects.filter(pk__in=selected_ids)
        .prefetch_related("parameters__parameter")
        .select_related("sub_category")
        .order_by("name")
    )
    sub_categories = SubCategory.objects.order_by("name")

    return render(
        request,
        "custom_admin/furniture_bulk_edit.html",
        {
            "furniture_list": furniture_qs,
            "selected_ids": selected_ids,
            "sub_categories": sub_categories,
            "sections": list(registry.all()),
        },
    )


@login_required
@require_POST
def furniture_bulk_edit_apply(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from furniture.models import Furniture
    from params.models import FurnitureParameter

    selected_ids = request.POST.getlist("selected_ids")
    furniture_qs = Furniture.objects.filter(pk__in=selected_ids).prefetch_related(
        "parameters"
    )

    updated_count = 0

    with transaction.atomic():
        for furniture in furniture_qs:
            fid = str(furniture.pk)
            changed = False

            new_sub_cat_id = request.POST.get(f"sub_category_{fid}")
            if new_sub_cat_id:
                try:
                    new_sub_cat_id = int(new_sub_cat_id)
                    if furniture.sub_category_id != new_sub_cat_id:
                        furniture.sub_category_id = new_sub_cat_id
                        changed = True
                except (ValueError, TypeError):
                    pass

            if changed:
                furniture.save(update_fields=["sub_category"])
                updated_count += 1

            for fp in furniture.parameters.all():
                pid = str(fp.pk)
                if request.POST.get(f"param_{fid}_{pid}_delete"):
                    fp.delete()
                    continue
                new_value = request.POST.get(f"param_{fid}_{pid}_value")
                if new_value is not None and new_value.strip() != fp.value:
                    fp.value = new_value.strip()
                    fp.save(update_fields=["value"])

    messages.success(request, f"Зміни збережено для {len(selected_ids)} товарів.")
    return redirect("custom_admin:list", section_slug="furniture")


@login_required
def furniture_palettes(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from django.core.paginator import Paginator

    from fabric_category.models import FabricColorPalette
    from furniture.models import Furniture

    palettes = FabricColorPalette.objects.filter(is_active=True).order_by("name")
    sub_categories = SubCategory.objects.order_by("name")

    if request.method == "POST":
        action = request.POST.get("action", "")
        selected_ids = request.POST.getlist("selected_furniture")
        palette_id_raw = request.POST.get("palette_id", "").strip()
        get_params = request.POST.get("get_params", "")

        if not selected_ids:
            messages.warning(request, "Виберіть хоча б один товар.")
        elif action in ("add_palette", "remove_palette") and not palette_id_raw:
            messages.warning(request, "Виберіть палітру.")
        else:
            qs = Furniture.objects.filter(pk__in=selected_ids)
            count = qs.count()

            if action == "add_palette":
                try:
                    palette = FabricColorPalette.objects.get(pk=int(palette_id_raw))
                    for f in qs:
                        f.color_palettes.add(palette)
                    messages.success(
                        request, f"Палітру «{palette.name}» додано до {count} товарів."
                    )
                except (FabricColorPalette.DoesNotExist, ValueError):
                    messages.error(request, "Палітру не знайдено.")

            elif action == "remove_palette":
                try:
                    palette = FabricColorPalette.objects.get(pk=int(palette_id_raw))
                    for f in qs:
                        f.color_palettes.remove(palette)
                    messages.success(
                        request, f"Палітру «{palette.name}» видалено з {count} товарів."
                    )
                except (FabricColorPalette.DoesNotExist, ValueError):
                    messages.error(request, "Палітру не знайдено.")

            elif action == "clear_promo":
                for f in qs:
                    if f.is_promotional:
                        f.is_promotional = False
                        f.promotional_price = None
                        f.sale_end_date = None
                        f.save(
                            update_fields=[
                                "is_promotional",
                                "promotional_price",
                                "sale_end_date",
                            ]
                        )
                messages.success(request, f"Акційний флаг знято з {count} товарів.")

        redirect_url = request.path
        if get_params:
            redirect_url += "?" + get_params
        return redirect(redirect_url)

    qs = (
        Furniture.objects.prefetch_related("color_palettes")
        .select_related("sub_category")
        .order_by("name")
    )

    search = request.GET.get("q", "").strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(article_code__icontains=search))

    sub_cat_id = request.GET.get("sub_category", "").strip()
    if sub_cat_id:
        try:
            qs = qs.filter(sub_category_id=int(sub_cat_id))
        except ValueError:
            pass

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    querydict = request.GET.copy()
    querydict.pop("page", None)
    current_query_string = querydict.urlencode()

    return render(
        request,
        "custom_admin/furniture_palettes.html",
        {
            "sections": list(registry.all()),
            "palettes": palettes,
            "sub_categories": sub_categories,
            "page_obj": page_obj,
            "is_paginated": page_obj.has_other_pages(),
            "search_query": search,
            "selected_sub_category": sub_cat_id,
            "current_query_string": current_query_string,
        },
    )


def redirect_to_dashboard(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("custom_admin:dashboard")
    return redirect("custom_admin:login")


# ── Variant group bulk editor ─────────────────────────────────────────────────


@login_required
def furniture_variants(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from collections import defaultdict

    from furniture.models import Furniture

    sub_categories = SubCategory.objects.order_by("name")
    selected_sub_cat_id = request.GET.get("sub_category") or request.POST.get(
        "sub_category"
    )

    furniture_qs = None
    if selected_sub_cat_id:
        furniture_qs = (
            Furniture.objects.filter(sub_category_id=selected_sub_cat_id)
            .select_related("variant_group_leader")
            .order_by("base_model_name", "name")
        )

    if request.method == "POST" and furniture_qs is not None:
        with transaction.atomic():
            # Collect updates from form
            updates: dict[int, dict] = {}
            for f in furniture_qs:
                fid = str(f.pk)
                bname = request.POST.get(f"base_model_name_{fid}", "").strip()
                label = request.POST.get(f"variant_label_{fid}", "").strip()
                new_name = request.POST.get(f"name_{fid}", "").strip()
                updates[f.pk] = {
                    "base_model_name": bname,
                    "variant_label": label,
                    "name": new_name,
                    "obj": f,
                }

            # Group by base_model_name
            groups: dict[str, list[int]] = defaultdict(list)
            for fid, data in updates.items():
                bname = data["base_model_name"]
                if bname:
                    groups[bname].append(fid)

            # Assign variant_group_leader per group
            leader_map: dict[int, int | None] = {}  # fid → leader_id or None
            for bname, fids in groups.items():
                sorted_fids = sorted(fids)
                leader_id = sorted_fids[0]
                leader_map[leader_id] = None  # leader points to nobody
                for fid in sorted_fids[1:]:
                    leader_map[fid] = leader_id

            # Products not in any group → clear leader
            for fid in updates:
                if fid not in leader_map:
                    leader_map[fid] = None

            # Save all
            for fid, data in updates.items():
                fields = dict(
                    base_model_name=data["base_model_name"],
                    variant_label=data["variant_label"],
                    variant_group_leader_id=leader_map[fid],
                )
                if data["name"]:
                    fields["name"] = data["name"]
                Furniture.objects.filter(pk=fid).update(**fields)

        messages.success(request, "Варіантні групи збережено.")
        return redirect(f"{request.path}?sub_category={selected_sub_cat_id}")

    # Build grouped display for GET
    grouped: list[dict] = []
    if furniture_qs is not None:
        by_group: dict[str, list] = defaultdict(list)
        standalone: list = []
        for f in furniture_qs:
            if f.base_model_name:
                by_group[f.base_model_name].append(f)
            else:
                standalone.append(f)
        for bname, items in sorted(by_group.items()):
            grouped.append({"group_name": bname, "items": items})
        if standalone:
            grouped.append({"group_name": "", "items": standalone})

    return render(
        request,
        "custom_admin/furniture_variants.html",
        {
            "sub_categories": sub_categories,
            "selected_sub_cat_id": (
                int(selected_sub_cat_id) if selected_sub_cat_id else None
            ),
            "grouped": grouped,
            "sections": list(registry.all()),
        },
    )


# ── Catalog updates hub (Evrodim / Andersen / Kreslalux / Eurosof) ──────────


@login_required
def catalog_updates_page(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from furniture.models import Furniture

    from .models import CatalogUpdateJob

    def _jobs(supplier: str):
        return list(CatalogUpdateJob.objects.filter(supplier=supplier)[:5])

    def _running(supplier: str, action: str, catalog_key: str = "") -> bool:
        return CatalogUpdateJob.objects.filter(
            supplier=supplier, action=action, catalog_key=catalog_key, status="running"
        ).exists()

    context = {
        "sections": list(registry.all()),
        "evrodim_count": Furniture.objects.filter(
            sub_category__slug="stoly-evrodim"
        ).count(),
        "evrodim_jobs": _jobs("evrodim"),
        "evrodim_prices_running": _running("evrodim", "update_prices"),
        "evrodim_params_running": _running("evrodim", "update_params"),
        "andersen_catalogs": list(ANDERSEN_CATALOG_CONFIGS.items()),
        "andersen_jobs": _jobs("andersen"),
        "andersen_prices_running": _running("andersen", "update_prices", "all"),
        "andersen_import_running": _running("andersen", "import", "all"),
        "kreslalux_count": Furniture.objects.filter(
            sub_category__slug="ortopedichni-krisla"
        ).count(),
        "kreslalux_jobs": _jobs("kreslalux"),
        "kreslalux_prices_running": _running("kreslalux", "update_prices"),
        "kreslalux_import_running": _running("kreslalux", "import"),
        "eurosof_catalogs": list(EUROSOF_CATALOG_CONFIGS.items()),
        "eurosof_jobs": _jobs("eurosof"),
        "eurosof_prices_running": _running("eurosof", "update_prices", "all"),
        "eurosof_import_running": _running("eurosof", "import", "all"),
        "feed_jobs": list(
            CatalogUpdateJob.objects.filter(
                supplier__in=["google_sheet", "supplier_feed", "supplier_web"]
            )[:8]
        ),
        "has_running_jobs": CatalogUpdateJob.objects.filter(status="running").exists(),
    }
    return render(request, "custom_admin/catalog_updates.html", context)


@login_required
@require_POST
def evrodim_update_prices(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from price_parser.evrodim_scraper import EvrodimScraper

    def run():
        return EvrodimScraper().update_prices(subcategory_slug="stoly-evrodim")

    job = start_job(request, "evrodim", "update_prices", run)
    if job is None:
        messages.warning(request, "Оновлення цін Evrodim вже виконується.")
    else:
        messages.info(
            request,
            "Запущено оновлення цін Evrodim у фоні — статус з'явиться нижче за кілька хвилин.",
        )
    return redirect("custom_admin:catalog_updates")


@login_required
@require_POST
def evrodim_update_params(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from price_parser.evrodim_scraper import EvrodimScraper

    def run():
        return EvrodimScraper().update_params(subcategory_slug="stoly-evrodim")

    job = start_job(request, "evrodim", "update_params", run)
    if job is None:
        messages.warning(request, "Оновлення характеристик Evrodim вже виконується.")
    else:
        messages.info(
            request,
            "Запущено оновлення характеристик Evrodim у фоні — статус з'явиться нижче за кілька хвилин.",
        )
    return redirect("custom_admin:catalog_updates")


# ── Andersen scraper views ───────────────────────────────────────────────────


@login_required
@require_POST
def andersen_update_prices(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from price_parser.andersen_scraper import AndersenScraper

    catalog_arg = request.POST.get("catalog", "all")
    catalogs = (
        list(ANDERSEN_CATALOG_CONFIGS.keys()) if catalog_arg == "all" else [catalog_arg]
    )

    def run():
        scraper = AndersenScraper()
        totals = {"checked": 0, "updated": 0, "not_found": 0, "errors": []}
        for catalog_key in catalogs:
            result = scraper.update_prices(catalog_key)
            if not result.get("success", True):
                totals["errors"].append(f"{catalog_key}: {result.get('error')}")
                continue
            for key in ("checked", "updated", "not_found"):
                totals[key] += result.get(key, 0)
            totals["errors"].extend(result.get("errors", []))
        return totals

    job = start_job(request, "andersen", "update_prices", run, catalog_key=catalog_arg)
    if job is None:
        messages.warning(request, "Оновлення цін Andersen вже виконується.")
    else:
        messages.info(
            request,
            "Запущено оновлення цін Andersen у фоні — статус з'явиться нижче за кілька хвилин.",
        )
    return redirect("custom_admin:catalog_updates")


@login_required
@require_POST
def andersen_run_import(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from price_parser.andersen_scraper import AndersenScraper

    catalog_arg = request.POST.get("catalog", "all")
    catalogs = (
        list(ANDERSEN_CATALOG_CONFIGS.keys()) if catalog_arg == "all" else [catalog_arg]
    )

    def run():
        scraper = AndersenScraper()
        totals = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
        for catalog_key in catalogs:
            result = scraper.run_import(catalog_key=catalog_key, dry_run=False)
            if not result.get("success", True):
                totals["errors"].append(f"{catalog_key}: {result.get('error')}")
                continue
            for key in ("created", "updated", "skipped"):
                totals[key] += result.get(key, 0)
            totals["errors"].extend(result.get("errors", []))
        return totals

    job = start_job(request, "andersen", "import", run, catalog_key=catalog_arg)
    if job is None:
        messages.warning(request, "Імпорт Andersen вже виконується.")
    else:
        messages.info(
            request,
            "Запущено імпорт Andersen у фоні — статус з'явиться нижче за кілька хвилин.",
        )
    return redirect("custom_admin:catalog_updates")


# ── Kreslalux scraper views ───────────────────────────────────────────────────


@login_required
@require_POST
def kreslalux_update_prices(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from price_parser.kreslalux_scraper import KreslaluxScraper

    def run():
        return KreslaluxScraper().update_prices()

    job = start_job(request, "kreslalux", "update_prices", run)
    if job is None:
        messages.warning(request, "Оновлення цін Kreslalux вже виконується.")
    else:
        messages.info(
            request,
            "Запущено оновлення цін Kreslalux у фоні — статус з'явиться нижче за кілька хвилин.",
        )
    return redirect("custom_admin:catalog_updates")


@login_required
@require_POST
def kreslalux_run_import(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from price_parser.kreslalux_scraper import KreslaluxScraper

    def run():
        return KreslaluxScraper().run_import(
            dry_run=False, subcategory_slug="ortopedichni-krisla"
        )

    job = start_job(request, "kreslalux", "import", run)
    if job is None:
        messages.warning(request, "Імпорт Kreslalux вже виконується.")
    else:
        messages.info(
            request,
            "Запущено імпорт Kreslalux у фоні — статус з'явиться нижче за кілька хвилин.",
        )
    return redirect("custom_admin:catalog_updates")


# ── Eurosof scraper views ────────────────────────────────────────────────────


@login_required
@require_POST
def eurosof_run_import(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    import os

    from price_parser.eurosof_scraper import EurosofImporter

    catalog_arg = request.POST.get("catalog", "all")
    update_prices_only = request.POST.get("update_prices_only") == "on"
    catalogs = (
        list(EUROSOF_CATALOG_CONFIGS.values())
        if catalog_arg == "all"
        else [EUROSOF_CATALOG_CONFIGS[catalog_arg]]
    )
    action = "update_prices" if update_prices_only else "import"

    if not os.path.exists(EUROSOF_DEFAULT_XLSX):
        messages.error(request, f"Excel-файл не знайдено: {EUROSOF_DEFAULT_XLSX}")
        return redirect("custom_admin:catalog_updates")

    def run():
        importer = EurosofImporter(xlsx_path=EUROSOF_DEFAULT_XLSX)
        totals = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "unmatched": 0,
            "errors": [],
        }
        for cfg in catalogs:
            result = importer.run(
                catalog_urls=[cfg["url"]],
                subcategory_name=cfg["subcategory_name"],
                subcategory_slug=cfg["subcategory_slug"],
                category_name=cfg["category_name"],
                corner=cfg.get("corner", False),
                bed=cfg.get("bed", False),
                dry_run=False,
                update_prices=update_prices_only,
            )
            for key in ("created", "updated", "skipped", "unmatched"):
                totals[key] += result.get(key, 0)
            totals["errors"].extend(result.get("errors", []))
        return totals

    job = start_job(request, "eurosof", action, run, catalog_key=catalog_arg)
    if job is None:
        messages.warning(request, "Ця операція Eurosof вже виконується.")
    else:
        messages.info(
            request, "Запущено у фоні — статус з'явиться нижче за кілька хвилин."
        )
    return redirect("custom_admin:catalog_updates")


@login_required
def palette_colors_bulk_add(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from fabric_category.models import FabricColor, FabricColorPalette

    palettes = FabricColorPalette.objects.filter(is_active=True).order_by("name")
    errors: list[str] = []
    saved_count = 0

    if request.method == "POST":
        indices = []
        for key in request.POST:
            if key.startswith("name_"):
                try:
                    indices.append(int(key.split("_", 1)[1]))
                except ValueError:
                    pass

        with transaction.atomic():
            for i in sorted(indices):
                name = request.POST.get(f"name_{i}", "").strip()
                palette_id = request.POST.get(f"palette_{i}", "").strip()
                if not name or not palette_id:
                    continue
                try:
                    palette = FabricColorPalette.objects.get(pk=int(palette_id))
                except (FabricColorPalette.DoesNotExist, ValueError):
                    errors.append(f"Рядок {i + 1}: палітру не знайдено.")
                    continue

                hex_code = request.POST.get(f"hex_code_{i}", "").strip()
                position_raw = request.POST.get(f"position_{i}", "0").strip()
                try:
                    position = int(position_raw)
                except ValueError:
                    position = 0
                image = request.FILES.get(f"image_{i}")

                if FabricColor.objects.filter(palette=palette, name=name).exists():
                    errors.append(
                        f"Рядок {i + 1}: «{name}» вже є в палітрі «{palette.name}»."
                    )
                    continue

                color = FabricColor(
                    palette=palette,
                    name=name,
                    hex_code=hex_code,
                    position=position,
                    is_active=True,
                )
                if image:
                    color.image = image
                color.save()
                saved_count += 1

        if saved_count:
            messages.success(request, f"Додано {saved_count} кольорів.")
        for err in errors:
            messages.error(request, err)
        if not errors:
            return redirect("custom_admin:palette_colors_bulk_add")

    return render(
        request,
        "custom_admin/palette_colors_bulk_add.html",
        {
            "sections": list(registry.all()),
            "palettes": palettes,
            "errors": errors,
        },
    )


@login_required
def palette_colors_bulk_edit(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    from fabric_category.models import FabricColor, FabricColorPalette

    palettes = FabricColorPalette.objects.filter(is_active=True).order_by("name")
    palette_id = (request.POST.get("palette") or request.GET.get("palette", "")).strip()
    selected_palette = None
    colors: list = []

    if palette_id:
        try:
            selected_palette = FabricColorPalette.objects.get(pk=int(palette_id))
            colors = list(selected_palette.colors.order_by("position", "id"))
        except (FabricColorPalette.DoesNotExist, ValueError):
            messages.error(request, "Палітру не знайдено.")

    if request.method == "POST" and selected_palette and "save" in request.POST:
        with transaction.atomic():
            updated = 0
            for color in colors:
                cid = str(color.pk)
                if request.POST.get(f"delete_{cid}"):
                    color.delete()
                    continue
                name = request.POST.get(f"name_{cid}", "").strip()
                hex_code = request.POST.get(f"hex_code_{cid}", "").strip()
                position_raw = request.POST.get(f"position_{cid}", "0").strip()
                is_active = bool(request.POST.get(f"is_active_{cid}"))
                image = request.FILES.get(f"image_{cid}")
                try:
                    position = int(position_raw)
                except ValueError:
                    position = color.position
                changed = False
                if name and name != color.name:
                    color.name = name
                    changed = True
                if hex_code != color.hex_code:
                    color.hex_code = hex_code
                    changed = True
                if position != color.position:
                    color.position = position
                    changed = True
                if is_active != color.is_active:
                    color.is_active = is_active
                    changed = True
                if image:
                    color.image = image
                    changed = True
                if changed:
                    color.save()
                    updated += 1
        messages.success(
            request, f"Оновлено {updated} кольорів у палітрі «{selected_palette.name}»."
        )
        return redirect(f"{request.path}?palette={selected_palette.pk}")

    return render(
        request,
        "custom_admin/palette_colors_bulk_edit.html",
        {
            "sections": list(registry.all()),
            "palettes": palettes,
            "selected_palette": selected_palette,
            "colors": colors,
        },
    )


def eurosof_price_config(request):
    if not request.user.is_staff:
        raise Http404("Сторінку не знайдено")

    import math
    from decimal import Decimal

    from furniture.models import Furniture, FurnitureSizeVariant
    from price_parser.models import EurosofPriceConfig

    config = EurosofPriceConfig.get()
    message = None
    recalc_count = 0

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save":
            try:
                config.price_multiplier = Decimal(request.POST["price_multiplier"])
                config.price_addon = Decimal(request.POST["price_addon"])
                config.save()
                message = ("success", "Конфігурацію збережено.")
            except Exception as exc:
                message = ("error", f"Помилка: {exc}")

        elif action == "recalculate":
            try:
                config.price_multiplier = Decimal(request.POST["price_multiplier"])
                config.price_addon = Decimal(request.POST["price_addon"])
                config.save()

                multiplier = config.price_multiplier
                addon = config.price_addon

                furniture_qs = Furniture.objects.filter(
                    article_code__startswith="eurosof-"
                )
                for f in furniture_qs.prefetch_related("size_variants"):
                    new_fabric_value = (
                        Decimal(str(math.ceil(float(f.fabric_step_raw * multiplier))))
                        if f.fabric_step_raw
                        else f.fabric_value
                    )
                    new_base_price = None
                    for v in f.size_variants.all():
                        if v.catalog_price:
                            new_price = round(v.catalog_price * multiplier + addon, 0)
                            v.price = new_price
                            v.save(update_fields=["price"])
                            if new_base_price is None:
                                new_base_price = new_price
                    f.fabric_value = new_fabric_value
                    if new_base_price:
                        f.price = new_base_price
                    f.save(update_fields=["price", "fabric_value"])
                    recalc_count += 1

                message = (
                    "success",
                    f"Перераховано ціни для {recalc_count} товарів Eurosof.",
                )
            except Exception as exc:
                message = ("error", f"Помилка при перерахунку: {exc}")

    eurosof_count = Furniture.objects.filter(
        article_code__startswith="eurosof-"
    ).count()
    return render(
        request,
        "custom_admin/eurosof_price_config.html",
        {
            "sections": list(registry.all()),
            "config": config,
            "eurosof_count": eurosof_count,
            "message": message,
        },
    )
