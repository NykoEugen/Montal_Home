from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "furniture/<int:furniture_id>/", views.furniture_detail, name="furniture_detail"
    ),
    path("add-to-cart/<int:furniture_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.view_cart, name="view_cart"),
    path("checkout/", views.checkout, name="checkout"),
]
