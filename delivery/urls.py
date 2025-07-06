from django.urls import path

from . import views

app_name: str = "delivery"

urlpatterns = [
    path("np/cities", views.autocomplete_city, name="autocomplete_city"),
    path("np/warehouses", views.get_warehouses, name="get_warehouse"),

]
