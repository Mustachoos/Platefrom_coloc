"""Tests for US-E1: Wi-Fi config becomes a site-wide, admin-only setting.

Covers:
- SiteSettings carries the four wifi_* fields (and Event no longer does).
- The data migration (0026) copies an active event's wifi config into
  SiteSettings before the schema migration (0027) drops it from Event.
- The three read sites (tv_view, slideshow_settings_api, wifi_qr_code) read
  from SiteSettings, independent of which event is active.
- The write handlers (save_wifi_config, toggle_wifi_qr) only live on
  admin_management_view now, and are admin-only.
- The dashboard's TV-layout tab no longer has any Wi-Fi editing UI; the
  admin management hub does.
"""
import importlib

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from photos.models import Event, SiteSettings

WIFI_MIGRATION_MODULE = "photos.migrations.0026_sitesettings_wifi_config_and_copy"


class SiteSettingsWifiFieldsTests(TestCase):
    """Model contract: the fields moved, with the same shape."""

    def test_site_settings_has_wifi_fields_with_expected_defaults(self):
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "")
        self.assertEqual(site_settings.wifi_password, "")
        self.assertEqual(site_settings.wifi_security, SiteSettings.WIFI_SECURITY_WPA)
        self.assertFalse(site_settings.wifi_qr_enabled)

    def test_site_settings_wifi_security_choices_shape_unchanged(self):
        self.assertEqual(
            SiteSettings.WIFI_SECURITY_CHOICES,
            [
                (SiteSettings.WIFI_SECURITY_WPA, "WPA / WPA2 / WPA3"),
                (SiteSettings.WIFI_SECURITY_WEP, "WEP"),
                (SiteSettings.WIFI_SECURITY_NOPASS, "Open (no password)"),
            ],
        )

    def test_event_no_longer_has_wifi_fields(self):
        event_field_names = {f.name for f in Event._meta.get_fields()}
        for field_name in ("wifi_ssid", "wifi_password", "wifi_security", "wifi_qr_enabled"):
            self.assertNotIn(field_name, event_field_names)

    def test_event_no_longer_has_wifi_security_constants(self):
        self.assertFalse(hasattr(Event, "WIFI_SECURITY_CHOICES"))
        self.assertFalse(hasattr(Event, "WIFI_SECURITY_WPA"))


class WifiConfigDataMigrationTests(TestCase):
    """Exercises the actual RunPython function from migration 0026 against
    test-created stand-ins for the pre-migration Event columns (Event no
    longer carries wifi_* fields on the current schema, so a real Event
    can't hold them — a lightweight stand-in exposing exactly what the
    migration reads is what lets this run against "the still-intact Event
    columns" the migration was written to read from)."""

    def setUp(self):
        module = importlib.import_module(WIFI_MIGRATION_MODULE)
        self.copy_fn = module.copy_active_event_wifi_to_site_settings

    class _StubEvent:
        def __init__(self, is_active, wifi_ssid="", wifi_password="", wifi_security="WPA", wifi_qr_enabled=False):
            self.is_active = is_active
            self.wifi_ssid = wifi_ssid
            self.wifi_password = wifi_password
            self.wifi_security = wifi_security
            self.wifi_qr_enabled = wifi_qr_enabled

    class _StubQuerySet:
        def __init__(self, items):
            self._items = items

        def first(self):
            return self._items[0] if self._items else None

    class _StubEventManager:
        def __init__(self, events):
            self._events = events

        def filter(self, **kwargs):
            matched = [e for e in self._events if all(getattr(e, k) == v for k, v in kwargs.items())]
            return WifiConfigDataMigrationTests._StubQuerySet(matched)

    class _StubEventModel:
        def __init__(self, events):
            self.objects = WifiConfigDataMigrationTests._StubEventManager(events)

    def _fake_apps(self, events):
        stub_event_model = self._StubEventModel(events)

        class _FakeApps:
            @staticmethod
            def get_model(app_label, model_name):
                assert app_label == "photos"
                if model_name == "Event":
                    return stub_event_model
                if model_name == "SiteSettings":
                    return SiteSettings
                raise LookupError(model_name)

        return _FakeApps()

    def test_copies_active_events_wifi_config_into_site_settings(self):
        active_event = self._StubEvent(
            is_active=True,
            wifi_ssid="Chez Axel",
            wifi_password="hunter2",
            wifi_security=SiteSettings.WIFI_SECURITY_WEP,
            wifi_qr_enabled=True,
        )
        self.copy_fn(self._fake_apps([active_event]), None)

        site_settings = SiteSettings.objects.get(pk=1)
        self.assertEqual(site_settings.wifi_ssid, "Chez Axel")
        self.assertEqual(site_settings.wifi_password, "hunter2")
        self.assertEqual(site_settings.wifi_security, SiteSettings.WIFI_SECURITY_WEP)
        self.assertTrue(site_settings.wifi_qr_enabled)

    def test_no_active_event_leaves_site_settings_at_defaults(self):
        inactive_event = self._StubEvent(is_active=False, wifi_ssid="Should not be copied")
        self.copy_fn(self._fake_apps([inactive_event]), None)

        # The migration never touches SiteSettings at all in this case, so
        # there may not even be a row yet — get_solo() is the same "give me
        # the defaults if nothing was ever written" read the app uses everywhere.
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "")
        self.assertFalse(site_settings.wifi_qr_enabled)

    def test_active_event_with_blank_ssid_leaves_site_settings_at_defaults(self):
        active_event_no_wifi = self._StubEvent(is_active=True, wifi_ssid="")
        self.copy_fn(self._fake_apps([active_event_no_wifi]), None)

        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "")
        self.assertEqual(site_settings.wifi_security, SiteSettings.WIFI_SECURITY_WPA)

    def test_no_events_at_all_leaves_site_settings_at_defaults(self):
        self.copy_fn(self._fake_apps([]), None)
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "")


