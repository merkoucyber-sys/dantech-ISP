from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='client_dashboard'),  # root of /dashboard/
    path('add_router/', views.add_router, name='client_add_router'),
    path('add_package/', views.add_package, name='client_add_package'),
    path('edit_package/<int:package_id>/', views.client_update_package, name='client_update_package'),
    path('update_business/', views.client_update_business, name='client_update_business'),
    path('update_payment_settings/', views.client_update_payment_settings, name='client_update_payment_settings'),
    path('buy_package/', views.buy_package, name='buy_package'),
    path('generate_voucher/', views.generate_voucher, name='generate_voucher'),
    path('reactivate_customer/', views.reactivate_customer, name='reactivate_customer'),
    path('generate_customer_voucher/', views.generate_customer_voucher, name='generate_customer_voucher'),
]
