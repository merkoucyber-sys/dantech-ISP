from django.db import models
from client.models import Package
from accounts.models import Client

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
