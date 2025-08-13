import json
import hashlib
import base64
from typing import Dict, Any, Optional
from datetime import datetime
import requests
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from .models import Payment


class LiqpayService:
    """Service class for handling Liqpay payment operations."""
    
    def __init__(self):
        self.public_key = settings.LIQPAY_PUBLIC_KEY
        self.private_key = settings.LIQPAY_PRIVATE_KEY
        self.sandbox = settings.LIQPAY_SANDBOX
        # Use the correct Liqpay API URL
        self.api_url = "https://www.liqpay.ua/api/3/checkout"
    
    def create_payment(self, order, amount: float, description: str = "") -> Dict[str, Any]:
        """
        Create a new payment for the given order.
        
        Args:
            order: Order instance
            amount: Payment amount
            description: Payment description
            
        Returns:
            Dict containing payment data and form HTML
        """
        # Generate unique order ID
        liqpay_order_id = f"order_{order.id}_{int(timezone.now().timestamp())}"
        
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            liqpay_order_id=liqpay_order_id,
            amount=amount,
            description=description or f"Оплата замовлення #{order.id}",
            status='pending'
        )
        
        # Prepare payment data
        payment_data = {
            'action': 'pay',
            'amount': str(amount),
            'currency': 'UAH',
            'description': payment.description,
            'order_id': liqpay_order_id,
            'version': '3',
            'sandbox': '1' if self.sandbox else '0',
            'server_url': self._get_server_url(),
            'result_url': self._get_result_url(),
        }
        
        # Add customer information
        if order.customer_email:
            payment_data['sender_email'] = order.customer_email
        
        # Generate signature and data
        data = base64.b64encode(json.dumps(payment_data).encode('utf-8')).decode('utf-8')
        signature = self._generate_signature(data)
        
        return {
            'payment': payment,
            'data': data,
            'signature': signature,
            'api_url': self.api_url,
            'order_id': liqpay_order_id
        }
    
    def verify_callback(self, data: str, signature: str) -> Optional[Dict[str, Any]]:
        """
        Verify Liqpay callback signature and decode data.
        
        Args:
            data: Base64 encoded data from Liqpay
            signature: Signature from Liqpay
            
        Returns:
            Decoded payment data if signature is valid, None otherwise
        """
        try:
            # Verify signature
            expected_signature = self._generate_signature(data)
            if signature != expected_signature:
                return None
            
            # Decode data
            decoded_data = json.loads(base64.b64decode(data).decode('utf-8'))
            return decoded_data
            
        except Exception as e:
            print(f"Error verifying Liqpay callback: {e}")
            return None
    
    def process_callback(self, data: str, signature: str) -> bool:
        """
        Process Liqpay callback and update payment status.
        
        Args:
            data: Base64 encoded data from Liqpay
            signature: Signature from Liqpay
            
        Returns:
            True if processing was successful, False otherwise
        """
        decoded_data = self.verify_callback(data, signature)
        if not decoded_data:
            return False
        
        try:
            # Find payment by order ID
            order_id = decoded_data.get('order_id')
            payment = Payment.objects.get(liqpay_order_id=order_id)
            
            # Update payment with Liqpay response
            payment.liqpay_response = decoded_data
            payment.liqpay_payment_id = decoded_data.get('payment_id')
            
            # Update status based on Liqpay status
            liqpay_status = decoded_data.get('status')
            if liqpay_status == 'success':
                payment.status = 'success'
                payment.paid_at = timezone.now()
            elif liqpay_status in ['failure', 'error']:
                payment.status = 'failed'
            elif liqpay_status == 'canceled':
                payment.status = 'cancelled'
            
            payment.save()
            
            return True
            
        except Payment.DoesNotExist:
            print(f"Payment not found for order_id: {decoded_data.get('order_id')}")
            return False
        except Exception as e:
            print(f"Error processing Liqpay callback: {e}")
            return False
    
    def get_payment_status(self, payment: Payment) -> Optional[str]:
        """
        Get current payment status from Liqpay API.
        
        Args:
            payment: Payment instance
            
        Returns:
            Current payment status or None if error
        """
        try:
            # Prepare request data
            request_data = {
                'action': 'status',
                'version': '3',
                'order_id': payment.liqpay_order_id,
            }
            
            # Generate signature
            data = base64.b64encode(json.dumps(request_data).encode('utf-8')).decode('utf-8')
            signature = self._generate_signature(data)
            
            # Make API request
            response = requests.post(
                self.api_url,
                data={
                    'data': data,
                    'signature': signature
                },
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status') == 'success':
                    return response_data.get('result', {}).get('status')
            
            return None
            
        except Exception as e:
            print(f"Error getting payment status: {e}")
            return None
    
    def _generate_signature(self, data: str) -> str:
        """Generate Liqpay signature for the given data."""
        string_to_sign = self.private_key + data + self.private_key
        return base64.b64encode(hashlib.sha1(string_to_sign.encode('utf-8')).digest()).decode('utf-8')
    
    def _get_server_url(self) -> str:
        """Get server URL for Liqpay callbacks."""
        # For development, use localhost
        if settings.DEBUG:
            return f"http://localhost:8000{reverse('payments:liqpay_callback')}"
        else:
            # You'll need to replace this with your actual domain
            return f"https://yourdomain.com{reverse('payments:liqpay_callback')}"
    
    def _get_result_url(self) -> str:
        """Get result URL for Liqpay redirects."""
        # For development, use localhost
        if settings.DEBUG:
            return f"http://localhost:8000{reverse('payments:payment_result')}"
        else:
            # You'll need to replace this with your actual domain
            return f"https://yourdomain.com{reverse('payments:payment_result')}" 