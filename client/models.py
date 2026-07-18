from django.db import models
from accounts.models import Client  # your custom Client model

class Router(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    is_online = models.BooleanField(default=False)

class Package(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_hours = models.IntegerField(null=True, blank=True)
    data_limit_gb = models.IntegerField(null=True, blank=True)
    device_limit = models.IntegerField(default=1)

class Voucher(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    username = models.CharField(max_length=20)
    password = models.CharField(max_length=20)
    expiry = models.DateTimeField()
    is_active = models.BooleanField(default=True)

class Receipt(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    mpesa_code = models.CharField(max_length=20)  # M-Pesa confirmation code
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True)
    phone_number = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)

