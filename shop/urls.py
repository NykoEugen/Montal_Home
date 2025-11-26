from django.urls import path

from . import auth_views, views

app_name: str = "shop"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("search-suggestions/", views.search_suggestions, name="search_suggestions"),
    path("promotions/", views.promotions, name="promotions"),
    path("where-to-buy/", views.where_to_buy, name="where_to_buy"),
    path("contacts/", views.contacts, name="contacts"),
    path("warranty/", views.warranty, name="warranty"),
    path("delivery-payment/", views.delivery_payment, name="delivery_payment"),
    path("offer/", views.offer, name="offer"),
    path("add-to-cart/", views.add_to_cart, name="add_to_cart"),
    path("add-to-cart-detail/", views.add_to_cart_from_detail, name="add_to_cart_from_detail"),
    path("remove-from-cart/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/", views.view_cart, name="view_cart"),
    path("login/", auth_views.login_view, name="login"),
    path("logout/", auth_views.logout_view, name="logout"),
    path("register/", auth_views.register_view, name="register"),
    path("reset-password/", auth_views.password_reset_request, name="password_reset"),
    path(
        "reset-password/<uidb64>/<token>/",
        auth_views.password_reset_confirm,
        name="password_reset_confirm",
    ),
]
