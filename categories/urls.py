from django.urls import path

from . import views

app_name: str = "categories"

urlpatterns = [
    path("", views.categories_list, name="categories_list"),
    path("<str:category_slug>/", views.category_detail, name="category_detail"),
]
