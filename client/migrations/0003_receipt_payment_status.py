from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0002_receipt_device_mac'),
    ]

    operations = [
        migrations.AlterField(
            model_name='receipt',
            name='mpesa_code',
            field=models.CharField(max_length=100),
        ),
        migrations.AddField(
            model_name='receipt',
            name='payment_status',
            field=models.CharField(default='pending', max_length=20),
        ),
    ]
