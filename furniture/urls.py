from django.urls import path

from . import views

app_name: str = "furniture"

urlpatterns = [
    path("", views.furniture_detail, name="furniture"),
    path("<str:furniture_slug>/", views.furniture_detail, name="furniture_detail"),
]
