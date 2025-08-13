import logging
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from checkout.models import Order
from .models import Payment
from .services import LiqpayService


class TestPaymentView(TemplateView):
    """View for testing Liqpay payment without real credentials."""
    
    template_name = "payments/test_payment.html"
    
    def get_context_data(self, **kwargs):
        """Generate test payment data."""
        context = super().get_context_data(**kwargs)
        
        try:
            # Create test payment data
            liqpay_service = LiqpayService()
            
            # Create a dummy order for testing
            from checkout.models import Order
            test_order = Order.objects.create(
                customer_name="Test",
                customer_last_name="User",
                customer_phone_number="0123456789",
                delivery_type="local",
                delivery_city="Test City",
                payment_type="liqupay"
            )
            
            # Generate payment data
            payment_data = liqpay_service.create_payment(
                order=test_order,
                amount=100.00,
                description="Test payment"
            )
            
            context['payment_data'] = payment_data
            
        except Exception as e:
            context['error'] = str(e)
            logger.error(f"Error creating test payment: {e}")
        
        return context

logger = logging.getLogger(__name__)


class PaymentView(TemplateView):
    """View for initiating Liqpay payment."""
    
    template_name = "payments/payment_form.html"
    
    def get_context_data(self, **kwargs):
        """Get payment form context."""
        context = super().get_context_data(**kwargs)
        order_id = self.kwargs.get('order_id')
        
        try:
            order = get_object_or_404(Order, id=order_id)
            
            # Calculate total amount
            total_amount = sum(
                item.price * item.quantity 
                for item in order.orderitem_set.all()
            )
            
            # Create Liqpay payment
            liqpay_service = LiqpayService()
            payment_data = liqpay_service.create_payment(
                order=order,
                amount=float(total_amount),
                description=f"Оплата замовлення #{order.id}"
            )
            
            context.update({
                'order': order,
                'payment_data': payment_data,
                'total_amount': total_amount,
            })
            
        except Exception as e:
            logger.error(f"Error creating payment for order {order_id}: {e}")
            messages.error(self.request, "Помилка створення платежу")
            return redirect('shop:home')
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
class LiqpayCallbackView(View):
    """Handle Liqpay server-to-server callbacks."""
    
    def post(self, request: HttpRequest) -> HttpResponse:
        """Process Liqpay callback."""
        try:
            # Get callback data
            data = request.POST.get('data')
            signature = request.POST.get('signature')
            
            if not data or not signature:
                logger.error("Missing data or signature in Liqpay callback")
                return HttpResponse(status=400)
            
            # Process callback
            liqpay_service = LiqpayService()
            success = liqpay_service.process_callback(data, signature)
            
            if success:
                logger.info("Liqpay callback processed successfully")
                return HttpResponse(status=200)
            else:
                logger.error("Failed to process Liqpay callback")
                return HttpResponse(status=400)
                
        except Exception as e:
            logger.error(f"Error processing Liqpay callback: {e}")
            return HttpResponse(status=500)


class PaymentResultView(TemplateView):
    """View for payment result page (user redirect from Liqpay)."""
    
    template_name = "payments/payment_result.html"
    
    def get_context_data(self, **kwargs):
        """Get payment result context."""
        context = super().get_context_data(**kwargs)
        
        # Get payment data from URL parameters
        data = self.request.GET.get('data')
        signature = self.request.GET.get('signature')
        
        if data and signature:
            # Verify and decode payment data
            liqpay_service = LiqpayService()
            decoded_data = liqpay_service.verify_callback(data, signature)
            
            if decoded_data:
                # Find payment
                order_id = decoded_data.get('order_id')
                try:
                    payment = Payment.objects.get(liqpay_order_id=order_id)
                    order = payment.order
                    
                    # Update payment status if needed
                    liqpay_status = decoded_data.get('status')
                    if liqpay_status == 'success' and payment.status != 'success':
                        payment.status = 'success'
                        payment.liqpay_response = decoded_data
                        payment.save()
                    
                    context.update({
                        'payment': payment,
                        'order': order,
                        'liqpay_status': liqpay_status,
                        'success': liqpay_status == 'success',
                    })
                    
                except Payment.DoesNotExist:
                    messages.error(self.request, "Платіж не знайдено")
                    context['error'] = True
            else:
                messages.error(self.request, "Помилка верифікації платежу")
                context['error'] = True
        else:
            messages.error(self.request, "Відсутні дані платежу")
            context['error'] = True
        
        return context


class PaymentStatusView(View):
    """View for checking payment status via AJAX."""
    
    def get(self, request: HttpRequest, payment_id: int) -> JsonResponse:
        """Get payment status."""
        try:
            payment = get_object_or_404(Payment, id=payment_id)
            
            # Get status from Liqpay if payment is pending
            if payment.status == 'pending':
                liqpay_service = LiqpayService()
                liqpay_status = liqpay_service.get_payment_status(payment)
                
                if liqpay_status:
                    # Update payment status
                    if liqpay_status == 'success':
                        payment.status = 'success'
                    elif liqpay_status in ['failure', 'error']:
                        payment.status = 'failed'
                    elif liqpay_status == 'canceled':
                        payment.status = 'cancelled'
                    
                    payment.save()
            
            return JsonResponse({
                'status': payment.status,
                'status_display': payment.get_status_display(),
                'is_paid': payment.is_paid,
                'is_pending': payment.is_pending,
                'is_failed': payment.is_failed,
            })
            
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return JsonResponse({'error': 'Помилка перевірки статусу'}, status=500)


@require_POST
def cancel_payment(request: HttpRequest, payment_id: int) -> HttpResponse:
    """Cancel a pending payment."""
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        
        if payment.status == 'pending':
            payment.status = 'cancelled'
            payment.save()
            messages.success(request, "Платіж скасовано")
        else:
            messages.error(request, "Неможливо скасувати цей платіж")
        
        return redirect('payments:payment_result', payment_id=payment_id)
        
    except Exception as e:
        logger.error(f"Error cancelling payment: {e}")
        messages.error(request, "Помилка скасування платежу")
        return redirect('shop:home')
