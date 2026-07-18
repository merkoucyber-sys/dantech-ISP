from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Add extra fields if needed
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_client = models.BooleanField(default=False)

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="client")
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    instructions = models.TextField(blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#007bff")  # Default to Bootstrap primary color