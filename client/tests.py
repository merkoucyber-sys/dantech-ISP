from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Client
from client.models import Package, Receipt, Voucher
from wifi.models import WifiUser, WifiUserDevice


class ClientDashboardTests(TestCase):
    def test_dashboard_renders_for_client_without_legacy_logo_fields(self):
        User = get_user_model()
        user = User.objects.create_user(username='client', password='secret123', is_client=True)
        Client.objects.create(user=user, name='Test Client', phone='0712345678')

        self.client.force_login(user)
        response = self.client.get(reverse('client_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/dashboard.html')

    def test_dashboard_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('client_dashboard'))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/dashboard/')

    def test_buy_package_creates_receipt_for_client(self):
        User = get_user_model()
        user = User.objects.create_user(username='buyer', password='secret123', is_client=True)
        client = Client.objects.create(user=user, name='Buyer Client', phone='0712345678')
        package = Package.objects.create(client=client, name='Basic', price='100.00', duration_hours=24, device_limit=5)

        self.client.force_login(user)
        response = self.client.post(reverse('buy_package'), {
            'package_id': package.id,
            'phone_number': '0712345678',
        })

        self.assertEqual(response.status_code, 302)
        receipt = Receipt.objects.get(client=client)
        self.assertEqual(receipt.package, package)
        self.assertEqual(receipt.amount, Decimal('100.00'))

    def test_activate_voucher_creates_wifi_user(self):
        User = get_user_model()
        user = User.objects.create_user(username='voucher-owner', password='secret123', is_client=True)
        client = Client.objects.create(user=user, name='Voucher Client', phone='0712345678')
        package = Package.objects.create(client=client, name='Basic', price='100.00', duration_hours=24, device_limit=5)
        voucher = package.client.voucher_set.create(
            username='ABC123',
            password='xyz789',
            expiry='2099-01-01T00:00:00Z',
            is_active=True,
        )

        response = self.client.post(reverse('activate_voucher'), {
            'username': voucher.username,
            'password': voucher.password,
            'phone_number': '0712345678',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(WifiUser.objects.filter(username='0712345678').exists())

    def test_client_can_update_business_settings(self):
        User = get_user_model()
        user = User.objects.create_user(username='brand-owner', password='secret123', is_client=True)
        client = Client.objects.create(user=user, name='Brand Client', phone='0712345678', instructions='Old text')

        self.client.force_login(user)
        response = self.client.post(reverse('client_update_business'), {
            'name': 'Sunset WiFi',
            'wifi_name': 'Sunset Internet',
            'phone': '0711112222',
            'instructions': 'Updated customer info',
            'primary_color': '#123456',
            'billing_info': 'Pay by M-Pesa only',
        })

        self.assertEqual(response.status_code, 302)
        client.refresh_from_db()
        self.assertEqual(client.name, 'Sunset WiFi')
        self.assertEqual(client.wifi_name, 'Sunset Internet')
        self.assertEqual(client.phone, '0711112222')
        self.assertEqual(client.instructions, 'Updated customer info')
        self.assertEqual(client.primary_color, '#123456')
        self.assertEqual(client.billing_info, 'Pay by M-Pesa only')

    def test_client_can_update_package_details(self):
        User = get_user_model()
        user = User.objects.create_user(username='package-owner', password='secret123', is_client=True)
        client = Client.objects.create(user=user, name='Package Client', phone='0712345678')
        package = Package.objects.create(client=client, name='Starter', price='100.00', duration_hours=24, device_limit=1)

        self.client.force_login(user)
        response = self.client.post(reverse('client_update_package', args=[package.id]), {
            'name': 'Premium Starter',
            'price': '150.00',
            'duration': '48',
            'devices': '3',
        })

        self.assertEqual(response.status_code, 302)
        package.refresh_from_db()
        self.assertEqual(package.name, 'Premium Starter')
        self.assertEqual(str(package.price), '150.00')
        self.assertEqual(package.duration_hours, 48)
        self.assertEqual(package.device_limit, 3)

    def test_client_can_update_package_using_hours(self):
        User = get_user_model()
        user = User.objects.create_user(username='hourly-package-owner', password='secret123', is_client=True)
        client = Client.objects.create(user=user, name='Hourly Package Client', phone='0712345678')
        package = Package.objects.create(client=client, name='Starter', price='100.00', duration_hours=30, device_limit=1)

        self.client.force_login(user)
        response = self.client.post(reverse('client_update_package', args=[package.id]), {
            'name': 'Hourly Starter',
            'price': '200.00',
            'duration': '2',
            'duration_unit': 'hours',
            'devices': '5',
        })

        self.assertEqual(response.status_code, 302)
        package.refresh_from_db()
        self.assertEqual(package.name, 'Hourly Starter')
        self.assertEqual(str(package.price), '200.00')
        self.assertEqual(package.duration_hours, 120)
        self.assertEqual(package.duration_display, '2 hours')
        self.assertEqual(package.device_limit, 5)

    def test_superuser_can_toggle_client_status_and_reset_password(self):
        User = get_user_model()
        admin = User.objects.create_superuser(username='admin', password='adminpass123')
        client_user = User.objects.create_user(username='client-user', password='oldpass123', is_client=True)
        client = Client.objects.create(user=client_user, name='Managed Client', phone='0712345678')

        self.client.force_login(admin)

        response = self.client.post(reverse('superuser_dashboard'), {
            'action': 'toggle_client_active',
            'client_id': client.id,
        })
        self.assertEqual(response.status_code, 302)
        client_user.refresh_from_db()
        self.assertFalse(client_user.is_active)

        response = self.client.post(reverse('superuser_dashboard'), {
            'action': 'reset_client_password',
            'client_id': client.id,
            'new_password': 'newsecure456',
        })
        self.assertEqual(response.status_code, 302)
        client_user.refresh_from_db()
        self.assertTrue(client_user.check_password('newsecure456'))

    def test_superuser_edit_client_handles_missing_optional_fields(self):
        User = get_user_model()
        admin = User.objects.create_superuser(username='admin2', password='adminpass456')
        client_user = User.objects.create_user(username='client-edit', password='oldpass123', is_client=True)
        client = Client.objects.create(
            user=client_user,
            name='Edit Client',
            phone='0712345678',
            wifi_name='Old WiFi',
            billing_info='Old billing',
            instructions='Old instructions',
        )

        self.client.force_login(admin)
        response = self.client.post(reverse('superuser_dashboard'), {
            'action': 'edit_client',
            'client_id': client.id,
            'client_name': 'Updated Client',
            'client_phone': '0798765432',
            'wifi_name': '',
            'billing_info': '',
            'instructions': '',
        })

        self.assertEqual(response.status_code, 302)
        client.refresh_from_db()
        self.assertEqual(client.name, 'Updated Client')
        self.assertEqual(client.phone, '0798765432')
        self.assertEqual(client.wifi_name, 'Old WiFi')
        self.assertEqual(client.billing_info, 'Old billing')
        self.assertEqual(client.instructions, 'Old instructions')

    def test_superuser_can_delete_client_with_related_data(self):
        User = get_user_model()
        admin = User.objects.create_superuser(username='admin3', password='adminpass789')
        client_user = User.objects.create_user(username='client-delete', password='oldpass123', is_client=True)
        client = Client.objects.create(user=client_user, name='Delete Client', phone='0712345678')
        router = client.routers.create(
            name='Router 1',
            ip_address='10.0.0.1',
            api_username='',
            api_password='',
            latitude=0.0,
            longitude=0.0,
            status='offline',
        )
        package = Package.objects.create(client=client, name='Starter', price='100.00', duration_hours=30, device_limit=1)
        voucher = Voucher.objects.create(client=client, username='ABC123', password='pass123', expiry='2099-01-01T00:00:00Z')
        receipt = Receipt.objects.create(client=client, mpesa_code='TEST-DEL', amount='100.00', package=package, phone_number='0712345678')
        WifiUser.objects.create(client=client, username='0712345678', password='wifi123', package=package, phone_number='0712345678', expiry='2099-01-01T00:00:00Z')

        self.client.force_login(admin)
        response = self.client.post(reverse('superuser_dashboard'), {
            'action': 'delete_client',
            'client_id': client.id,
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Client.objects.filter(id=client.id).exists())
        self.assertFalse(User.objects.filter(username='client-delete').exists())
        self.assertFalse(router.__class__.objects.filter(id=router.id).exists())
        self.assertFalse(package.__class__.objects.filter(id=package.id).exists())
        self.assertFalse(voucher.__class__.objects.filter(id=voucher.id).exists())
        self.assertFalse(receipt.__class__.objects.filter(id=receipt.id).exists())
        self.assertFalse(WifiUser.objects.filter(client_id=client.id).exists())

    def test_client_dashboard_includes_customer_activity_summary(self):
        User = get_user_model()
        user = User.objects.create_user(username='customer-list', password='secret123', is_client=True)
        client = Client.objects.create(user=user, name='Customer List Client', phone='0712345678')
        package = Package.objects.create(client=client, name='Basic', price='150.00', duration_hours=60, device_limit=1)
        WifiUser.objects.create(
            client=client,
            username='0712345678',
            password='wifi123',
            package=package,
            phone_number='0712345678',
            expiry='2099-01-01T00:00:00Z',
            is_active=True,
            device_mac='AA:BB:CC:DD:EE:FF',
        )
        WifiUser.objects.create(
            client=client,
            username='0711111111',
            password='wifi456',
            package=package,
            phone_number='0711111111',
            expiry='2020-01-01T00:00:00Z',
            is_active=False,
            device_mac='11:22:33:44:55:66',
        )
        Receipt.objects.create(client=client, mpesa_code='TXN-1', amount='150.00', package=package, phone_number='0712345678')

        self.client.force_login(user)
        response = self.client.get(reverse('client_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('customer_accounts', response.context)
        self.assertIn('daily_summary', response.context)
        self.assertGreater(len(response.context['customer_accounts']), 0)
        self.assertGreater(len(response.context['daily_summary']), 0)

    def test_client_can_update_payment_settings(self):
        User = get_user_model()
        user = User.objects.create_user(username='payment-owner', password='secret123', is_client=True)
        client = Client.objects.create(user=user, name='Payment Client', phone='0712345678')

        self.client.force_login(user)
        response = self.client.post(reverse('client_update_payment_settings'), {
            'mpesa_shortcode': '174379',
            'mpesa_consumer_key': 'demo-key',
            'mpesa_consumer_secret': 'demo-secret',
            'mpesa_passkey': 'demo-passkey',
            'mpesa_callback_url': 'https://example.com/wifi/mpesa-callback/',
            'mpesa_environment': 'sandbox',
        })

        self.assertEqual(response.status_code, 302)
        client.refresh_from_db()
        self.assertEqual(client.mpesa_shortcode, '174379')
        self.assertEqual(client.mpesa_consumer_key, 'demo-key')
        self.assertEqual(client.mpesa_environment, 'sandbox')

    def test_wifi_login_rejects_unexpected_device_mac(self):
        User = get_user_model()
        user = User.objects.create_user(username='mac-owner', password='secret123', is_client=True)
        client = Client.objects.create(user=user, name='Mac Client', phone='0712345678')
        package = Package.objects.create(client=client, name='Basic', price='200.00', duration_hours=60, device_limit=1)
        wifi_user = WifiUser.objects.create(
            client=client,
            username='0712345678',
            password='wifi123',
            package=package,
            phone_number='0712345678',
            expiry='2099-01-01T00:00:00Z',
            is_active=True,
            device_mac='AA:BB:CC:DD:EE:FF',
        )

        response = self.client.post(reverse('wifi_login'), {
            'username': wifi_user.username,
            'password': wifi_user.password,
            'device_mac': '00:11:22:33:44:55',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'device')

    def test_purchase_preserves_device_mac_for_wifi_account(self):
        User = get_user_model()
        user = User.objects.create_user(username='purchase-owner', password='secret123', is_client=True)
        client = Client.objects.create(user=user, name='Purchase Client', phone='0712345678')
        package = Package.objects.create(client=client, name='Basic', price='200.00', duration_hours=60, device_limit=1)

        response = self.client.post(reverse('process_payment'), {
            'package': package.id,
            'phone_number': '0712345678',
            'device_mac': 'aa-bb-cc-dd-ee-ff',
            'payment_method': 'mpesa',
        })

        self.assertEqual(response.status_code, 200)
        receipt = Receipt.objects.get(client=client)
        self.assertEqual(receipt.device_mac, 'AA:BB:CC:DD:EE:FF')

    def test_purchase_can_start_without_device_mac(self):
        User = get_user_model()
        user = User.objects.create_user(username='no-mac-owner', password='secret123', is_client=True)
        client = Client.objects.create(user=user, name='No MAC Client', phone='0712345678')
        package = Package.objects.create(client=client, name='Basic', price='100.00', duration_hours=30, device_limit=1)

        response = self.client.post(reverse('process_payment'), {
            'package': package.id,
            'phone_number': '0712345678',
            'payment_method': 'mpesa',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Receipt.objects.get(client=client).device_mac, '')

    def test_package_device_limit_allows_only_configured_devices(self):
        User = get_user_model()
        user = User.objects.create_user(username='device-owner', password='secret123', is_client=True)
        client = Client.objects.create(user=user, name='Device Client', phone='0712345678')
        package = Package.objects.create(client=client, name='Two Device', price='200.00', duration_hours=60, device_limit=2)
        wifi_user = WifiUser.objects.create(
            client=client,
            username='0712345678',
            password='wifi123',
            package=package,
            phone_number='0712345678',
            expiry='2099-01-01T00:00:00Z',
            device_mac='AA:BB:CC:DD:EE:FF',
        )
        WifiUserDevice.objects.create(wifi_user=wifi_user, device_mac=wifi_user.device_mac)

        second = self.client.post(reverse('wifi_login'), {
            'username': wifi_user.username,
            'password': wifi_user.password,
            'device_mac': '11:22:33:44:55:66',
        })
        self.assertEqual(second.status_code, 302)
        self.assertEqual(wifi_user.registered_devices.count(), 2)

        third = self.client.post(reverse('wifi_login'), {
            'username': wifi_user.username,
            'password': wifi_user.password,
            'device_mac': '77:88:99:AA:BB:CC',
        })
        self.assertEqual(third.status_code, 200)
        self.assertContains(third, 'allows only 2 registered device')
