# Generated for US-E1 (site-wide Wi-Fi config)
#
# Drops the four wifi_* columns from Event now that 0026 has already copied
# whatever the active event had configured into SiteSettings. Kept as a
# separate migration (not merged into 0026) so the data copy always runs
# against the still-intact Event columns.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('photos', '0026_sitesettings_wifi_config_and_copy'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='wifi_password',
        ),
        migrations.RemoveField(
            model_name='event',
            name='wifi_qr_enabled',
        ),
        migrations.RemoveField(
            model_name='event',
            name='wifi_security',
        ),
        migrations.RemoveField(
            model_name='event',
            name='wifi_ssid',
        ),
    ]
