from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import WifiUser, WifiUserDevice
from client.models import Package, Receipt, Voucher
from accounts.models import Client
from datetime import timedelta, datetime
import json
import requests
import os
import base64


def resolve_client(request):
    client = getattr(request, 'client_profile', None)
    if client is None:
        client = Client.objects.first()
    return client


def normalize_device_mac(value):
    if not value:
        return ''
    cleaned = ''.join(ch for ch in str(value).upper() if ch.isalnum())
    if len(cleaned) != 12:
        return cleaned
    return ':'.join(cleaned[i:i+2] for i in range(0, 12, 2))


def wifi_login(request):
    client = resolve_client(request)
    if not client:
        return HttpResponse('No client configured.', status=404)

    packages = Package.objects.filter(client=client)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        submitted_mac = normalize_device_mac(request.POST.get('device_mac'))
        try:
            user = WifiUser.objects.get(username=username, password=password, client=client)
            if not submitted_mac:
                return render(request, 'wifi/error.html', {
                    'error': 'Device MAC address is required for this account.'
                })

            registered_devices = user.registered_devices.all()
            if user.device_mac and not registered_devices.exists():
                WifiUserDevice.objects.get_or_create(
                    wifi_user=user,
                    device_mac=normalize_device_mac(user.device_mac),
                )
                registered_devices = user.registered_devices.all()

            if not registered_devices.filter(device_mac=submitted_mac).exists():
                device_limit = max(1, user.package.device_limit if user.package else 1)
                if registered_devices.count() >= device_limit:
                    return render(request, 'wifi/error.html', {
                        'error': f'This WiFi package allows only {device_limit} registered device(s).'
                    })
                WifiUserDevice.objects.create(wifi_user=user, device_mac=submitted_mac)
            if user.is_active and user.expiry > timezone.now():
                return redirect('https://www.google.com')
            return render(request, 'wifi/expired.html')
        except WifiUser.DoesNotExist:
            return render(request, 'wifi/error.html', {'error': 'Invalid WiFi credentials.'})

    return render(request, 'wifi/login.html', {'packages': packages, 'client': client})


def wifi_checkout(request):
    """Display WiFi package checkout page"""
    client = resolve_client(request)
    if not client:
        return HttpResponse('No client configured.', status=404)

    packages = Package.objects.filter(client=client)
    
    context = {
        'packages': packages,
        'client': client,
    }
    
    return render(request, 'wifi/checkout.html', context)


def create_wifi_user(client, package, phone_number, duration_hours=None, device_mac=None):
    """Create a WiFi user account with expiry in minutes."""
    duration_minutes = int(duration_hours if duration_hours is not None else (package.duration_hours or 3))
    if duration_minutes <= 0:
        duration_minutes = 3

    expiry = timezone.now() + timedelta(minutes=duration_minutes)
    wifi_user = WifiUser.objects.create(
        client=client,
        username=phone_number,
        password='wifi123',
        package=package,
        phone_number=phone_number,
        expiry=expiry,
        is_active=True,
        device_mac=normalize_device_mac(device_mac),
    )
    if wifi_user.device_mac:
        WifiUserDevice.objects.get_or_create(
            wifi_user=wifi_user,
            device_mac=wifi_user.device_mac,
        )

    from routers.mitrotic_api import enforce_wifi_account_on_client_routers
    router_sync_succeeded, router_results = enforce_wifi_account_on_client_routers(wifi_user)
    if not router_sync_succeeded:
        wifi_user.delete()
        failed_routers = ', '.join(
            router.name for router, success, message in router_results if not success
        )
        raise RuntimeError(
            f'WiFi account could not be secured on router(s): {failed_routers}'
        )
    return wifi_user


@require_POST
def process_payment(request):
    """Handle payment processing - main entry point"""
    client = resolve_client(request)
    if not client:
        return HttpResponse('No client configured', status=404)

    try:
        package_id = request.POST.get('package')
        phone_number = request.POST.get('phone_number', '').strip()
        device_mac = normalize_device_mac(request.POST.get('device_mac'))
        payment_method = request.POST.get('payment_method', 'mpesa')
        
        # Validate inputs
        if not package_id or not phone_number:
            return render(request, 'wifi/checkout.html', {
                'error': 'Package and phone number are required',
                'packages': Package.objects.filter(client=client)
            })
        
        package = get_object_or_404(Package, id=package_id, client=client)
        
        # Normalize phone number (add country code if needed)
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif not phone_number.startswith('254'):
            phone_number = '254' + phone_number
        
        # Always use M-Pesa for this simplified flow
        return initiate_mpesa_stk_push(request, client, package, phone_number, device_mac)
            
    except Package.DoesNotExist:
        return render(request, 'wifi/checkout.html', {
            'error': 'Package not found',
            'packages': Package.objects.filter(client=client)
        })
    except Exception as e:
        return render(request, 'wifi/checkout.html', {
            'error': f'Error: {str(e)}',
            'packages': Package.objects.filter(client=client)
        })


