from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='receipt',
            name='device_mac',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]
