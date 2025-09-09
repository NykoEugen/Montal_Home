"""
Enhanced admin utilities for graceful reconnects and error handling.
"""

import logging
from django.contrib import admin, messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils.html import format_html
from django.db import transaction
from django.core.exceptions import ValidationError
from .connection_utils import (
    resilient_database_operation, 
    save_form_draft, 
    load_form_draft, 
    clear_form_draft,
    check_database_connection
)

logger = logging.getLogger('store.connection')


class ResilientModelAdmin(admin.ModelAdmin):
    """
    Enhanced ModelAdmin with connection resilience and graceful error handling.
    """
    
    def save_model(self, request, obj, form, change):
        """Save model with connection resilience."""
        try:
            def save_operation():
                obj.save()
                return obj
            
            result = resilient_database_operation(save_operation)
            
            if change:
                self.message_user(request, f"{obj._meta.verbose_name} was changed successfully.")
            else:
                self.message_user(request, f"{obj._meta.verbose_name} was added successfully.")
            
            # Clear any saved drafts
            clear_form_draft(request, f"{obj._meta.model_name}_form")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to save {obj._meta.model_name}: {e}")
            
            # Save form data as draft
            form_data = form.cleaned_data if form.is_valid() else form.data
            save_form_draft(request, form_data, f"{obj._meta.model_name}_form")
            
            self.message_user(
                request, 
                f"Failed to save {obj._meta.verbose_name}. Your data has been saved as a draft. Please try again.",
                level=messages.ERROR
            )
            raise
    
    def delete_model(self, request, obj):
        """Delete model with connection resilience."""
        try:
            def delete_operation():
                obj.delete()
            
            resilient_database_operation(delete_operation)
            self.message_user(request, f"{obj._meta.verbose_name} was deleted successfully.")
            
        except Exception as e:
            logger.error(f"Failed to delete {obj._meta.model_name}: {e}")
            self.message_user(
                request, 
                f"Failed to delete {obj._meta.verbose_name}. Please try again.",
                level=messages.ERROR
            )
            raise
    
    def get_form(self, request, obj=None, **kwargs):
        """Get form with draft data if available."""
        form = super().get_form(request, obj, **kwargs)
        
        # Load draft data if creating new object
        if not obj:
            draft_data = load_form_draft(request, f"{self.model._meta.model_name}_form")
            if draft_data:
                form.initial = draft_data
                messages.info(request, "Draft data loaded. Please review and save.")
        
        return form
    
    def changelist_view(self, request, extra_context=None):
        """Enhanced changelist view with connection monitoring."""
        extra_context = extra_context or {}
        
        # Add connection status to context
        try:
            db_connected = check_database_connection()
            extra_context['connection_status'] = {
                'database': 'connected' if db_connected else 'disconnected',
                'show_warning': not db_connected
            }
        except Exception as e:
            logger.error(f"Connection status check failed: {e}")
            extra_context['connection_status'] = {
                'database': 'error',
                'show_warning': True
            }
        
        return super().changelist_view(request, extra_context)
    
    def response_add(self, request, obj, post_url_continue=None):
        """Enhanced response for successful addition."""
        response = super().response_add(request, obj, post_url_continue)
        
        # Clear any saved drafts
        clear_form_draft(request, f"{obj._meta.model_name}_form")
        
        return response
    
    def response_change(self, request, obj):
        """Enhanced response for successful change."""
        response = super().response_change(request, obj)
        
        # Clear any saved drafts
        clear_form_draft(request, f"{obj._meta.model_name}_form")
        
        return response


class ResilientInlineAdmin(admin.TabularInline):
    """
    Enhanced TabularInline with connection resilience.
    """
    
    def save_formset(self, request, form, formset, change):
        """Save formset with connection resilience."""
        try:
            def save_formset_operation():
                formset.save()
            
            resilient_database_operation(save_formset_operation)
            
        except Exception as e:
            logger.error(f"Failed to save formset: {e}")
            
            # Save formset data as draft
            formset_data = []
            for form in formset:
                if form.has_changed():
                    formset_data.append(form.cleaned_data)
            
            if formset_data:
                save_form_draft(request, formset_data, f"{formset.model._meta.model_name}_formset")
            
            messages.error(
                request, 
                "Failed to save some items. Your changes have been saved as a draft. Please try again."
            )
            raise


def admin_connection_status_view(request):
    """Admin view for checking connection status."""
    from .connection_utils import admin_connection_monitor
    
    status = admin_connection_monitor(request)
    return JsonResponse(status)


def admin_retry_failed_operations_view(request):
    """Admin view for retrying failed operations using saved drafts."""
    if request.method == 'POST':
        operation_type = request.POST.get('operation_type')
        
        try:
            if operation_type == 'clear_drafts':
                # Clear all saved drafts
                from django.core.cache import cache
                cache.delete_many([key for key in cache._cache.keys() if key.startswith('form_draft_')])
                messages.success(request, "All saved drafts have been cleared.")
            elif operation_type == 'retry_connection':
                # Test database connection
                from .connection_utils import ensure_database_connection
                ensure_database_connection()
                messages.success(request, "Database connection restored successfully.")
            
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))
            
        except Exception as e:
            logger.error(f"Failed to retry operation: {e}")
            messages.error(request, f"Failed to retry operation: {e}")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)
