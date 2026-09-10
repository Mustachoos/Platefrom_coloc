# Generated for US-E2 (per-event Wi-Fi QR toggle)
#
# US-E1 centralized the whole Wi-Fi config (credentials + on/off toggle) onto
# SiteSettings. This splits the on/off toggle back out to per-Event, while
# credentials stay on SiteSettings. Same two-migration data-then-schema shape
# US-E1 itself used, just in reverse: this migration adds the column back and
# copies the current site-wide toggle value onto the active event (if any);
# the next migration drops the column from SiteSettings.

from django.db import migrations, models


def copy_site_settings_wifi_qr_enabled_to_active_event(apps, schema_editor):
    Event = apps.get_model("photos", "Event")
    SiteSettings = apps.get_model("photos", "SiteSettings")

    site_settings = SiteSettings.objects.filter(pk=1).first()
    if not site_settings:
        return
    active_event = Event.objects.filter(is_active=True).first()
    if active_event:
        active_event.wifi_qr_enabled = site_settings.wifi_qr_enabled
        active_event.save(update_fields=["wifi_qr_enabled"])


class Migration(migrations.Migration):

    dependencies = [
        ('photos', '0027_remove_event_wifi_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='wifi_qr_enabled',
            field=models.BooleanField(default=False, help_text='When on, a second QR code to join the Wi-Fi is shown next to the upload QR code on the TV screen.'),
        ),
        migrations.RunPython(copy_site_settings_wifi_qr_enabled_to_active_event, migrations.RunPython.noop),
    ]
