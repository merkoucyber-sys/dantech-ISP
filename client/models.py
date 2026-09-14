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

    @property
    def duration_display(self):
        minutes = int(self.duration_hours or 0)
        if minutes >= 60 and minutes % 60 == 0:
            hours = minutes // 60
            return f"{hours} hour" if hours == 1 else f"{hours} hours"
        return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"

class Voucher(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    username = models.CharField(max_length=20)
    password = models.CharField(max_length=20)
    expiry = models.DateTimeField()
    is_active = models.BooleanField(default=True)

class Receipt(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    mpesa_code = models.CharField(max_length=100)  # Checkout or confirmation code
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True)
    phone_number = models.CharField(max_length=15)
    device_mac = models.CharField(max_length=20, blank=True, default='')
    payment_status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

