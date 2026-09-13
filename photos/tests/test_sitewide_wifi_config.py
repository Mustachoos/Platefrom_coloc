"""Tests for US-E1: Wi-Fi config becomes a site-wide, admin-only setting.

Covers:
- SiteSettings carries the three wifi_* credential fields (and Event no
  longer does).
- The data migration (0026) copies an active event's wifi config into
  SiteSettings before the schema migration (0027) drops it from Event.
- The credential read sites (tv_view, slideshow_settings_api, wifi_qr_code)
  read credentials from SiteSettings, independent of which event is active.
- The write handler (verify_wifi_config) only lives on admin_management_view,
  and is admin-only.

Note (US-E2): the on/off "show the QR on TV" toggle was split back out to
per-Event (`wifi_qr_enabled` lives on `Event` again, not `SiteSettings`).
Tests here that used to exercise that toggle as a site-wide, admin-only
setting have been updated or removed accordingly — see
`test_per_event_wifi_toggle.py` for the current toggle contract.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from photos.models import Event, SiteSettings


class SiteSettingsWifiFieldsTests(TestCase):
    """Model contract: the credential fields moved, with the same shape."""

    def test_site_settings_has_wifi_credential_fields_with_expected_defaults(self):
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "")
        self.assertEqual(site_settings.wifi_password, "")
        self.assertEqual(site_settings.wifi_security, SiteSettings.WIFI_SECURITY_WPA)

    def test_site_settings_wifi_security_choices_shape_unchanged(self):
        self.assertEqual(
            SiteSettings.WIFI_SECURITY_CHOICES,
            [
                (SiteSettings.WIFI_SECURITY_WPA, "WPA / WPA2 / WPA3"),
                (SiteSettings.WIFI_SECURITY_WEP, "WEP"),
                (SiteSettings.WIFI_SECURITY_NOPASS, "Ouvert (sans mot de passe)"),
            ],
        )

    def test_event_no_longer_has_wifi_credential_fields(self):
        event_field_names = {f.name for f in Event._meta.get_fields()}
        for field_name in ("wifi_ssid", "wifi_password", "wifi_security"):
            self.assertNotIn(field_name, event_field_names)

    def test_event_no_longer_has_wifi_security_constants(self):
        self.assertFalse(hasattr(Event, "WIFI_SECURITY_CHOICES"))
        self.assertFalse(hasattr(Event, "WIFI_SECURITY_WPA"))


class WifiReadSitesTests(TestCase):
    """tv_view, slideshow_settings_api, wifi_qr_code read credentials from
    SiteSettings (independent of which event is active), but whether the QR
    is actually shown also depends on the active event's own
    `wifi_qr_enabled` flag (US-E2)."""

    def setUp(self):
        self.client = Client()
        # FirstRunRedirectMiddleware funnels every request to /create-admin/
        # until a superuser exists at all, regardless of who's browsing —
        # these are public pages (TV screen, slideshow API, Wi-Fi QR image).
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.event_a = Event.objects.create(name="Event A", is_active=True)
        self.event_b = Event.objects.create(name="Event B", is_active=False)
        self.site_settings = SiteSettings.get_solo()

    def _configure_credentials(self):
        self.site_settings.wifi_ssid = "Chez Axel"
        self.site_settings.wifi_security = SiteSettings.WIFI_SECURITY_WPA
        self.site_settings.wifi_password = "hunter2"
        self.site_settings.save()

    def _enable_wifi_qr(self, event):
        self._configure_credentials()
        event.wifi_qr_enabled = True
        event.save(update_fields=["wifi_qr_enabled"])

    def test_tv_view_wifi_qr_shown_reflects_credentials_and_active_event_flag(self):
        response = self.client.get(reverse("tv"))
        self.assertFalse(response.context["wifi_qr_shown"])

        self._enable_wifi_qr(self.event_a)
        response = self.client.get(reverse("tv"))
        self.assertTrue(response.context["wifi_qr_shown"])

    def test_slideshow_settings_api_wifi_qr_shown_reflects_credentials_and_active_event_flag(self):
        response = self.client.get(reverse("slideshow-settings-api"))
        self.assertFalse(response.json()["wifi_qr_shown"])

        self._enable_wifi_qr(self.event_a)
        response = self.client.get(reverse("slideshow-settings-api"))
        self.assertTrue(response.json()["wifi_qr_shown"])

    def test_wifi_qr_code_404_when_disabled(self):
        response = self.client.get(reverse("wifi-qr-code"))
        self.assertEqual(response.status_code, 404)

    def test_wifi_qr_code_returns_png_when_enabled(self):
        self._enable_wifi_qr(self.event_a)
        response = self.client.get(reverse("wifi-qr-code"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    def test_wifi_qr_code_404_when_no_active_event(self):
        self._enable_wifi_qr(self.event_a)
        self.event_a.is_active = False
        self.event_a.save(update_fields=["is_active"])
        # No event active at all now — nothing to read the per-event flag from.
        response = self.client.get(reverse("wifi-qr-code"))
        self.assertEqual(response.status_code, 404)

    def test_wifi_qr_code_404_when_no_ssid_even_if_event_flag_on(self):
        self.event_a.wifi_qr_enabled = True
        self.event_a.save(update_fields=["wifi_qr_enabled"])
        self.site_settings.wifi_ssid = ""
        self.site_settings.save()
        response = self.client.get(reverse("wifi-qr-code"))
        self.assertEqual(response.status_code, 404)


class WifiCredentialWriteHandlerAdminOnlyTests(TestCase):
    """verify_wifi_config lives on admin_management_view, which is
    @superuser_required — so only a superuser can reach it. (The on/off QR
    toggle moved to the dashboard in US-E2 — see test_per_event_wifi_toggle.py.)"""

    def setUp(self):
        self.client = Client()
        self.event = Event.objects.create(name="Test Event", is_active=True)
        self.admin_url = reverse("admin-management")
        self.superuser = get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.staff_user = get_user_model().objects.create_user(
            username="staffer", password="pw12345", is_staff=True, is_superuser=False
        )

    def test_superuser_can_save_wifi_config(self):
        self.client.login(username="admin", password="pw12345")
        response = self.client.post(
            self.admin_url,
            {
                "verify_wifi_config": "1",
                "wifi_ssid": "Chez Axel",
                "wifi_password": "hunter2",
                "wifi_security": SiteSettings.WIFI_SECURITY_WEP,
            },
        )
        # ?wifi_check=1 triggers the verify-QR popup auto-opening on this
        # render — see test_wifi_verify_workflow.py.
        self.assertRedirects(response, f"{self.admin_url}?wifi_check=1")
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "Chez Axel")
        self.assertEqual(site_settings.wifi_password, "hunter2")
        self.assertEqual(site_settings.wifi_security, SiteSettings.WIFI_SECURITY_WEP)

    def test_save_wifi_config_falls_back_to_wpa_for_invalid_security(self):
        self.client.login(username="admin", password="pw12345")
        self.client.post(
            self.admin_url,
            {"verify_wifi_config": "1", "wifi_ssid": "Chez Axel", "wifi_security": "not-a-real-choice"},
        )
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_security, SiteSettings.WIFI_SECURITY_WPA)

    def test_non_superuser_staff_cannot_save_wifi_config(self):
        self.client.login(username="staffer", password="pw12345")
        response = self.client.post(
            self.admin_url, {"verify_wifi_config": "1", "wifi_ssid": "Should not save"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard"), response.url)
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "")

    def test_anonymous_cannot_save_wifi_config(self):
        response = self.client.post(
            self.admin_url, {"verify_wifi_config": "1", "wifi_ssid": "Should not save"},
        )
        self.assertEqual(response.status_code, 302)
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "")


class WifiTemplatePlacementTests(TestCase):
    """The credential-entry form lives in the admin management hub, next to
    #network-details. The on/off QR toggle lives on the dashboard's
    TV-layout tab (US-E2) — not in admin management."""

    def setUp(self):
        self.client = Client()
        self.event = Event.objects.create(name="Test Event", is_active=True)
        self.superuser = get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )

    def test_dashboard_tv_layout_tab_has_wifi_toggle_but_not_credentials_form(self):
        self.client.login(username="admin", password="pw12345")
        response = self.client.get(reverse("dashboard") + "?tab=tv-layout")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('name="toggle_wifi_qr"', content)
        self.assertNotIn('name="verify_wifi_config"', content)
        self.assertNotIn('name="wifi_ssid"', content)

    def test_admin_management_has_credentials_form_but_not_the_toggle(self):
        self.client.login(username="admin", password="pw12345")
        response = self.client.get(reverse("admin-management"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('name="verify_wifi_config"', content)
        self.assertIn('name="wifi_ssid"', content)
        self.assertNotIn('name="toggle_wifi_qr"', content)
        network_details_pos = content.index('id="network-details"')
        wifi_details_pos = content.index('id="wifi-details"')
        between = content[network_details_pos:wifi_details_pos]
        self.assertLess(len(between), 6000, "wifi block should sit right next to #network-details")
