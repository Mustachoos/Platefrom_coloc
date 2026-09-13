"""PI-3 US-A1: responsive fixes to /dashboard/ and /admin-account/ for
phone-width screens. This is a CSS/markup-only change — these tests check
the markup contract each fix depends on (the right classes/wrapper elements
exist), not actual rendered layout (Django's test client can't run CSS).
"""
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from photos.models import Event, Photo, UserIdentity

PHOTO_MEDIA_ROOT = tempfile.mkdtemp(prefix="partybooth-test-media-")

# A minimal valid 1x1 GIF, good enough to round-trip through an ImageField.
TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04"
    b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


class DashboardGuestCardsFallbackTests(TestCase):
    def setUp(self):
        self.client = Client()
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")
        self.event = Event.objects.create(name="Test event", is_active=True)
        self.identity = UserIdentity.objects.create(
            event=self.event, pseudo="Alex", session_key="sess-1"
        )

    def test_guests_table_is_wrapped_for_the_mobile_hide_rule(self):
        response = self.client.get(reverse("dashboard") + "?tab=guests")
        content = response.content.decode()
        self.assertIn('class="table-wrap"', content)

    def test_guest_cards_fallback_exists_with_same_guest_data(self):
        response = self.client.get(reverse("dashboard") + "?tab=guests")
        content = response.content.decode()
        self.assertIn('class="guest-cards"', content)
        self.assertIn("guest-card", content)
        # Same guest appears in both the table and the card fallback.
        self.assertEqual(content.count("Alex"), 2)

    def test_guest_card_keeps_the_delete_action(self):
        response = self.client.get(reverse("dashboard") + "?tab=guests")
        content = response.content.decode()
        delete_url = reverse("dashboard-delete-guest", args=[self.identity.id])
        # One delete form in the table, one in the card fallback.
        self.assertEqual(content.count(delete_url), 2)


class DashboardTvLayoutSideColumnClassesTests(TestCase):
    def setUp(self):
        self.client = Client()
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")
        Event.objects.create(name="Test event", is_active=True)

    def test_tv_layout_main_and_side_have_dedicated_classes(self):
        response = self.client.get(reverse("dashboard") + "?tab=tv-layout")
        content = response.content.decode()
        self.assertIn("tv-layout-main", content)
        self.assertIn("tv-layout-side", content)

    def test_tv_layout_side_no_longer_hardcodes_flex_basis_inline(self):
        # The 30%/220px sizing now lives in components.css (.tv-layout-side)
        # so the mobile media query can actually override it — an inline
        # style would win over any non-!important class rule regardless of
        # breakpoint.
        response = self.client.get(reverse("dashboard") + "?tab=tv-layout")
        content = response.content.decode()
        self.assertNotIn("flex:0 0 30%", content)


@override_settings(MEDIA_ROOT=PHOTO_MEDIA_ROOT)
class DashboardPhotoCardActionsClassTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(PHOTO_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")

    def test_photos_tab_renders_without_error(self):
        event = Event.objects.create(name="Test event", is_active=True)
        Photo.objects.create(
            event=event,
            username="alex",
            image=SimpleUploadedFile("photo.gif", TINY_GIF, content_type="image/gif"),
        )
        response = self.client.get(reverse("dashboard") + "?tab=photos")
        self.assertEqual(response.status_code, 200)
        self.assertIn("photo-card__actions", response.content.decode())


class AdminManagementWifiHelpTextResponsiveTests(TestCase):
    def setUp(self):
        self.client = Client()
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")

    def test_wifi_help_text_uses_the_responsive_class_not_inline_position(self):
        response = self.client.get(reverse("admin-management"))
        content = response.content.decode()
        self.assertIn("wifi-qr-help-text", content)
        # The old bug: this element was positioned inline with left:100%,
        # which a media query can't override without !important. It should
        # now carry no inline positioning at all.
        start = content.index('id="wifi-qr-help-text"')
        tag_end = content.index(">", start)
        opening_tag = content[start:tag_end]
        self.assertNotIn("left:100%", opening_tag)
        self.assertNotIn("position:absolute", opening_tag)


class DashboardTabbarOverflowClassTests(TestCase):
    def setUp(self):
        self.client = Client()
        get_user_model().objects.create_superuser(
            username="admin", password="pw12345", email="admin@example.com"
        )
        self.client.login(username="admin", password="pw12345")

    def test_tabbar_present_for_the_mobile_scroll_rule_to_target(self):
        Event.objects.create(name="Test event", is_active=True)
        response = self.client.get(reverse("dashboard"))
        content = response.content.decode()
        self.assertIn('class="tabbar"', content)
