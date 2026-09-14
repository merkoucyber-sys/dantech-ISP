from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wifi', '0002_wifiuser_device_mac'),
    ]

    operations = [
        migrations.CreateModel(
            name='WifiUserDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_mac', models.CharField(max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('wifi_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registered_devices', to='wifi.wifiuser')),
            ],
        ),
        migrations.AddConstraint(
            model_name='wifiuserdevice',
            constraint=models.UniqueConstraint(fields=('wifi_user', 'device_mac'), name='unique_wifi_user_device_mac'),
        ),
    ]
