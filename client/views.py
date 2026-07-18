from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
import random, string
from routers.models import Router
from .models import Package, Voucher, Receipt
from accounts.models import Client

@login_required(login_url='/accounts/login/')
def dashboard(request):
    if request.user.is_superuser:
        routers = Router.objects.all()
        packages = Package.objects.all()
        vouchers = Voucher.objects.all()
        receipts = Receipt.objects.all()
        client = None
    else:
        if not getattr(request.user, 'is_authenticated', False):
            return redirect('/accounts/login/')

        try:
            client = request.user.client
            routers = Router.objects.filter(client=client)
            packages = Package.objects.filter(client=client)
            vouchers = Voucher.objects.filter(client=client)
            receipts = Receipt.objects.filter(client=client)
        except (Client.DoesNotExist, AttributeError):
            return render(request, 'client/no_client.html')

    return render(request, 'client/dashboard.html', {
        'routers': routers,
        'packages': packages,
        'vouchers': vouchers,
        'receipts': receipts,
        'customer_care': client.phone if client else '',
        'instructions': getattr(client, 'instructions', '') if client else '',
        'primary_color': getattr(client, 'primary_color', '#007bff') if client else '#007bff',
    })

@login_required(login_url='/accounts/login/')
def add_router(request):
    if request.method == 'POST':
        try:
            client = request.user.client
        except AttributeError:
            return redirect('/accounts/login/')

        name = request.POST.get('name', '').strip()
        ip = request.POST.get('ip', '').strip()
        if name and ip:
            Router.objects.create(client=client, name=name, ip_address=ip, api_username='', api_password='', latitude=0.0, longitude=0.0, status='offline')
        return redirect('client_dashboard')

@login_required(login_url='/accounts/login/')
def add_package(request):
    if request.method == 'POST':
        try:
            client = request.user.client
        except AttributeError:
            return redirect('/accounts/login/')

        name = request.POST.get('name', '').strip()
        price = request.POST.get('price')
        duration = request.POST.get('duration')
        devices = request.POST.get('devices')
        if name and price and duration and devices:
            Package.objects.create(client=client, name=name, price=price,
                                   duration_hours=duration, device_limit=devices)
        return redirect('client_dashboard')

@login_required(login_url='/accounts/login/')
def generate_voucher(request):
    try:
        client = request.user.client
    except AttributeError:
        return redirect('/accounts/login/')

    username = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    expiry = timezone.now() + timedelta(hours=1)

    Voucher.objects.create(client=client, username=username, password=password, expiry=expiry)
    return redirect('client_dashboard')
