from django.urls import path

from . import views

app_name: str = "delivery"

urlpatterns = [
    path("", views.delivery_address, name="delivery_address"),

]
