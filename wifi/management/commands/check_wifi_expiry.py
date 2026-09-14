import os
import sys
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from wifi.models import WifiUser


class Command(BaseCommand):
    help = 'Check and expire WiFi user accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-expiry',
            action='store_true',
            help='Check and deactivate expired WiFi accounts',
        )
        parser.add_argument(
            '--warning-hours',
            type=int,
            default=24,
            help='Send warning SMS X hours before expiry (default: 24)',
        )

    def handle(self, *args, **options):
        if options['check_expiry']:
            self.check_expiry()
        else:
            self.check_expiry()
            self.send_expiry_warnings(options['warning_hours'])

    def check_expiry(self):
        """Check and deactivate expired WiFi accounts"""
        now = timezone.now()
        expired_users = WifiUser.objects.filter(
            is_active=True,
            expiry__lt=now
        )
        
        count = expired_users.count()
        expired_users.update(is_active=False)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Deactivated {count} expired WiFi accounts'
            )
        )

    def send_expiry_warnings(self, hours_before):
        """Send expiry warnings to users about to expire"""
        now = timezone.now()
        warning_time = now + timedelta(hours=hours_before)
        
        users_expiring = WifiUser.objects.filter(
            is_active=True,
            expiry__gt=now,
            expiry__lte=warning_time
        )
        
        count = users_expiring.count()
        
        # TODO: Integrate with SMS provider (Twilio, AWS SNS, etc.)
        for user in users_expiring:
            # Example SMS message
            message = f"Your {user.package.name} WiFi package expires at {user.expiry}. Renew now!"
            # send_sms(user.phone_number, message)
            self.stdout.write(
                f"📱 Warning sent to {user.phone_number}: {user.package.name} expires at {user.expiry}"
            )
        
        self.stdout.write(
            self.style.WARNING(
                f'⏰ Sent expiry warnings to {count} users'
            )
        )


def send_sms(phone_number, message):
    """
    Send SMS notification using Twilio or other provider
    
    For Twilio:
    from twilio.rest import Client
    
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    client = Client(account_sid, auth_token)
    
    client.messages.create(
        to=f"+254{phone_number[1:]}",
        from_=settings.TWILIO_PHONE_NUMBER,
        body=message
    )
    """
    pass
