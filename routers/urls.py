from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # empty path = root
    path('register/', views.register_router, name='register_router'),
]