from django.urls import path
from . import views

urlpatterns = [
    # WiFi Login & Checkout
    path('login/', views.wifi_login, name='wifi_login'),
    path('checkout/', views.wifi_checkout, name='wifi_checkout'),
    
    # Payment Processing
    path('process-payment/', views.process_payment, name='process_payment'),
    path('mpesa-callback/', views.mpesa_callback, name='mpesa_callback'),
    
    # Payment Status
    path('payment-success/<int:receipt_id>/', views.payment_success, name='payment_success'),
    path('payment-failed/', views.payment_failed, name='payment_failed'),
    path('check-payment-status/<int:receipt_id>/', views.check_payment_status, name='check_payment_status'),
    
    # Voucher
    path('activate-voucher/', views.activate_voucher, name='activate_voucher'),
]

