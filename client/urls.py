from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='client_dashboard'),  # root of /dashboard/
    path('add_router/', views.add_router, name='client_add_router'),
    path('add_package/', views.add_package, name='client_add_package'),
    path('generate_voucher/', views.generate_voucher, name='generate_voucher'),
]
