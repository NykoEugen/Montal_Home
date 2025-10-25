"""
URL configuration for store project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from . import views
from .admin_utils import admin_connection_status_view, admin_retry_failed_operations_view
from .sitemaps import SITEMAPS

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin/connection-status/", admin_connection_status_view, name="admin_connection_status"),
    path("admin/retry-operations/", admin_retry_failed_operations_view, name="admin_retry_operations"),
    path("health/", views.health_check, name="health_check"),
    path("health/simple/", views.simple_health_check, name="simple_health_check"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("", include("shop.urls", namespace="shop")),
    path("catalogue/", include("categories.urls")),
    path("furniture/", include("furniture.urls")),
    path("sub-categories/", include("sub_categories.urls")),
    path("checkout/", include("checkout.urls")),
    path("delivery/", include("delivery.urls")),
    path("price-parser/", include("price_parser.urls", namespace="price_parser")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
