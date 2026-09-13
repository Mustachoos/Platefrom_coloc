"""Tests for US-E3: green "credentials look valid" indicator for Wi-Fi
credentials, based purely on a format/policy check (never a live network
join — that would risk dropping the server's own connection at a live
event, see the story file).

Covers:
- SiteSettings.wifi_credentials_check's validation contract directly.
- admin_management_view computes it synchronously on every render, from
  whatever is currently stored in SiteSettings.
- admin_management.html shows the green badge only when the check passes,
  no badge at all for the neutral "not configured" (blank SSID) state, and
  an inline error message only when a security-specific rule is violated.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from photos.models import SiteSettings


class WifiCredentialsCheckFunctionTests(TestCase):
    """Direct unit tests of the validation function itself."""

    def test_blank_ssid_is_invalid_but_not_an_error(self):
        valid, error = SiteSettings.wifi_credentials_check("", "", SiteSettings.WIFI_SECURITY_WPA)
        self.assertFalse(valid)
        self.assertIsNone(error)

    def test_blank_ssid_is_invalid_but_not_an_error_regardless_of_security(self):
        valid, error = SiteSettings.wifi_credentials_check(
            "", "whatever1", SiteSettings.WIFI_SECURITY_WEP
        )
        self.assertFalse(valid)
        self.assertIsNone(error)

    def test_nopass_with_blank_password_is_valid(self):
        valid, error = SiteSettings.wifi_credentials_check(
            "Chez Axel", "", SiteSettings.WIFI_SECURITY_NOPASS
        )
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_nopass_with_a_password_is_invalid_with_error(self):
        valid, error = SiteSettings.wifi_credentials_check(
            "Chez Axel", "hunter2", SiteSettings.WIFI_SECURITY_NOPASS
        )
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertIn("open networks", error.lower())

    def test_wpa_with_12_char_password_is_valid(self):
        valid, error = SiteSettings.wifi_credentials_check(
            "Chez Axel", "abcdefghijkl", SiteSettings.WIFI_SECURITY_WPA
        )
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_wpa_with_8_char_password_is_valid_lower_bound(self):
        valid, error = SiteSettings.wifi_credentials_check(
            "Chez Axel", "abcdefgh", SiteSettings.WIFI_SECURITY_WPA
        )
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_wpa_with_63_char_password_is_valid_upper_bound(self):
        valid, error = SiteSettings.wifi_credentials_check(
            "Chez Axel", "a" * 63, SiteSettings.WIFI_SECURITY_WPA
        )
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_wpa_with_4_char_password_is_invalid_with_error(self):
        valid, error = SiteSettings.wifi_credentials_check(
            "Chez Axel", "abcd", SiteSettings.WIFI_SECURITY_WPA
        )
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertIn("8-63", error)

    def test_wpa_with_64_char_password_is_invalid_with_error(self):
        valid, error = SiteSettings.wifi_credentials_check(
            "Chez Axel", "a" * 64, SiteSettings.WIFI_SECURITY_WPA
        )
        self.assertFalse(valid)
        self.assertIsNotNone(error)

    def test_wep_with_5_char_password_is_valid(self):
        valid, error = SiteSettings.wifi_credentials_check(
            "Chez Axel", "abcde", SiteSettings.WIFI_SECURITY_WEP
        )
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_wep_with_13_char_password_is_valid(self):
        valid, error = SiteSettings.wifi_credentials_check(
            "Chez Axel", "a" * 13, SiteSettings.WIFI_SECURITY_WEP
        )
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_wep_with_wrong_length_password_is_invalid_with_error(self):
        valid, error = SiteSettings.wifi_credentials_check(
            "Chez Axel", "abcdef", SiteSettings.WIFI_SECURITY_WEP
        )
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertIn("5 or 13", error)


class AdminManagementViewWifiIndicatorTests(TestCase):
    """admin_management_view computes the check synchronously against
    SiteSettings.get_solo() on every render."""

    def setUp(self):
        self.client = Client()
        self.admin_url = reverse("admin-management")
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")

    def test_context_neutral_when_ssid_blank(self):
        response = self.client.get(self.admin_url)
        self.assertFalse(response.context["wifi_credentials_valid"])
        self.assertIsNone(response.context["wifi_credentials_error"])

    def test_context_valid_for_well_formed_wpa_credentials(self):
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_ssid = "Chez Axel"
        site_settings.wifi_password = "a" * 12
        site_settings.wifi_security = SiteSettings.WIFI_SECURITY_WPA
        site_settings.save()

        response = self.client.get(self.admin_url)
        self.assertTrue(response.context["wifi_credentials_valid"])
        self.assertIsNone(response.context["wifi_credentials_error"])

    def test_context_invalid_with_error_for_short_wpa_password(self):
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_ssid = "Chez Axel"
        site_settings.wifi_password = "abcd"
        site_settings.wifi_security = SiteSettings.WIFI_SECURITY_WPA
        site_settings.save()

        response = self.client.get(self.admin_url)
        self.assertFalse(response.context["wifi_credentials_valid"])
        self.assertIsNotNone(response.context["wifi_credentials_error"])

    def test_indicator_updates_immediately_after_save_wifi_config_redirect(self):
        # No background thread/polling involved (unlike the IP check) — a
        # single POST-then-redirect-follow should already reflect it.
        response = self.client.post(
            self.admin_url,
            {
                "verify_wifi_config": "1",
                "wifi_ssid": "Chez Axel",
                "wifi_password": "a" * 12,
                "wifi_security": SiteSettings.WIFI_SECURITY_WPA,
            },
            follow=True,
        )
        self.assertTrue(response.context["wifi_credentials_valid"])


class AdminManagementTemplateWifiIndicatorTests(TestCase):
    """Rendered-HTML acceptance criteria from the story file."""

    def setUp(self):
        self.client = Client()
        self.admin_url = reverse("admin-management")
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")

    def _set_wifi(self, ssid="", password="", security=SiteSettings.WIFI_SECURITY_WPA):
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_ssid = ssid
        site_settings.wifi_password = password
        site_settings.wifi_security = security
        site_settings.save()

    def test_blank_ssid_shows_no_green_dot_and_no_error(self):
        response = self.client.get(self.admin_url)
        content = response.content.decode()
        self.assertNotIn("status-circle verified", content)
        self.assertNotIn("WPA/WPA2/WPA3 passwords must be", content)
        self.assertNotIn("WEP passwords must be", content)
        self.assertNotIn("can't have a password", content)

    def test_wpa_with_12_char_password_alone_does_not_show_green_dot(self):
        # The green dot now means "admin manually confirmed via a QR scan"
        # (see test_wifi_verify_workflow.py) — passing the format check
        # alone is necessary but no longer sufficient to turn it green.
        self._set_wifi(ssid="Chez Axel", password="a" * 12, security=SiteSettings.WIFI_SECURITY_WPA)
        response = self.client.get(self.admin_url)
        content = response.content.decode()
        self.assertNotIn("status-circle verified", content)

    def test_wpa_with_4_char_password_shows_no_green_dot_but_shows_length_error(self):
        self._set_wifi(ssid="Chez Axel", password="abcd", security=SiteSettings.WIFI_SECURITY_WPA)
        response = self.client.get(self.admin_url)
        content = response.content.decode()
        self.assertNotIn("status-circle verified", content)
        self.assertIn("WPA/WPA2/WPA3 passwords must be 8-63 characters.", content)

    def test_nopass_with_password_shows_no_green_dot_but_shows_open_network_error(self):
        self._set_wifi(ssid="Chez Axel", password="hunter2", security=SiteSettings.WIFI_SECURITY_NOPASS)
        response = self.client.get(self.admin_url)
        content = response.content.decode()
        self.assertNotIn("status-circle verified", content)
        self.assertIn("Open networks can&#x27;t have a password", content)

    def test_wep_with_wrong_length_password_shows_no_green_dot_but_shows_wep_error(self):
        # Neither 5 nor 13 characters — the two valid WEP ASCII key lengths.
        self._set_wifi(ssid="Chez Axel", password="wrongsize", security=SiteSettings.WIFI_SECURITY_WEP)
        response = self.client.get(self.admin_url)
        content = response.content.decode()
        self.assertNotIn("status-circle verified", content)
        self.assertIn("WEP passwords must be exactly 5 or 13 characters", content)

    def test_status_dot_tooltip_reads_as_a_manual_scan_not_an_automatic_test(self):
        # Superseded by the QR-verify workflow (test_wifi_verify_workflow.py):
        # the dot's tooltip now describes the manual QR-scan confirmation,
        # not the format check — but the same honesty principle holds, just
        # with updated wording.
        self._set_wifi(ssid="Chez Axel", password="a" * 12, security=SiteSettings.WIFI_SECURITY_WPA)
        response = self.client.get(self.admin_url)
        content = response.content.decode()
        self.assertIn("Confirmé en scannant le QR code pour de vrai", content)
        self.assertNotIn("Wi-Fi confirmed working", content)
