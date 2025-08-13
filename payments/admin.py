from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin configuration for Payment model."""
    
    list_display = [
        'liqpay_order_id', 
        'order', 
        'amount', 
        'currency', 
        'status', 
        'created_at'
    ]
    
    list_filter = [
        'status', 
        'currency', 
        'created_at', 
        'paid_at'
    ]
    
    search_fields = [
        'liqpay_order_id', 
        'liqpay_payment_id', 
        'order__customer_name', 
        'order__customer_last_name',
        'order__customer_phone_number'
    ]
    
    readonly_fields = [
        'liqpay_order_id', 
        'liqpay_payment_id', 
        'created_at', 
        'updated_at', 
        'paid_at',
        'liqpay_response'
    ]
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('order', 'liqpay_order_id', 'liqpay_payment_id', 'status')
        }),
        ('Фінансова інформація', {
            'fields': ('amount', 'currency', 'description')
        }),
        ('Дати', {
            'fields': ('created_at', 'updated_at', 'paid_at'),
            'classes': ('collapse',)
        }),
        ('Відповідь Liqpay', {
            'fields': ('liqpay_response',),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Disable manual payment creation."""
        return False
