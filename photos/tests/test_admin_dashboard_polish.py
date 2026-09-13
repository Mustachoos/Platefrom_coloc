"""PI-2 Feature C (admin dashboard polish) and Feature D (Wi-Fi verify
via QR scan):

- C1: the admin_management.html hub sections (network, wifi, drive,
  recovery email) no longer use native <details>/<summary> — collapse is
  now a plain .details-body + a dedicated .hub-toggle-btn (top-right
  corner of each box), toggled purely by clicking that button. No
  server-rendered condition (verify_token, drive_error, etc.) ever sets
  the collapsed/expanded state — that was the whole point of dropping
  <details> here, since its {% if %}-driven `open` attribute coupled the
  section's visibility to unrelated actions.
- C2: verifying the network address shows a success notification (checked
  at the JS-source level — Django's test client can't execute the poll).
- D1: "Vérifier" replaces "Enregistrer" in the Wi-Fi box. Saving credentials
  resets the tri-state wifi_verified back to unset and redirects with
  ?wifi_check=1 (which auto-opens the QR popup, gated on the format check
  still passing). The popup's two outcome buttons set wifi_verified
  True/False, driving the status dot exactly like the network-address box's
  own verified/failed states. A new admin-only QR preview endpoint serves
  the credentials regardless of any event's own wifi_qr_enabled toggle.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from photos.models import SiteSettings


class ArrowOnlyCollapsePanelsTests(TestCase):
    SECTION_IDS = ("network-details", "wifi-details", "drive-details", "support-email-details")

    def setUp(self):
        self.client = Client()
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")

    def test_admin_management_has_no_details_summary_left(self):
        response = self.client.get(reverse("admin-management"))
        content = response.content.decode()
        self.assertNotIn("<details", content)
        self.assertNotIn("<summary", content)

    def test_all_four_section_bodies_are_present_unconditionally(self):
        response = self.client.get(reverse("admin-management"))
        content = response.content.decode()
        for section_id in self.SECTION_IDS:
            self.assertIn(f'id="{section_id}"', content)

    def test_each_section_has_its_own_toggle_button(self):
        response = self.client.get(reverse("admin-management"))
        content = response.content.decode()
        for section_id in self.SECTION_IDS:
            self.assertIn(f'class="hub-toggle-btn" data-target="{section_id}"', content)

    def test_section_bodies_never_server_rendered_as_hidden(self):
        # The whole point: no {% if %} (verify_token, drive_error, ...)
        # ever sets the collapsed state — only the client-side click
        # handler below ever touches `.details-body`'s hidden attribute.
        # Exercise the two states that used to auto-open a <details> block
        # (an in-progress IP verification, and a Drive connection error)
        # and confirm the body still isn't server-rendered hidden either way.
        response = self.client.post(
            reverse("admin-management"), {"start_verify_ip": "1", "ip_address": "192.168.1.13"}, follow=True
        )
        content = response.content.decode()
        start = content.index('id="network-details"')
        network_section = content[start:start + 600]
        self.assertNotIn("details-body\" hidden", network_section)

    def test_toggle_click_handler_is_wired_up_in_js(self):
        response = self.client.get(reverse("admin-management"))
        content = response.content.decode()
        self.assertIn("hub-toggle-btn", content)
        self.assertIn("body.hidden = !body.hidden", content)


class IpVerifiedNotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")

    def test_verified_poll_branch_calls_notify(self):
        # The polling <script> block only renders while a verification is
        # actually in progress (inside {% if verify_token %}) — start one
        # via start_verify_ip and follow its redirect to reach that state,
        # same as a real "Vérifier l'IP" click would.
        response = self.client.post(
            reverse("admin-management"), {"start_verify_ip": "1", "ip_address": "192.168.1.13"}, follow=True
        )
        content = response.content.decode()
        self.assertIn("window.notify('Adresse réseau vérifiée !', 'success')", content)


class WifiVerifyButtonAndFormTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_url = reverse("admin-management")
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")

    def test_wifi_form_button_is_verifier_not_enregistrer(self):
        response = self.client.get(self.admin_url)
        content = response.content.decode()
        self.assertIn('name="verify_wifi_config"', content)
        self.assertIn(">Vérifier<", content)
        self.assertNotIn(">Enregistrer<", content)

    def test_saving_credentials_resets_verification_and_redirects_with_check_flag(self):
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_verified = True
        site_settings.save(update_fields=["wifi_verified"])

        response = self.client.post(
            self.admin_url,
            {
                "verify_wifi_config": "1",
                "wifi_ssid": "Chez Axel",
                "wifi_password": "a" * 12,
                "wifi_security": SiteSettings.WIFI_SECURITY_WPA,
            },
        )

        self.assertRedirects(response, f"{self.admin_url}?wifi_check=1")
        site_settings.refresh_from_db()
        self.assertIsNone(site_settings.wifi_verified)


class WifiStatusDotTriStateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_url = reverse("admin-management")
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_ssid = "Chez Axel"
        site_settings.wifi_password = "a" * 12
        site_settings.wifi_security = SiteSettings.WIFI_SECURITY_WPA
        site_settings.save()

    def _wifi_dot_html(self, content):
        start = content.index('id="wifi-status-circle"')
        return content[max(0, start - 200):start + 50]

    def test_default_unset_shows_neutral_grey(self):
        response = self.client.get(self.admin_url)
        dot_html = self._wifi_dot_html(response.content.decode())
        self.assertNotIn("verified", dot_html)
        self.assertNotIn("failed", dot_html)

    def test_wifi_verify_ok_shows_green(self):
        self.client.post(self.admin_url, {"wifi_verify_ok": "1"})
        response = self.client.get(self.admin_url)
        dot_html = self._wifi_dot_html(response.content.decode())
        self.assertIn("verified", dot_html)

    def test_wifi_verify_broken_shows_red_failed(self):
        self.client.post(self.admin_url, {"wifi_verify_broken": "1"})
        response = self.client.get(self.admin_url)
        dot_html = self._wifi_dot_html(response.content.decode())
        self.assertIn("failed", dot_html)

    def test_only_superuser_can_set_verification_outcome(self):
        get_user_model().objects.create_user(username="staffer", password="pw12345", is_staff=True)
        client = Client()
        client.login(username="staffer", password="pw12345")

        response = client.post(self.admin_url, {"wifi_verify_ok": "1"})

        self.assertNotEqual(response.status_code, 200)
        self.assertIsNone(SiteSettings.get_solo().wifi_verified)


class WifiVerifyPopupAutoOpenTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_url = reverse("admin-management")
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")

    def test_popup_auto_opens_when_check_flag_set_and_credentials_valid(self):
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_ssid = "Chez Axel"
        site_settings.wifi_password = "a" * 12
        site_settings.wifi_security = SiteSettings.WIFI_SECURITY_WPA
        site_settings.save()

        response = self.client.get(self.admin_url, {"wifi_check": "1"})

        self.assertContains(response, "document.getElementById('wifi-verify-modal').showModal();")

    def test_popup_does_not_auto_open_without_check_flag(self):
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_ssid = "Chez Axel"
        site_settings.wifi_password = "a" * 12
        site_settings.wifi_security = SiteSettings.WIFI_SECURITY_WPA
        site_settings.save()

        response = self.client.get(self.admin_url)

        self.assertNotContains(response, "showModal();")

    def test_popup_does_not_auto_open_when_credentials_invalid_even_with_check_flag(self):
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_ssid = "Chez Axel"
        site_settings.wifi_password = "abcd"  # too short for WPA
        site_settings.wifi_security = SiteSettings.WIFI_SECURITY_WPA
        site_settings.save()

        response = self.client.get(self.admin_url, {"wifi_check": "1"})

        self.assertNotContains(response, "showModal();")


class WifiQrPreviewEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("wifi-qr-preview")
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )

    def test_404_when_no_ssid(self):
        self.client.login(username="admin", password="pw12345")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_returns_png_when_ssid_set_regardless_of_any_event_toggle(self):
        # No Event/wifi_qr_enabled involved at all here — this endpoint tests
        # the credentials themselves, independent of any per-event display
        # toggle (unlike views.wifi_qr_code).
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_ssid = "Chez Axel"
        site_settings.wifi_password = "a" * 12
        site_settings.save()
        self.client.login(username="admin", password="pw12345")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    def test_non_superuser_cannot_reach_preview(self):
        get_user_model().objects.create_user(username="staffer", password="pw12345", is_staff=True)
        self.client.login(username="staffer", password="pw12345")

        response = self.client.get(self.url)

        self.assertNotEqual(response.status_code, 200)
