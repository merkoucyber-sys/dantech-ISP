from django.db import models
from client.models import Package
from accounts.models import Client
from routers.models import Router

class WifiUser(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    username = models.CharField(max_length=20)
    password = models.CharField(max_length=20)
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True)
    phone_number = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    expiry = models.DateTimeField()
    device_mac = models.CharField(max_length=20, blank=True, default='')


class WifiUserDevice(models.Model):
    wifi_user = models.ForeignKey(WifiUser, on_delete=models.CASCADE, related_name='registered_devices')
    device_mac = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['wifi_user', 'device_mac'],
                name='unique_wifi_user_device_mac',
            ),
        ]


class PppoeUser(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='pppoe_users')
    router = models.ForeignKey(Router, on_delete=models.SET_NULL, null=True, blank=True, related_name='pppoe_users')
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=80)
    password = models.CharField(max_length=128)
    phone_number = models.CharField(max_length=20, blank=True, default='')
    is_active = models.BooleanField(default=True)
    expiry = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_mac = models.CharField(max_length=20, blank=True, default='')
    online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    data_in_mb = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    data_out_mb = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['client', 'username'], name='unique_client_pppoe_username'),
        ]


class RadiusSession(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='radius_sessions')
    username = models.CharField(max_length=80)
    router = models.ForeignKey(Router, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=128, unique=True)
    framed_ip = models.GenericIPAddressField(null=True, blank=True)
    mac_address = models.CharField(max_length=20, blank=True, default='')
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    input_mb = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    output_mb = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_online = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
