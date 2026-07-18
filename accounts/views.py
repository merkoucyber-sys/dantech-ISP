from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
import random, string

from .models import Client, User
from routers.models import Router
from client.models import Package, Voucher, Receipt


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('login_redirect')
        else:
            return render(request, 'accounts/login.html', {'error': 'Invalid credentials'})
    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def login_redirect(request):
    if request.user.is_superuser:
        return redirect('superuser_dashboard')
    elif request.user.is_client:
        return redirect('client_dashboard')
    else:
        return redirect('wifi_login')


@login_required(login_url='/accounts/login/')
def superuser_dashboard(request):
    if not request.user.is_superuser:
        return redirect('login')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_client':
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            name = request.POST.get('name', '').strip()
            phone = request.POST.get('phone', '').strip()
            if username and password and name and phone:
                user = User.objects.create_user(username=username, password=password)
                user.is_client = True
                user.save()
                Client.objects.create(user=user, name=name, phone=phone)
            return redirect('superuser_dashboard')

        if action == 'add_router':
            client_id = request.POST.get('client_id')
            name = request.POST.get('router_name', '').strip()
            ip = request.POST.get('router_ip', '').strip()
            if client_id and name and ip:
                client = Client.objects.filter(id=client_id).first()
                if client:
                    Router.objects.create(
                        client=client,
                        name=name,
                        ip_address=ip,
                        api_username=request.POST.get('router_username', '').strip(),
                        api_password=request.POST.get('router_password', '').strip(),
                        latitude=float(request.POST.get('latitude') or 0.0),
                        longitude=float(request.POST.get('longitude') or 0.0),
                        status='offline',
                    )
            return redirect('superuser_dashboard')

        if action == 'add_package':
            client_id = request.POST.get('client_id')
            name = request.POST.get('package_name', '').strip()
            price = request.POST.get('package_price')
            duration = request.POST.get('package_duration')
            devices = request.POST.get('package_devices')
            if client_id and name and price and duration and devices:
                client = Client.objects.filter(id=client_id).first()
                if client:
                    Package.objects.create(
                        client=client,
                        name=name,
                        price=price,
                        duration_hours=duration,
                        device_limit=devices,
                    )
            return redirect('superuser_dashboard')

        if action == 'generate_voucher':
            client_id = request.POST.get('client_id')
            client = Client.objects.filter(id=client_id).first()
            if client:
                username = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                expiry = timezone.now() + timedelta(hours=1)
                Voucher.objects.create(client=client, username=username, password=password, expiry=expiry)
            return redirect('superuser_dashboard')

    clients = Client.objects.all()
    routers = Router.objects.all()
    packages = Package.objects.all()
    vouchers = Voucher.objects.all()
    receipts = Receipt.objects.all()

    return render(request, 'accounts/superuser_dashboard.html', {
        'clients': clients,
        'routers': routers,
        'packages': packages,
        'vouchers': vouchers,
        'receipts': receipts,
    })
