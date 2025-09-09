"""
Connection resilience utilities for graceful reconnects.
Provides retry mechanisms, circuit breaker patterns, and connection monitoring.
"""

import time
import logging
from functools import wraps
from typing import Callable, Any, Optional
from django.conf import settings
from django.db import connection, transaction
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib import messages

logger = logging.getLogger('store.connection')


class CircuitBreaker:
    """Circuit breaker pattern implementation for connection resilience."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
            else:
                raise ConnectionError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e


def retry_with_backoff(
    max_retries: int = 3,
    delay: float = 1.0,
    exponential_backoff: bool = True,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        exponential_backoff: Whether to use exponential backoff
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise e
                    
                    logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    
                    if attempt < max_retries:
                        time.sleep(current_delay)
                        if exponential_backoff:
                            current_delay *= 2
            
            raise last_exception
        return wrapper
    return decorator


def check_database_connection() -> bool:
    """Check if database connection is healthy."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def ensure_database_connection():
    """Ensure database connection is available, reconnect if necessary."""
    if not check_database_connection():
        logger.info("Attempting to reconnect to database...")
        connection.close()
        # Force a new connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        logger.info("Database reconnection successful")


@retry_with_backoff(max_retries=3, delay=1.0, exceptions=(Exception,))
def resilient_database_operation(operation: Callable, *args, **kwargs) -> Any:
    """
    Execute database operation with automatic retry and reconnection.
    
    Args:
        operation: Database operation function to execute
        *args: Arguments for the operation
        **kwargs: Keyword arguments for the operation
    
    Returns:
        Result of the database operation
    """
    try:
        return operation(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Database operation failed, attempting reconnection: {e}")
        ensure_database_connection()
        raise e


def save_form_draft(request, form_data: dict, form_name: str) -> None:
    """Save form data as draft in case of connection failure."""
    try:
        draft_key = f"form_draft_{form_name}_{request.session.session_key}"
        cache.set(draft_key, form_data, timeout=3600)  # 1 hour
        logger.info(f"Form draft saved for {form_name}")
    except Exception as e:
        logger.error(f"Failed to save form draft: {e}")


def load_form_draft(request, form_name: str) -> Optional[dict]:
    """Load form data from draft."""
    try:
        draft_key = f"form_draft_{form_name}_{request.session.session_key}"
        return cache.get(draft_key)
    except Exception as e:
        logger.error(f"Failed to load form draft: {e}")
        return None


def clear_form_draft(request, form_name: str) -> None:
    """Clear form draft after successful submission."""
    try:
        draft_key = f"form_draft_{form_name}_{request.session.session_key}"
        cache.delete(draft_key)
        logger.info(f"Form draft cleared for {form_name}")
    except Exception as e:
        logger.error(f"Failed to clear form draft: {e}")


class ConnectionResilienceMiddleware:
    """Middleware for handling connection resilience across requests."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=getattr(settings, 'CONNECTION_RESILIENCE', {}).get('CIRCUIT_BREAKER_THRESHOLD', 5),
            timeout=getattr(settings, 'CONNECTION_RESILIENCE', {}).get('CIRCUIT_BREAKER_TIMEOUT', 60)
        )
    
    def __call__(self, request):
        # Check database connection before processing request
        if not check_database_connection():
            logger.warning("Database connection lost, attempting reconnection")
            try:
                ensure_database_connection()
            except Exception as e:
                logger.error(f"Failed to reconnect to database: {e}")
                if request.path.startswith('/admin/'):
                    messages.error(request, "Database connection lost. Please refresh the page.")
                return JsonResponse({
                    'error': 'Database connection lost',
                    'message': 'Please try again in a moment'
                }, status=503)
        
        response = self.get_response(request)
        return response


def admin_connection_monitor(request):
    """Monitor admin panel connections and provide status."""
    try:
        db_status = check_database_connection()
        cache_status = cache.get('connection_test', 'test') == 'test'
        
        return {
            'database': 'connected' if db_status else 'disconnected',
            'cache': 'connected' if cache_status else 'disconnected',
            'timestamp': time.time()
        }
    except Exception as e:
        logger.error(f"Connection monitoring failed: {e}")
        return {
            'database': 'error',
            'cache': 'error',
            'error': str(e),
            'timestamp': time.time()
        }
