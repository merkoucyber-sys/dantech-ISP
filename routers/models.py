from django.db import models
from accounts.models import Client


class Router(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='routers')
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    api_username = models.CharField(max_length=50)
    api_password = models.CharField(max_length=50)
    latitude = models.FloatField()
    longitude = models.FloatField()
    status = models.CharField(max_length=20, default='offline')

    def __str__(self):
        return f"{self.name} ({self.ip_address})"
