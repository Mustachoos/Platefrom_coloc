# Generated for US-E1 (site-wide Wi-Fi config)

from django.db import migrations, models


def copy_active_event_wifi_to_site_settings(apps, schema_editor):
    """Wi-Fi config is moving from per-Event to a single site-wide
    SiteSettings row. Before the four wifi_* columns are dropped from Event
    (next migration), carry over whatever the currently-active event has
    configured — if any event is active and it has a non-blank SSID. If no
    event is active, or the active one never configured Wi-Fi, SiteSettings
    is left at its just-added defaults."""
    Event = apps.get_model("photos", "Event")
    SiteSettings = apps.get_model("photos", "SiteSettings")

    active_event = Event.objects.filter(is_active=True).first()
    if active_event and active_event.wifi_ssid:
        site_settings, _ = SiteSettings.objects.get_or_create(pk=1)
        site_settings.wifi_ssid = active_event.wifi_ssid
        site_settings.wifi_password = active_event.wifi_password
        site_settings.wifi_security = active_event.wifi_security
        site_settings.wifi_qr_enabled = active_event.wifi_qr_enabled
        site_settings.save(
            update_fields=["wifi_ssid", "wifi_password", "wifi_security", "wifi_qr_enabled"]
        )


class Migration(migrations.Migration):

    dependencies = [
        ('photos', '0025_photo_hidden'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='wifi_password',
            field=models.CharField(blank=True, max_length=200, verbose_name='Wi-Fi password'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='wifi_qr_enabled',
            field=models.BooleanField(default=False, help_text='When on, a second QR code to join the Wi-Fi is shown next to the upload QR code on the TV screen.'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='wifi_security',
            field=models.CharField(choices=[('WPA', 'WPA / WPA2 / WPA3'), ('WEP', 'WEP'), ('NOPASS', 'Open (no password)')], default='WPA', max_length=10),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='wifi_ssid',
            field=models.CharField(blank=True, max_length=100, verbose_name='Wi-Fi network name (SSID)'),
        ),
        migrations.RunPython(copy_active_event_wifi_to_site_settings, migrations.RunPython.noop),
    ]
