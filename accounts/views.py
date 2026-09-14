from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
import random, string

from .models import Client, User
from .forms import ClientRegistrationForm
from routers.models import Router
from client.models import Package, Voucher, Receipt
from wifi.models import WifiUser


def normalize_package_duration(value, unit=None):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return 30

    if str(unit or '').lower() == 'hours':
        return max(1, int(round(amount * 60)))
    return max(1, int(round(amount)))


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


def register_client(request):
    if request.method == 'POST':
        form = ClientRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            name = form.cleaned_data['name']
            phone = form.cleaned_data['phone']
            user = User.objects.create_user(username=username, password=password)
            user.is_client = True
            user.save()
            Client.objects.create(user=user, name=name, phone=phone)
            login(request, user)
            return redirect('client_dashboard')
    else:
        form = ClientRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


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
                user.is_active = True
                user.save()
                Client.objects.create(user=user, name=name, phone=phone)
            return redirect('superuser_dashboard')

        if action == 'edit_client':
            client_id = request.POST.get('client_id')
            client = Client.objects.filter(id=client_id).first()
            if client:
                client.name = (request.POST.get('client_name') or client.name).strip()
                client.phone = (request.POST.get('client_phone') or client.phone).strip()
                client.wifi_name = (request.POST.get('wifi_name') or client.wifi_name or '').strip()
                client.billing_info = (request.POST.get('billing_info') or client.billing_info or '').strip()
                client.instructions = (request.POST.get('instructions') or client.instructions or '').strip()
                client.save()
            return redirect('superuser_dashboard')

        if action == 'delete_client':
            client_id = request.POST.get('client_id')
            client = Client.objects.filter(id=client_id).first()
            if client:
                Router.objects.filter(client=client).delete()
                Package.objects.filter(client=client).delete()
                Voucher.objects.filter(client=client).delete()
                Receipt.objects.filter(client=client).delete()
                WifiUser.objects.filter(client=client).delete()

                if client.user_id:
                    client.user.delete()
                else:
                    client.delete()
            return redirect('superuser_dashboard')

        if action == 'toggle_client_active':
            client_id = request.POST.get('client_id')
            client = Client.objects.filter(id=client_id).first()
            if client:
                client.user.is_active = not client.user.is_active
                client.user.save()
            return redirect('superuser_dashboard')

        if action == 'reset_client_password':
            client_id = request.POST.get('client_id')
            new_password = request.POST.get('new_password', '').strip()
            client = Client.objects.filter(id=client_id).first()
            if client and new_password:
                client.user.set_password(new_password)
                client.user.save()
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

        if action == 'delete_router':
            router_id = request.POST.get('router_id')
            router = Router.objects.filter(id=router_id).first()
            if router:
                router.delete()
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
                        duration_hours=normalize_package_duration(duration, request.POST.get('duration_unit')),
                        device_limit=devices,
                    )
            return redirect('superuser_dashboard')

        if action == 'delete_package':
            package_id = request.POST.get('package_id')
            package = Package.objects.filter(id=package_id).first()
            if package:
                package.delete()
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

    clients = Client.objects.select_related('user').all()
    routers = Router.objects.select_related('client').all()
    packages = Package.objects.select_related('client').all()
    vouchers = Voucher.objects.select_related('client').all()
    receipts = Receipt.objects.select_related('client', 'package').all()
    inactive_clients = [client for client in clients if not client.user.is_active]

    return render(request, 'accounts/superuser_dashboard.html', {
        'clients': clients,
        'routers': routers,
        'packages': packages,
        'vouchers': vouchers,
        'receipts': receipts,
        'inactive_clients': inactive_clients,
        'active_clients': sum(1 for client in clients if client.user.is_active),
        'total_packages': packages.count(),
        'pending_payments': len(inactive_clients),
    })