def initiate_mpesa_stk_push(request, client, package, phone_number, device_mac=''):
    """
    Initiate M-Pesa STK Push - prompts user to enter M-Pesa PIN on their phone
    """
    try:
        # Create a receipt record with PENDING status
        receipt = Receipt.objects.create(
            client=client,
            mpesa_code=f'STK-{phone_number}-{timezone.now().timestamp()}',
            amount=package.price,
            package=package,
            phone_number=phone_number,
            device_mac=device_mac,
            payment_status='pending',
        )

        # Initiate STK Push to phone
        stk_result = send_mpesa_stk_push(phone_number, package.price, client=client)
        
        if stk_result.get('success'):
            # STK Push sent successfully
            receipt.mpesa_code = stk_result.get('checkout_request_id', receipt.mpesa_code)
            receipt.save()
            
            context = {
                'receipt': receipt,
                'package': package,
                'phone_number': phone_number,
                'client': client,
                'amount': package.price,
                'checkout_request_id': stk_result.get('checkout_request_id'),
            }
            
            return render(request, 'wifi/mpesa_waiting.html', context)
        else:
            # STK Push failed
            receipt.delete()
            return render(request, 'wifi/payment_failed.html', {
                'error': stk_result.get('error', 'Failed to send M-Pesa prompt'),
                'client': client,
            })
            
    except Exception as e:
        return render(request, 'wifi/payment_failed.html', {
            'error': f'Payment initiation error: {str(e)}',
            'client': client,
        })


def get_mpesa_access_token(client=None):
    consumer_key = getattr(client, 'mpesa_consumer_key', '') or settings.MPESA_CONSUMER_KEY
    consumer_secret = getattr(client, 'mpesa_consumer_secret', '') or settings.MPESA_CONSUMER_SECRET
    passkey = getattr(client, 'mpesa_passkey', '') or settings.MPESA_PASSKEY
    environment = getattr(client, 'mpesa_environment', '') or settings.MPESA_ENVIRONMENT

    if (
        consumer_key.startswith('your_')
        or consumer_secret.startswith('your_')
        or passkey.startswith('your_')
    ):
        raise ValueError('Set your Safaricom Daraja credentials in the payment settings first.')

    base_url = 'https://api.safaricom.co.ke' if environment == 'production' else 'https://sandbox.safaricom.co.ke'
    url = f'{base_url}/oauth/v1/generate?grant_type=client_credentials'
    response = requests.get(url, auth=(consumer_key, consumer_secret), timeout=30)
    response.raise_for_status()
    data = response.json()
    return data['access_token']


def send_mpesa_stk_push(phone_number, amount, client=None):
    """
    Send M-Pesa STK Push to user's phone.
    Falls back to simulated mode only if the Daraja credentials are not configured.
    """
    shortcode = getattr(client, 'mpesa_shortcode', '') or settings.MPESA_SHORTCODE
    consumer_key = getattr(client, 'mpesa_consumer_key', '') or settings.MPESA_CONSUMER_KEY
    consumer_secret = getattr(client, 'mpesa_consumer_secret', '') or settings.MPESA_CONSUMER_SECRET
    passkey = getattr(client, 'mpesa_passkey', '') or settings.MPESA_PASSKEY
    callback_url = getattr(client, 'mpesa_callback_url', '') or settings.MPESA_CALLBACK_URL
    environment = getattr(client, 'mpesa_environment', '') or settings.MPESA_ENVIRONMENT

    if consumer_key.startswith('your_') or consumer_secret.startswith('your_'):
        return {
            'success': True,
            'checkout_request_id': f'ws_CO_{phone_number}_{timezone.now().timestamp()}',
            'message': 'Mock STK Push used because Daraja credentials are not configured yet.'
        }

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(
        f"{shortcode}{passkey}{timestamp}".encode()
    ).decode()

    payload = {
        'BusinessShortCode': shortcode,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': int(amount),
        'PartyA': phone_number,
        'PartyB': shortcode,
        'PhoneNumber': phone_number,
        'CallBackURL': callback_url,
        'AccountReference': 'WiFi Purchase',
        'TransactionDesc': 'WiFi Package Purchase',
    }

    base_url = 'https://api.safaricom.co.ke' if environment == 'production' else 'https://sandbox.safaricom.co.ke'
    url = f'{base_url}/mpesa/stkpush/v1/processrequest'
    headers = {
        'Authorization': f"Bearer {get_mpesa_access_token(client=client)}",
        'Content-Type': 'application/json',
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    result = response.json()

    return {
        'success': result.get('ResponseCode') == '0',
        'checkout_request_id': result.get('CheckoutRequestID'),
        'error': result.get('ResponseDescription'),
        'message': result.get('CustomerMessage'),
    }


def handle_cash_payment(request, client, package, phone_number, device_mac=''):
    """Handle cash payment - create pending user"""
    # Create receipt with CASH payment method
    receipt = Receipt.objects.create(
        client=client,
        mpesa_code=f'CASH-{phone_number}',
        amount=package.price,
        package=package,
        phone_number=phone_number,
        device_mac=device_mac,
    )
    
    # Show pending payment confirmation
    context = {
        'receipt': receipt,
        'package': package,
        'phone_number': phone_number,
        'client': client,
        'payment_method': 'cash',
    }
    
    return render(request, 'wifi/payment_pending.html', context)


@csrf_exempt
@require_POST
def mpesa_callback(request):
    """Handle M-Pesa payment callback from Safaricom"""
    try:
        # Parse callback data
        data = json.loads(request.body)
        
        # Extract payment details
        result_code = data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
        result_desc = data.get('Body', {}).get('stkCallback', {}).get('ResultDesc')
        metadata = data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {})
        
        # Update receipt based on payment status
        if result_code == 0:
            # Payment successful
            items = metadata.get('Item', [])
            mpesa_code = None
            amount = None
            phone = None
            
            for item in items:
                if item.get('Name') == 1:  # M-Pesa code
                    mpesa_code = item.get('Value')
                elif item.get('Name') == 2:  # Amount
                    amount = item.get('Value')
                elif item.get('Name') == 4:  # Phone
                    phone = item.get('Value')
            
            # Update receipt
            receipt = Receipt.objects.filter(mpesa_code='PENDING', phone_number=phone).first()
            if not receipt:
                checkout_request_id = data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
                receipt = Receipt.objects.filter(mpesa_code=checkout_request_id, payment_status='pending').first()
            if receipt:
                receipt.mpesa_code = mpesa_code or 'CONFIRMED'
                receipt.payment_status = 'completed'
                receipt.save()
                
                # Create WiFi user
                create_wifi_user(
                    receipt.client,
                    receipt.package,
                    phone,
                    device_mac=receipt.device_mac,
                )
                
                return JsonResponse({'success': True})
        
        checkout_request_id = data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
        receipt = Receipt.objects.filter(mpesa_code=checkout_request_id, payment_status='pending').first()
        if receipt:
            receipt.payment_status = 'failed'
            receipt.save(update_fields=['payment_status'])
        return JsonResponse({'error': result_desc or 'Payment failed'}, status=400)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def payment_success(request, receipt_id):
    """Display payment success page"""
    receipt = get_object_or_404(Receipt, id=receipt_id)
    
    context = {
        'receipt': receipt,
        'package': receipt.package,
        'phone_number': receipt.phone_number,
        'client': receipt.client,
        'credentials': {
            'username': receipt.phone_number,
            'password': 'wifi123',
        }
    }
    
    return render(request, 'wifi/payment_success.html', context)


