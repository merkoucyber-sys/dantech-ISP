from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # empty path = root
    path('register/', views.register_router, name='register_router'),
    path('<int:router_id>/delete/', views.delete_router, name='delete_router'),
    path('<int:router_id>/script/', views.router_script, name='router_script'),
    path('heartbeat/<str:token>/', views.router_heartbeat, name='router_heartbeat'),
]