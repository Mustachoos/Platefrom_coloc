"""Tests for US-E2: the "show Wi-Fi QR on TV" toggle moves back to per-event.

Post-E1, `wifi_qr_enabled` lived on `SiteSettings` alongside the Wi-Fi
credentials. This story splits it back out: credentials (`wifi_ssid` /
`wifi_password` / `wifi_security`) stay site-wide on `SiteSettings`, but
whether to actually show the QR code on the TV is per-Event again, and
staff (not just admins) can flip it from the dashboard.

Covers the acceptance criteria:
- No SSID configured -> the dashboard toggle is disabled with explanatory
  text, and posting the toggle directly is rejected.
- SSID configured -> staff can toggle `active_event.wifi_qr_enabled` on/off
  from the dashboard; switching the active event preserves each event's own
  choice.
- Switching the active event changes what the TV shows, without touching
  the underlying site-wide credentials.
- `SiteSettings` no longer has a `wifi_qr_enabled` field; `admin_management`
  no longer has an enable/disable toggle for it.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from photos.models import Event, SiteSettings


class PerEventWifiQrToggleTests(TestCase):
    def setUp(self):
        self.client = Client()
        # FirstRunRedirectMiddleware funnels every request to /create-admin/
        # until a superuser exists at all, regardless of who's logged in.
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.staff_user = get_user_model().objects.create_user(
            username="staffer", password="pw12345", is_staff=True, is_superuser=False
        )
        self.event_a = Event.objects.create(name="Event A", is_active=True)
        self.event_b = Event.objects.create(name="Event B", is_active=False)
        self.dashboard_url = reverse("dashboard")
        self.site_settings = SiteSettings.get_solo()

    def _login_staff(self):
        self.client.login(username="staffer", password="pw12345")

    def _configure_credentials(self):
        self.site_settings.wifi_ssid = "Chez Axel"
        self.site_settings.wifi_password = "hunter2"
        self.site_settings.save(update_fields=["wifi_ssid", "wifi_password"])

    # --- Model contract ----------------------------------------------------

    def test_event_has_wifi_qr_enabled_default_false(self):
        self.assertFalse(self.event_a.wifi_qr_enabled)
        self.assertFalse(self.event_b.wifi_qr_enabled)

    def test_site_settings_no_longer_has_wifi_qr_enabled_field(self):
        field_names = {f.name for f in SiteSettings._meta.get_fields()}
        self.assertNotIn("wifi_qr_enabled", field_names)

    # --- No SSID configured: disabled + rejected ----------------------------

    def test_dashboard_toggle_disabled_and_explained_when_no_ssid(self):
        self._login_staff()
        response = self.client.get(self.dashboard_url + "?tab=tv-layout")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Requires admin to set up Wi-Fi credentials", content)
        self.assertRegex(content, r'name="toggle_wifi_qr"[^>]*disabled')

    def test_posting_toggle_directly_rejected_when_no_ssid(self):
        self._login_staff()
        response = self.client.post(self.dashboard_url, {"toggle_wifi_qr": "1"}, follow=True)
        self.event_a.refresh_from_db()
        self.assertFalse(self.event_a.wifi_qr_enabled)
        messages = [str(m) for m in response.context["messages"]]
        self.assertIn("Ask an admin to set up Wi-Fi credentials first.", messages)

    # --- SSID configured: staff can toggle per event ------------------------

    def test_dashboard_toggle_enabled_when_ssid_present(self):
        self._configure_credentials()
        self._login_staff()
        response = self.client.get(self.dashboard_url + "?tab=tv-layout")
        content = response.content.decode()
        self.assertNotIn("Requires admin to set up Wi-Fi credentials", content)
        self.assertNotRegex(content, r'name="toggle_wifi_qr"[^>]*disabled')

    def test_staff_can_toggle_wifi_qr_on_and_off(self):
        self._configure_credentials()
        self._login_staff()

        response = self.client.post(self.dashboard_url, {"toggle_wifi_qr": "1"}, follow=True)
        self.event_a.refresh_from_db()
        self.assertTrue(self.event_a.wifi_qr_enabled)
        messages = [str(m) for m in response.context["messages"]]
        self.assertIn("Wi-Fi QR code enabled.", messages)

        response = self.client.post(self.dashboard_url, {"toggle_wifi_qr": "1"}, follow=True)
        self.event_a.refresh_from_db()
        self.assertFalse(self.event_a.wifi_qr_enabled)
        messages = [str(m) for m in response.context["messages"]]
        self.assertIn("Wi-Fi QR code disabled.", messages)

    def test_switching_active_event_preserves_each_events_own_choice(self):
        self._configure_credentials()
        self._login_staff()

        # Enable it on event_a only.
        self.client.post(self.dashboard_url, {"toggle_wifi_qr": "1"})
        self.event_a.refresh_from_db()
        self.assertTrue(self.event_a.wifi_qr_enabled)

        # Switch the active event to event_b — its own choice defaults off,
        # untouched by event_a's.
        self.event_a.is_active = False
        self.event_a.save(update_fields=["is_active"])
        self.event_b.is_active = True
        self.event_b.save(update_fields=["is_active"])
        self.event_b.refresh_from_db()
        self.assertFalse(self.event_b.wifi_qr_enabled)

        # Switch back — event_a's own choice was preserved the whole time.
        self.event_b.is_active = False
        self.event_b.save(update_fields=["is_active"])
        self.event_a.is_active = True
        self.event_a.save(update_fields=["is_active"])
        self.event_a.refresh_from_db()
        self.assertTrue(self.event_a.wifi_qr_enabled)

    # --- TV reflects the active event's own flag, credentials untouched ----

    def test_tv_reflects_active_events_flag_without_touching_credentials(self):
        self._configure_credentials()
        self.event_a.wifi_qr_enabled = True
        self.event_a.save(update_fields=["wifi_qr_enabled"])
        # event_b left at its default (False).

        response = self.client.get(reverse("tv"))
        self.assertTrue(response.context["wifi_qr_shown"])

        self.event_a.is_active = False
        self.event_a.save(update_fields=["is_active"])
        self.event_b.is_active = True
        self.event_b.save(update_fields=["is_active"])

        response = self.client.get(reverse("tv"))
        self.assertFalse(response.context["wifi_qr_shown"])

        self.site_settings.refresh_from_db()
        self.assertEqual(self.site_settings.wifi_ssid, "Chez Axel")
        self.assertEqual(self.site_settings.wifi_password, "hunter2")

    def test_slideshow_settings_api_reflects_active_events_flag(self):
        self._configure_credentials()
        self.event_a.wifi_qr_enabled = True
        self.event_a.save(update_fields=["wifi_qr_enabled"])

        response = self.client.get(reverse("slideshow-settings-api"))
        self.assertTrue(response.json()["wifi_qr_shown"])

        self.event_a.is_active = False
        self.event_a.save(update_fields=["is_active"])
        self.event_b.is_active = True
        self.event_b.save(update_fields=["is_active"])

        response = self.client.get(reverse("slideshow-settings-api"))
        self.assertFalse(response.json()["wifi_qr_shown"])

    def test_wifi_qr_code_image_gated_on_active_events_flag(self):
        self._configure_credentials()
        response = self.client.get(reverse("wifi-qr-code"))
        self.assertEqual(response.status_code, 404)

        self.event_a.wifi_qr_enabled = True
        self.event_a.save(update_fields=["wifi_qr_enabled"])
        response = self.client.get(reverse("wifi-qr-code"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    # --- admin_management.html no longer has the toggle ----------------------

    def test_admin_management_has_no_wifi_qr_toggle_but_keeps_credentials_form(self):
        self.client.login(username="admin", password="pw12345")
        response = self.client.get(reverse("admin-management"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('name="toggle_wifi_qr"', content)
        self.assertIn('name="wifi_ssid"', content)
        self.assertIn('name="save_wifi_config"', content)

    def test_posting_toggle_wifi_qr_to_admin_management_does_nothing(self):
        """The handler moved to the dashboard — admin_management_view no
        longer recognizes this POST key at all."""
        self._configure_credentials()
        self.client.login(username="admin", password="pw12345")
        self.client.post(reverse("admin-management"), {"toggle_wifi_qr": "1"})
        self.event_a.refresh_from_db()
        self.assertFalse(self.event_a.wifi_qr_enabled)