def payment_failed(request):
    """Display payment failed page"""
    return render(request, 'wifi/payment_failed.html')


def activate_voucher(request):
    """Activate voucher for WiFi access"""
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
        return render(request, 'wifi/error.html', {
            'error': 'Invalid or expired voucher'
        })

    package = Package.objects.filter(client=voucher.client).first()
    if not package:
        return render(request, 'wifi/error.html', {
            'error': 'No packages available'
        })

    # Create WiFi user from voucher
    wifi_user = create_wifi_user(voucher.client, package, phone_number, duration_hours=package.duration_hours)
    
    # Deactivate voucher
    voucher.is_active = False
    voucher.save()

    # Create receipt record
    Receipt.objects.create(
        client=voucher.client,
        mpesa_code=f'VOUCHER-{voucher.username}',
        amount=0,
        package=package,
        phone_number=phone_number,
    )

    # Show success and redirect
    if request.user.is_authenticated and getattr(request.user, 'is_client', False):
        return redirect('client_dashboard')
    return redirect('wifi_login')


def check_payment_status(request, receipt_id):
    """Check M-Pesa payment status (AJAX endpoint)"""
    try:
        receipt = Receipt.objects.get(id=receipt_id)
        
        # Check if payment has been confirmed
        # In production, query M-Pesa API for actual status
        # For now, we simulate based on receipt status
        
        if receipt.payment_status == 'pending':
            return JsonResponse({
                'status': 'pending',
                'message': 'Waiting for M-Pesa confirmation...'
            })
        elif receipt.payment_status == 'failed':
            return JsonResponse({
                'status': 'failed',
                'message': 'Payment was not completed.'
            })
        elif receipt.payment_status == 'completed':
            return JsonResponse({
                'status': 'completed',
                'message': 'Payment successful!'
            })
        elif receipt.mpesa_code == 'PENDING':
            time_diff = (timezone.now() - receipt.created_at).total_seconds()
            if time_diff > 5:  # Auto-confirm after 5 seconds for demo
                # Auto-create WiFi user
                create_wifi_user(
                    receipt.client,
                    receipt.package,
                    receipt.phone_number,
                    device_mac=receipt.device_mac,
                )
                receipt.mpesa_code = f'AUTO-CONFIRMED-{timezone.now().timestamp()}'
                receipt.save()
                
                return JsonResponse({
                    'status': 'completed',
                    'message': 'Payment confirmed!'
                })
            else:
                return JsonResponse({
                    'status': 'pending',
                    'message': 'Waiting for M-Pesa confirmation...'
                })
        else:
            # Payment confirmed
            return JsonResponse({
                'status': 'completed',
                'message': 'Payment successful!'
            })
            
    except Receipt.DoesNotExist:
        return JsonResponse({
            'status': 'failed',
            'error': 'Transaction not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
