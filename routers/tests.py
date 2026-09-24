from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Client
from .models import Router
from client.forms import RouterForm


class RouterConnectionTests(TestCase):
	def setUp(self):
		user = get_user_model().objects.create_user(username='router-owner', password='secret')
		self.client_record = Client.objects.create(user=user, name='Router Owner', phone='0700000000')
		self.router = Router.objects.create(client=self.client_record, name='Shop Router')
		self.client.force_login(user)

	def test_script_does_not_require_an_ip(self):
		response = self.client.get(reverse('router_script', args=[self.router.id]))

		self.assertEqual(response.status_code, 200)
		self.assertIn(str(self.router.connection_token), response.content.decode())
		self.assertIn('netcore-heartbeat', response.content.decode())
		self.assertIn('/system script add', response.content.decode())
		self.assertIn('/system scheduler add', response.content.decode())
		self.assertIn('ether1', response.content.decode())
		self.assertIn('ether2', response.content.decode())
		self.assertIn('netcore-hotspot', response.content.decode())
		self.assertIn('masquerade', response.content.decode())

	def test_heartbeat_marks_router_online(self):
		response = self.client.post(
			reverse('router_heartbeat', args=[self.router.connection_token]),
			{'identity': 'SHOP-ROUTER', 'serial': 'ABC123'},
		)

		self.assertEqual(response.status_code, 200)
		self.router.refresh_from_db()
		self.assertEqual(self.router.status, 'online')
		self.assertIsNotNone(self.router.last_seen)

	def test_invalid_heartbeat_token_is_rejected(self):
		response = self.client.post(reverse('router_heartbeat', args=['invalid-token']))

		self.assertEqual(response.status_code, 404)

	def test_router_form_requires_winbox_credentials(self):
		form = RouterForm(data={
			'name': 'Shop Router',
			'router_os_version': 'universal',
			'has_public_ip': '',
		})

		self.assertFalse(form.is_valid())
		self.assertIn('api_username', form.errors)
		self.assertIn('api_password', form.errors)

	def test_owner_can_delete_router(self):
		response = self.client.post(reverse('delete_router', args=[self.router.id]))

		self.assertRedirects(response, reverse('dashboard'))
		self.assertFalse(Router.objects.filter(id=self.router.id).exists())

	def test_owner_cannot_delete_another_clients_router(self):
		other_user = get_user_model().objects.create_user(username='other-owner', password='secret')
		other_client = Client.objects.create(user=other_user, name='Other Owner', phone='0711111111')
		other_router = Router.objects.create(client=other_client, name='Other Router')

		response = self.client.post(reverse('delete_router', args=[other_router.id]))

		self.assertEqual(response.status_code, 404)
		self.assertTrue(Router.objects.filter(id=other_router.id).exists())
