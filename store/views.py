"""
Health check views for the store application.
"""

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import time


def health_check(request):
    """
    Simple health check endpoint that verifies:
    - Django application is running
    - Database connection is working
    - Cache is working
    """
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
    return JsonResponse({"status": "ok", "timestamp": time.time()})
