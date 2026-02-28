import secrets
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpResponse, JsonResponse

"""
Health check views for the store application.
"""


def _healthcheck_authorized(request):
    """Allow unrestricted health checks only in DEBUG."""
    shared_secret = getattr(settings, "HEALTHCHECK_SHARED_SECRET", "")
    if not shared_secret:
        return settings.DEBUG
    provided = request.headers.get("X-Health-Check", "")
    return bool(provided) and secrets.compare_digest(provided, shared_secret)


def health_check(request):
    """
    Simple health check endpoint that verifies:
    - Django application is running
    - Database connection is working
    - Cache is working
    """
    if not _healthcheck_authorized(request):
        return JsonResponse({"status": "forbidden"}, status=403)
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check cache
    try:
        cache.set("health_check", "test", 10)
        cache_value = cache.get("health_check")
        if cache_value == "test":
            health_status["checks"]["cache"] = "ok"
        else:
            health_status["checks"]["cache"] = "error: cache not working"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["cache"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Return appropriate HTTP status code
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return JsonResponse(health_status, status=status_code)


def simple_health_check(request):
    """
    Very simple health check that just returns OK if the server is running.
    Useful for basic load balancer health checks.
    """
    if not _healthcheck_authorized(request):
        return JsonResponse({"status": "forbidden"}, status=403)
    return JsonResponse({"status": "ok", "timestamp": time.time()})


def robots_txt(request):
    """
    Return robots.txt directives for search engines.
    """
    site_url = getattr(settings, "SITE_BASE_URL", "https://montal.com.ua").rstrip("/")
    host = getattr(settings, "SITE_DOMAIN", "montal.com.ua")
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /checkout/",
        "Disallow: /price-parser/",
        "Allow: /",
        f"Sitemap: {site_url}/sitemap.xml",
        f"Host: {host}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
