# Generated for US-E2 (per-event Wi-Fi QR toggle)
#
# Drops wifi_qr_enabled from SiteSettings now that 0028 has already copied
# its value onto the active event. Kept as a separate migration (not merged
# into 0028) so the data copy always runs against the still-intact
# SiteSettings column.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('photos', '0028_event_wifi_qr_enabled_and_copy'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sitesettings',
            name='wifi_qr_enabled',
        ),
    ]