class WifiReadSitesTests(TestCase):
    """tv_view, slideshow_settings_api, wifi_qr_code all read from
    SiteSettings now — not tied to which event is active."""

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

    def _enable_wifi_qr(self):
        self.site_settings.wifi_ssid = "Chez Axel"
        self.site_settings.wifi_qr_enabled = True
        self.site_settings.wifi_security = SiteSettings.WIFI_SECURITY_WPA
        self.site_settings.wifi_password = "hunter2"
        self.site_settings.save()

    def test_tv_view_wifi_qr_shown_reflects_site_settings(self):
        response = self.client.get(reverse("tv"))
        self.assertFalse(response.context["wifi_qr_shown"])

        self._enable_wifi_qr()
        response = self.client.get(reverse("tv"))
        self.assertTrue(response.context["wifi_qr_shown"])

    def test_tv_view_wifi_qr_shown_survives_switching_active_event(self):
        self._enable_wifi_qr()
        self.event_a.is_active = False
        self.event_a.save(update_fields=["is_active"])
        self.event_b.is_active = True
        self.event_b.save(update_fields=["is_active"])

        response = self.client.get(reverse("tv"))
        self.assertTrue(response.context["wifi_qr_shown"])

    def test_slideshow_settings_api_wifi_qr_shown_reflects_site_settings(self):
        response = self.client.get(reverse("slideshow-settings-api"))
        self.assertFalse(response.json()["wifi_qr_shown"])

        self._enable_wifi_qr()
        response = self.client.get(reverse("slideshow-settings-api"))
        self.assertTrue(response.json()["wifi_qr_shown"])

    def test_wifi_qr_code_404_when_disabled(self):
        response = self.client.get(reverse("wifi-qr-code"))
        self.assertEqual(response.status_code, 404)

    def test_wifi_qr_code_returns_png_when_enabled(self):
        self._enable_wifi_qr()
        response = self.client.get(reverse("wifi-qr-code"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    def test_wifi_qr_code_reflects_site_settings_regardless_of_active_event(self):
        self._enable_wifi_qr()
        self.event_a.is_active = False
        self.event_a.save(update_fields=["is_active"])
        # No event active at all now.
        response = self.client.get(reverse("wifi-qr-code"))
        self.assertEqual(response.status_code, 200)

    def test_wifi_qr_code_404_when_no_ssid_even_if_flag_on(self):
        self.site_settings.wifi_qr_enabled = True
        self.site_settings.wifi_ssid = ""
        self.site_settings.save()
        response = self.client.get(reverse("wifi-qr-code"))
        self.assertEqual(response.status_code, 404)


class WifiWriteHandlersAdminOnlyTests(TestCase):
    """save_wifi_config / toggle_wifi_qr now live on admin_management_view,
    which is @superuser_required — so only a superuser can reach them."""

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
                "save_wifi_config": "1",
                "wifi_ssid": "Chez Axel",
                "wifi_password": "hunter2",
                "wifi_security": SiteSettings.WIFI_SECURITY_WEP,
            },
        )
        self.assertRedirects(response, self.admin_url)
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "Chez Axel")
        self.assertEqual(site_settings.wifi_password, "hunter2")
        self.assertEqual(site_settings.wifi_security, SiteSettings.WIFI_SECURITY_WEP)

    def test_save_wifi_config_falls_back_to_wpa_for_invalid_security(self):
        self.client.login(username="admin", password="pw12345")
        self.client.post(
            self.admin_url,
            {"save_wifi_config": "1", "wifi_ssid": "Chez Axel", "wifi_security": "not-a-real-choice"},
        )
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_security, SiteSettings.WIFI_SECURITY_WPA)

    def test_saving_blank_ssid_turns_off_an_enabled_qr_code(self):
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_ssid = "Chez Axel"
        site_settings.wifi_qr_enabled = True
        site_settings.save()

        self.client.login(username="admin", password="pw12345")
        self.client.post(self.admin_url, {"save_wifi_config": "1", "wifi_ssid": "", "wifi_security": "WPA"})

        site_settings.refresh_from_db()
        self.assertEqual(site_settings.wifi_ssid, "")
        self.assertFalse(site_settings.wifi_qr_enabled)

    def test_superuser_can_toggle_wifi_qr_on(self):
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_ssid = "Chez Axel"
        site_settings.save()

        self.client.login(username="admin", password="pw12345")
        response = self.client.post(self.admin_url, {"toggle_wifi_qr": "1"}, follow=True)
        site_settings.refresh_from_db()
        self.assertTrue(site_settings.wifi_qr_enabled)
        messages = [str(m) for m in response.context["messages"]]
        self.assertIn("Wi-Fi QR code enabled.", messages)

    def test_toggle_wifi_qr_rejected_without_ssid(self):
        self.client.login(username="admin", password="pw12345")
        response = self.client.post(self.admin_url, {"toggle_wifi_qr": "1"}, follow=True)
        site_settings = SiteSettings.get_solo()
        self.assertFalse(site_settings.wifi_qr_enabled)
        messages = [str(m) for m in response.context["messages"]]
        self.assertIn("Enter a Wi-Fi network name first.", messages)

    def test_non_superuser_staff_cannot_save_wifi_config(self):
        self.client.login(username="staffer", password="pw12345")
        response = self.client.post(
            self.admin_url, {"save_wifi_config": "1", "wifi_ssid": "Should not save"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard"), response.url)
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "")

    def test_non_superuser_staff_cannot_toggle_wifi_qr(self):
        site_settings = SiteSettings.get_solo()
        site_settings.wifi_ssid = "Chez Axel"
        site_settings.save()

        self.client.login(username="staffer", password="pw12345")
        response = self.client.post(self.admin_url, {"toggle_wifi_qr": "1"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard"), response.url)
        site_settings.refresh_from_db()
        self.assertFalse(site_settings.wifi_qr_enabled)

    def test_anonymous_cannot_save_wifi_config(self):
        response = self.client.post(
            self.admin_url, {"save_wifi_config": "1", "wifi_ssid": "Should not save"},
        )
        self.assertEqual(response.status_code, 302)
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "")

    def test_posting_old_wifi_fields_to_dashboard_no_longer_does_anything(self):
        """The dashboard used to handle save_wifi_config/toggle_wifi_qr
        itself; those handlers moved to admin_management_view, so posting
        them to the dashboard now just falls through, untouched."""
        self.client.login(username="staffer", password="pw12345")
        response = self.client.post(
            reverse("dashboard"),
            {"save_wifi_config": "1", "wifi_ssid": "Should not save here either"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("tab=features", response.url)
        site_settings = SiteSettings.get_solo()
        self.assertEqual(site_settings.wifi_ssid, "")


class WifiTemplatePlacementTests(TestCase):
    """The Wi-Fi block moved out of the dashboard's TV-layout tab and into
    the admin management hub, next to #network-details."""

    def setUp(self):
        self.client = Client()
        self.event = Event.objects.create(name="Test Event", is_active=True)
        self.superuser = get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )

    def test_dashboard_tv_layout_tab_has_no_wifi_editing_ui(self):
        self.client.login(username="admin", password="pw12345")
        response = self.client.get(reverse("dashboard") + "?tab=tv-layout")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('name="save_wifi_config"', content)
        self.assertNotIn('name="toggle_wifi_qr"', content)
        self.assertNotIn('name="wifi_ssid"', content)

    def test_admin_management_has_wifi_editing_ui_near_network_details(self):
        self.client.login(username="admin", password="pw12345")
        response = self.client.get(reverse("admin-management"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('name="save_wifi_config"', content)
        self.assertIn('name="toggle_wifi_qr"', content)
        self.assertIn('name="wifi_ssid"', content)
        # Both are physical-network config blocks: assert they're near each
        # other rather than just present anywhere on the page.
        network_details_pos = content.index('id="network-details"')
        wifi_details_pos = content.index('id="wifi-details"')
        between = content[network_details_pos:wifi_details_pos]
        self.assertLess(len(between), 6000, "wifi block should sit right next to #network-details")
