"""
Custom middleware for handling connection resilience and graceful reconnects.
"""

import json
import logging
import time
from django.http import JsonResponse, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages
from django.core.cache import cache
from django.conf import settings
from .connection_utils import (
    check_database_connection,
    ensure_database_connection,
    save_form_draft,
    load_form_draft,
    CircuitBreaker
)

logger = logging.getLogger('store.connection')


class ConnectionResilienceMiddleware(MiddlewareMixin):
    """
    Middleware for handling connection resilience across all requests.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=getattr(settings, 'CONNECTION_RESILIENCE', {}).get('CIRCUIT_BREAKER_THRESHOLD', 5),
            timeout=getattr(settings, 'CONNECTION_RESILIENCE', {}).get('CIRCUIT_BREAKER_TIMEOUT', 60)
        )
    
    def process_request(self, request):
        return None
    
    def process_response(self, request, response):
        """Process response and add connection status headers."""
        # Add connection status header for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                db_connected = check_database_connection()
                response['X-Connection-Status'] = 'connected' if db_connected else 'disconnected'
            except Exception:
                response['X-Connection-Status'] = 'error'
        
        return response
    
    def _handle_post_connection_failure(self, request):
        """Handle POST request connection failures by saving form data."""
        try:
            # Extract form data
            form_data = {}
            if request.content_type == 'application/json':
                form_data = json.loads(request.body)
            else:
                form_data = request.POST.dict()
            
            # Save as draft
            if form_data:
                save_form_draft(request, form_data, 'post_request')
                logger.info("POST request data saved as draft due to connection failure")
                
        except Exception as e:
            logger.error(f"Failed to save POST request data: {e}")


class PostRequestResilienceMiddleware(MiddlewareMixin):
    """
    Middleware specifically for handling POST request resilience.
    """
    
    def process_request(self, request):
        """Process POST requests with resilience features."""
        if request.method != 'POST':
            return None
        
        # Check if retry is enabled
        resilience_settings = getattr(settings, 'POST_REQUEST_RESILIENCE', {})
        if not resilience_settings.get('ENABLE_RETRY', True):
            return None
        
        # Store original POST data for potential retry
        if hasattr(request, 'POST') and request.POST:
            request._original_post_data = request.POST.dict()
        
        return None
    
    def process_exception(self, request, exception):
        """Handle exceptions during POST request processing."""
        if request.method != 'POST':
            return None
        
        # Check if this is a connection-related exception
        if any(keyword in str(exception).lower() for keyword in 
               ['connection', 'database', 'timeout', 'network']):
            
            logger.warning(f"POST request failed due to connection issue: {exception}")
            
            # Save form data as draft
            if hasattr(request, '_original_post_data'):
                save_form_draft(request, request._original_post_data, 'post_request')
            
            # Return appropriate response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': 'Connection lost',
                    'message': 'Your data has been saved. Please try again.',
                    'retry_available': True,
                    'draft_saved': True
                }, status=503)
            else:
                messages.error(
                    request,
                    "Connection lost. Your data has been saved. Please try again.",
                    extra_tags="user",
                )
                return None
        
        return None


class AdminConnectionMonitorMiddleware(MiddlewareMixin):
    """
    Middleware for monitoring admin panel connections.
    """
    
    def process_request(self, request):
        return None
    
    def process_response(self, request, response):
        """Add connection status to admin responses."""
        if not request.path.startswith('/admin/'):
            return response
        
        # Add connection status to admin pages
        if hasattr(response, 'content') and b'<html' in response.content:
            try:
                db_connected = check_database_connection()
                status_class = 'connected' if db_connected else 'disconnected'
                
                # Add connection status indicator to admin pages
                status_html = f'''
                <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    var status = document.createElement('div');
                    status.id = 'connection-status';
                    status.className = 'connection-status {status_class}';
                    status.innerHTML = 'DB: {status_class}';
                    status.style.cssText = 'position:fixed;top:10px;right:10px;padding:5px 10px;border-radius:3px;font-size:12px;z-index:9999;';
                    status.style.backgroundColor = db_connected ? '#d4edda' : '#f8d7da';
                    status.style.color = db_connected ? '#155724' : '#721c24';
                    document.body.appendChild(status);
                }});
                </script>
                '''
                
                # Insert the script before closing body tag
                if b'</body>' in response.content:
                    response.content = response.content.replace(
                        b'</body>', 
                        status_html.encode() + b'</body>'
                    )
            
            except Exception as e:
                logger.error(f"Failed to add connection status to admin page: {e}")
        
        return response
