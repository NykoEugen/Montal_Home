from django.urls import path

from . import views

app_name: str = "sub_categories"

urlpatterns = [
    path("", views.sub_categories_list, name="sub_categories_list"),
    path(
        "<str:sub_categories_slug>/",
        views.sub_categories_details,
        name="sub_categories_details",
    ),
]
