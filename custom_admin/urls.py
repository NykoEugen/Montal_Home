from django.urls import path

from . import views

app_name = "custom_admin"

urlpatterns = [
    path("", views.redirect_to_dashboard, name="root"),
    path("login/", views.CustomAdminLoginView.as_view(), name="login"),
    path("logout/", views.CustomAdminLogoutView.as_view(), name="logout"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("orders/<int:pk>/generate-iban/", views.generate_iban_invoice, name="generate_iban_invoice"),
    path(
        "price-configs/<int:pk>/update-prices/",
        views.update_price_config_prices,
        name="price_config_update_prices",
    ),
    path(
        "price-configs/<int:pk>/test-parse/",
        views.test_price_config_parse,
        name="price_config_test_parse",
    ),
    path(
        "price-configs/bulk-action/",
        views.price_config_bulk_action,
        name="price_config_bulk_action",
    ),
    path(
        "supplier-feeds/<int:pk>/update-prices/",
        views.update_supplier_feed_prices,
        name="supplier_feed_update_prices",
    ),
    path(
        "supplier-feeds/<int:pk>/test-parse/",
        views.test_supplier_feed_parse,
        name="supplier_feed_test_parse",
    ),
    path(
        "supplier-feeds/bulk-action/",
        views.supplier_feed_bulk_action,
        name="supplier_feed_bulk_action",
    ),
    path(
        "supplier-web/<int:pk>/update-prices/",
        views.update_supplier_web_prices,
        name="supplier_web_update_prices",
    ),
    path(
        "supplier-web/<int:pk>/test-parse/",
        views.test_supplier_web_parse,
        name="supplier_web_test_parse",
    ),
    path(
        "supplier-web/bulk-action/",
        views.supplier_web_bulk_action,
        name="supplier_web_bulk_action",
    ),
    path("furniture/bulk-edit/", views.furniture_bulk_edit, name="furniture_bulk_edit"),
    path("furniture/bulk-edit/apply/", views.furniture_bulk_edit_apply, name="furniture_bulk_edit_apply"),
    path("kreslalux/", views.kreslalux_page, name="kreslalux"),
    path("<slug:section_slug>/", views.SectionListView.as_view(), name="list"),
    path("<slug:section_slug>/create/", views.SectionCreateView.as_view(), name="create"),
    path(
        "<slug:section_slug>/<int:pk>/",
        views.SectionDetailView.as_view(),
        name="detail",
    ),
    path(
        "<slug:section_slug>/<int:pk>/edit/",
        views.SectionUpdateView.as_view(),
        name="edit",
    ),
    path(
        "<slug:section_slug>/<int:pk>/delete/",
        views.SectionDeleteView.as_view(),
        name="delete",
    ),
]
