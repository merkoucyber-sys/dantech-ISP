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
    wifi_name = models.CharField(max_length=100, blank=True, default="")
    phone = models.CharField(max_length=20)
    instructions = models.TextField(blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#007bff")
    logo = models.CharField(max_length=255, blank=True, default="")
    billing_info = models.TextField(blank=True, default="")

    mpesa_shortcode = models.CharField(max_length=20, blank=True, default="174379")
    mpesa_consumer_key = models.CharField(max_length=255, blank=True, default="")
    mpesa_consumer_secret = models.CharField(max_length=255, blank=True, default="")
    mpesa_passkey = models.CharField(max_length=255, blank=True, default="")
    mpesa_callback_url = models.URLField(blank=True, default="")
    mpesa_environment = models.CharField(max_length=20, default="sandbox")
    billing_account_type = models.CharField(max_length=20, default="till")
    till_number = models.CharField(max_length=30, blank=True, default="")
    paybill_number = models.CharField(max_length=30, blank=True, default="")
    paybill_account_number = models.CharField(max_length=100, blank=True, default="")
    bank_name = models.CharField(max_length=100, blank=True, default="")
    bank_account_name = models.CharField(max_length=150, blank=True, default="")
    bank_account_number = models.CharField(max_length=100, blank=True, default="")
    bank_branch = models.CharField(max_length=100, blank=True, default="")
    bank_swift_code = models.CharField(max_length=30, blank=True, default="")
    mpesa_validation_url = models.URLField(blank=True, default="")
    mpesa_confirmation_url = models.URLField(blank=True, default="")

    def __str__(self):
        return self.name
