from django.urls import path

from . import views

app_name: str = "checkout"

urlpatterns = [
    path("", views.checkout, name="checkout"),
    path("order-history/", views.order_history, name="order_history"),
]
