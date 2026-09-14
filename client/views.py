from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from datetime import timedelta
import random, string
from routers.models import Router
from .models import Package, Voucher, Receipt
from accounts.models import Client
from wifi.models import WifiUser


def normalize_duration_minutes(value, unit=None):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return 30

    if str(unit or '').lower() == 'hours':
        return max(1, int(round(amount * 60)))
    return max(1, int(round(amount)))


def normalize_mac(value):
    if not value:
        return ''
    cleaned = ''.join(ch for ch in str(value).upper() if ch.isalnum())
    if len(cleaned) != 12:
        return cleaned.upper()
    return ':'.join(cleaned[i:i+2] for i in range(0, 12, 2))


@login_required(login_url='/accounts/login/')
def dashboard(request):
    if request.user.is_superuser:
        routers = Router.objects.all()
        packages = Package.objects.all()
        vouchers = Voucher.objects.all()
        receipts = Receipt.objects.all()
        customer_accounts = WifiUser.objects.select_related('client', 'package').all().order_by('-expiry')
        client = None
    else:
        if not getattr(request.user, 'is_authenticated', False):
            return redirect('/accounts/login/')

        try:
            client = request.user.client
            routers = Router.objects.filter(client=client)
            packages = Package.objects.filter(client=client)
            vouchers = Voucher.objects.filter(client=client)
            receipts = Receipt.objects.filter(client=client).select_related('package').order_by('-created_at')
            customer_accounts = WifiUser.objects.filter(client=client).select_related('package').order_by('-expiry')
        except (Client.DoesNotExist, AttributeError):
            return render(request, 'client/no_client.html')

    daily_summary = list(
        receipts.annotate(day=TruncDate('created_at')).values('day').annotate(
            amount=Sum('amount'),
            sales=Count('id')
        ).order_by('-day')
    )
    weekly_summary = list(
        receipts.annotate(week=TruncWeek('created_at')).values('week').annotate(
            amount=Sum('amount'),
            sales=Count('id')
        ).order_by('-week')
    )
    monthly_summary = list(
        receipts.annotate(month=TruncMonth('created_at')).values('month').annotate(
            amount=Sum('amount'),
            sales=Count('id')
        ).order_by('-month')
    )

    active_customers = [account for account in customer_accounts if account.is_active and account.expiry > timezone.now()]
    inactive_customers = [account for account in customer_accounts if not account.is_active or account.expiry <= timezone.now()]

    return render(request, 'client/dashboard.html', {
        'routers': routers,
        'packages': packages,
        'vouchers': vouchers,
        'receipts': receipts,
        'customer_accounts': customer_accounts,
        'active_customers': active_customers,
        'inactive_customers': inactive_customers,
        'daily_summary': daily_summary,
        'weekly_summary': weekly_summary,
        'monthly_summary': monthly_summary,
        'client': client,
        'customer_care': client.phone if client else '',
        'instructions': getattr(client, 'instructions', '') if client else '',
        'billing_info': getattr(client, 'billing_info', '') if client else '',
        'primary_color': getattr(client, 'primary_color', '#007bff') if client else '#007bff',
        'wifi_name': getattr(client, 'wifi_name', '') if client else '',
        'logo': getattr(client, 'logo', '') if client else '',
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
        api_username = request.POST.get('api_username', '').strip()
        api_password = request.POST.get('api_password', '').strip()
        if name and ip:
            Router.objects.create(
                client=client,
                name=name,
                ip_address=ip,
                api_username=api_username,
                api_password=api_password,
                latitude=0.0,
                longitude=0.0,
                status='offline'
            )
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
            duration_minutes = normalize_duration_minutes(duration, request.POST.get('duration_unit'))
            Package.objects.create(client=client, name=name, price=price,
                                   duration_hours=duration_minutes, device_limit=devices)
        return redirect('client_dashboard')

@login_required(login_url='/accounts/login/')
def client_update_business(request):
    if request.method != 'POST':
        return redirect('client_dashboard')

    client = request.user.client
    client.name = request.POST.get('name', client.name).strip() or client.name
    client.wifi_name = request.POST.get('wifi_name', client.wifi_name).strip() or client.name
    client.phone = request.POST.get('phone', client.phone).strip() or client.phone
    client.instructions = request.POST.get('instructions', client.instructions) or client.instructions
    client.primary_color = request.POST.get('primary_color', client.primary_color).strip() or client.primary_color
    client.billing_info = request.POST.get('billing_info', client.billing_info) or client.billing_info

    logo = request.POST.get('logo')
    if logo:
        client.logo = logo.strip()

    client.save()
    return redirect('client_dashboard')

@login_required(login_url='/accounts/login/')
def client_update_package(request, package_id):
    package = get_object_or_404(Package, id=package_id, client=request.user.client)
    if request.method == 'POST':
        package.name = request.POST.get('name', package.name).strip() or package.name
        package.price = request.POST.get('price', package.price)
        package.duration_hours = normalize_duration_minutes(
            request.POST.get('duration', package.duration_hours or 30),
            request.POST.get('duration_unit')
        )
        package.device_limit = request.POST.get('devices', package.device_limit)
        package.save()
    return redirect('client_dashboard')


@login_required(login_url='/accounts/login/')
def client_update_payment_settings(request):
    if request.method != 'POST':
        return redirect('client_dashboard')

    client = request.user.client
    client.mpesa_shortcode = (request.POST.get('mpesa_shortcode') or client.mpesa_shortcode or '174379').strip()
    client.mpesa_consumer_key = (request.POST.get('mpesa_consumer_key') or client.mpesa_consumer_key or '').strip()
    client.mpesa_consumer_secret = (request.POST.get('mpesa_consumer_secret') or client.mpesa_consumer_secret or '').strip()
    client.mpesa_passkey = (request.POST.get('mpesa_passkey') or client.mpesa_passkey or '').strip()
    client.mpesa_callback_url = (request.POST.get('mpesa_callback_url') or client.mpesa_callback_url or '').strip()
    client.mpesa_environment = (request.POST.get('mpesa_environment') or client.mpesa_environment or 'sandbox').strip()
    client.save()
    return redirect('client_dashboard')

@login_required(login_url='/accounts/login/')
def buy_package(request):
    if request.method != 'POST':
        return redirect('client_dashboard')

    client = request.user.client
    package_id = request.POST.get('package_id')
    phone_number = request.POST.get('phone_number', '').strip()
    if not package_id or not phone_number:
        return redirect('client_dashboard')

    package = get_object_or_404(Package, id=package_id, client=client)
    Receipt.objects.create(
        client=client,
        mpesa_code='CLIENT-SETTLED',
        amount=package.price,
        package=package,
        phone_number=phone_number,
        payment_status='completed',
    )
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


@login_required(login_url='/accounts/login/')
def reactivate_customer(request):
    if request.method != 'POST':
        return redirect('client_dashboard')

    try:
        client = request.user.client
    except AttributeError:
        return redirect('/accounts/login/')

    wifi_user_id = request.POST.get('wifi_user_id')
    wifi_user = get_object_or_404(WifiUser, id=wifi_user_id, client=client)

    package = wifi_user.package or Package.objects.filter(client=client).first()
    duration_minutes = int((package.duration_hours or 60) if package else 60)
    wifi_user.is_active = True
    wifi_user.expiry = timezone.now() + timedelta(minutes=duration_minutes)
    wifi_user.save()
    return redirect('client_dashboard')


@login_required(login_url='/accounts/login/')
def generate_customer_voucher(request):
    if request.method != 'POST':
        return redirect('client_dashboard')

    try:
        client = request.user.client
    except AttributeError:
        return redirect('/accounts/login/')

    phone_number = request.POST.get('phone_number', '').strip() or request.POST.get('customer_phone', '').strip()
    duration_hours = request.POST.get('duration_hours', '1')
    username = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    expiry = timezone.now() + timedelta(hours=max(1, int(float(duration_hours) or 1)))

    Voucher.objects.create(client=client, username=username, password=password, expiry=expiry)
    if phone_number:
        Receipt.objects.create(
            client=client,
            mpesa_code=f'VOUCHER-{username}',
            amount=0,
            package=Package.objects.filter(client=client).first(),
            phone_number=phone_number,
            payment_status='completed',
        )

    return redirect('client_dashboard')
