from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Client
from client.models import Package, Receipt
from wifi.models import WifiUser


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
