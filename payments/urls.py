from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    # Payment initiation
    path('payment/<int:order_id>/', views.PaymentView.as_view(), name='payment_form'),
    
    # Liqpay callback (server-to-server)
    path('liqpay/callback/', views.LiqpayCallbackView.as_view(), name='liqpay_callback'),
    
    # Payment result page (user redirect)
    path('payment/result/', views.PaymentResultView.as_view(), name='payment_result'),
    
    # Payment status check
    path('payment/<int:payment_id>/status/', views.PaymentStatusView.as_view(), name='payment_status'),
    
    # Cancel payment
    path('payment/<int:payment_id>/cancel/', views.cancel_payment, name='cancel_payment'),
    
    # Test payment page
    path('test/', views.TestPaymentView.as_view(), name='test_payment'),
] 