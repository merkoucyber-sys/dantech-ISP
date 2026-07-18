from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from .models import WifiUser
from client.models import Package, Receipt, Voucher
from accounts.models import Client
from datetime import timedelta


def resolve_client(request):
    client = getattr(request, 'client_profile', None)
    if client is None:
        client = Client.objects.first()
    return client


def wifi_login(request):
    client = resolve_client(request)
    if not client:
        return HttpResponse('No client configured.', status=404)

    packages = Package.objects.filter(client=client)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            user = WifiUser.objects.get(username=username, password=password, client=client)
            if user.is_active and user.expiry > timezone.now():
                return redirect('https://www.google.com')
            return render(request, 'wifi/expired.html')
        except WifiUser.DoesNotExist:
            return render(request, 'wifi/error.html')

    return render(request, 'wifi/login.html', {'packages': packages, 'client': client})


def create_wifi_user(client, package, phone_number, duration_hours=None):
    expiry = timezone.now() + timedelta(hours=duration_hours or package.duration_hours or 1)
    return WifiUser.objects.create(
        client=client,
        username=phone_number,
        password='wifi123',
        package=package,
        phone_number=phone_number,
        expiry=expiry,
        is_active=True,
    )


def mpesa_payment(request, package_id):
    client = resolve_client(request)
    if not client:
        return HttpResponse('No client configured.', status=404)

    package = get_object_or_404(Package, id=package_id, client=client)
    if request.method != 'POST':
        return redirect('wifi_login')

    phone = request.POST.get('phone_number')
    mpesa_code = 'MPESA123456'
    create_wifi_user(client, package, phone, duration_hours=package.duration_hours)
    Receipt.objects.create(
        client=client,
        mpesa_code=mpesa_code,
        amount=package.price,
        package=package,
        phone_number=phone,
    )

    return redirect('https://www.google.com')


def buy_package(request):
    return mpesa_payment(request, request.POST.get('package_id'))


def activate_voucher(request):
    if request.method != 'POST':
        return redirect('wifi_login')

    username = request.POST.get('username')
    password = request.POST.get('password')
    phone_number = request.POST.get('phone_number')

    voucher = Voucher.objects.filter(
        username=username,
        password=password,
        is_active=True,
        expiry__gt=timezone.now()
    ).first()
    if not voucher:
        return render(request, 'wifi/error.html')

    package = Package.objects.filter(client=voucher.client).first()
    if not package:
        return render(request, 'wifi/error.html')

    create_wifi_user(voucher.client, package, phone_number, duration_hours=package.duration_hours)
    voucher.is_active = False
    voucher.save()

    Receipt.objects.create(
        client=voucher.client,
        mpesa_code='VOUCHER',
        amount=0,
        package=package,
        phone_number=phone_number,
    )

    return redirect('https://www.google.com')
