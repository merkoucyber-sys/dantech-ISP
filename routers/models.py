from django.db import models
import uuid
from accounts.models import Client


class Router(models.Model):
    ROUTER_OS_CHOICES = (
        ('universal', 'Universal'),
        ('routeros7', 'RouterOS 7'),
        ('routeros6', 'RouterOS 6'),
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='routers')
    name = models.CharField(max_length=100)
    api_username = models.CharField(max_length=50, default='admin')
    api_password = models.CharField(max_length=128, default='')
    router_os_version = models.CharField(max_length=20, choices=ROUTER_OS_CHOICES, default='universal')
    has_public_ip = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    latitude = models.FloatField(default=0.0, blank=True)
    longitude = models.FloatField(default=0.0, blank=True)
    status = models.CharField(max_length=20, default='offline')
    connection_token = models.CharField(max_length=64, unique=True, default=uuid.uuid4, editable=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
