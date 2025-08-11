from django.urls import path

from . import views

app_name: str = "shop"

urlpatterns = [
    path("", views.home, name="home"),
    path("promotions/", views.promotions, name="promotions"),
    path("where-to-buy/", views.where_to_buy, name="where_to_buy"),
    path("contacts/", views.contacts, name="contacts"),
    path("add-to-cart/", views.add_to_cart, name="add_to_cart"),
    path("add-to-cart-detail/", views.add_to_cart_from_detail, name="add_to_cart_from_detail"),
    path("remove-from-cart/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/", views.view_cart, name="view_cart"),
]
