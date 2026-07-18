from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.wifi_login, name='wifi_login'),
    path('pay/<int:package_id>/', views.mpesa_payment, name='mpesa_payment'),
    path('buy/', views.buy_package, name='buy_package'),
    path('activate/', views.activate_voucher, name='activate_voucher'),
]
