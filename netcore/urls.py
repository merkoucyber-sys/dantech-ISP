"""
URL configuration for netcore project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.shortcuts import redirect, render
from django.http import HttpResponse


def redirect_to_dashboard(request):
    return redirect('client_dashboard')


def home(request):
    return render(request, 'client/landing.html')


def service_worker(request):
    return HttpResponse(
        """self.addEventListener('install', (event) => { event.waitUntil(self.skipWaiting()); });
self.addEventListener('activate', (event) => { event.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', (event) => { event.respondWith(fetch(event.request)); });
""",
        content_type='application/javascript',
    )

urlpatterns = [
    path('', home, name='home'),
    path('dashboard/', include('client.urls')),
    path('accounts/', include('accounts.urls')),
    path('wifi/', include('wifi.urls')),
    path('routers/', include('routers.urls')),
    path('service-worker.js', service_worker),
]
