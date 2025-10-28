from django.urls import path

from . import views

app_name = "custom_admin"

urlpatterns = [
    path("", views.redirect_to_dashboard, name="root"),
    path("login/", views.CustomAdminLoginView.as_view(), name="login"),
    path("logout/", views.CustomAdminLogoutView.as_view(), name="logout"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("<slug:section_slug>/", views.SectionListView.as_view(), name="list"),
    path("<slug:section_slug>/create/", views.SectionCreateView.as_view(), name="create"),
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
