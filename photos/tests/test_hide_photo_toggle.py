import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from photos.models import Event, Photo
from photos.views import _photo_payload

# A minimal valid 1x1 GIF, good enough to round-trip through an ImageField
# without needing real Pillow-validated content for these tests.
TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04"
    b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)

MEDIA_ROOT = tempfile.mkdtemp(prefix="partybooth-test-media-")


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ToggleHiddenPhotoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.event = Event.objects.create(name="Test Event", is_active=True)
        self.photo = Photo.objects.create(
            event=self.event,
            username="alice",
            image=SimpleUploadedFile("photo.gif", TINY_GIF, content_type="image/gif"),
        )
        # Superuser (not just is_staff): FirstRunRedirectMiddleware funnels
        # every request to /create-admin/ until a superuser exists at all,
        # regardless of who's logged in.
        self.staff_user = get_user_model().objects.create_superuser(
            username="staffer", password="pw12345", email="staffer@example.com"
        )
        self.toggle_url = reverse("dashboard-toggle-photo-hidden", args=[self.photo.id])

    def _mock_channel_layer(self):
        """Patch out the WS broadcast plumbing, recording calls synchronously.

        `async_to_sync` normally wraps a coroutine function; here we make it
        a no-op passthrough so calling the wrapped callable just calls the
        (synchronous) MagicMock directly and records the call args, mirroring
        how the other broadcast call sites in this module could be tested.
        """
        mock_channel_layer = MagicMock()
        patcher_get_layer = patch("photos.views.get_channel_layer", return_value=mock_channel_layer)
        patcher_async_to_sync = patch("photos.views.async_to_sync", side_effect=lambda fn: fn)
        patcher_get_layer.start()
        patcher_async_to_sync.start()
        self.addCleanup(patcher_get_layer.stop)
        self.addCleanup(patcher_async_to_sync.stop)
        return mock_channel_layer

    # -- URL / access control -------------------------------------------------

    def test_toggle_url_resolves(self):
        self.assertEqual(self.toggle_url, f"/dashboard/photos/{self.photo.id}/toggle-hidden/")

    def test_anonymous_is_redirected_to_staff_login_and_photo_untouched(self):
        response = self.client.post(self.toggle_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("staff-login"), response.url)
        self.photo.refresh_from_db()
        self.assertFalse(self.photo.hidden)

    def test_non_staff_user_is_redirected_and_photo_untouched(self):
        get_user_model().objects.create_user(username="guest", password="pw12345", is_staff=False)
        self.client.login(username="guest", password="pw12345")
        response = self.client.post(self.toggle_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("staff-login"), response.url)
        self.photo.refresh_from_db()
        self.assertFalse(self.photo.hidden)

    def test_get_request_does_not_toggle(self):
        self.client.login(username="staffer", password="pw12345")
        mock_channel_layer = self._mock_channel_layer()
        response = self.client.get(self.toggle_url)
        self.assertEqual(response.status_code, 302)
        self.photo.refresh_from_db()
        self.assertFalse(self.photo.hidden)
        mock_channel_layer.group_send.assert_not_called()

    # -- Hiding -----------------------------------------------------------------

    def test_hide_sets_hidden_true_and_redirects_to_photos_tab(self):
        self.client.login(username="staffer", password="pw12345")
        self._mock_channel_layer()
        response = self.client.post(self.toggle_url)
        self.assertRedirects(response, reverse("dashboard") + "?tab=photos")
        self.photo.refresh_from_db()
        self.assertTrue(self.photo.hidden)

    def test_hide_broadcasts_photo_hidden_message(self):
        self.client.login(username="staffer", password="pw12345")
        mock_channel_layer = self._mock_channel_layer()
        self.client.post(self.toggle_url)
        self.photo.refresh_from_db()
        mock_channel_layer.group_send.assert_called_once_with(
            "tv_updates", {"type": "photo.hidden", "url": self.photo.image.url}
        )

    def test_hide_shows_success_message(self):
        self.client.login(username="staffer", password="pw12345")
        self._mock_channel_layer()
        response = self.client.post(self.toggle_url, follow=True)
        messages = [str(m) for m in response.context["messages"]]
        self.assertIn("Photo masquée.", messages)

    # -- Unhiding -----------------------------------------------------------------

    def test_unhide_sets_hidden_false(self):
        self.photo.hidden = True
        self.photo.save(update_fields=["hidden"])
        self.client.login(username="staffer", password="pw12345")
        self._mock_channel_layer()
        self.client.post(self.toggle_url)
        self.photo.refresh_from_db()
        self.assertFalse(self.photo.hidden)

    def test_unhide_broadcasts_reused_photo_uploaded_message(self):
        self.photo.hidden = True
        self.photo.save(update_fields=["hidden"])
        self.client.login(username="staffer", password="pw12345")
        mock_channel_layer = self._mock_channel_layer()
        self.client.post(self.toggle_url)
        self.photo.refresh_from_db()
        mock_channel_layer.group_send.assert_called_once_with(
            "tv_updates", {"type": "photo.uploaded", "photo": _photo_payload(self.photo)}
        )

    def test_unhide_shows_success_message(self):
        self.photo.hidden = True
        self.photo.save(update_fields=["hidden"])
        self.client.login(username="staffer", password="pw12345")
        self._mock_channel_layer()
        response = self.client.post(self.toggle_url, follow=True)
        messages = [str(m) for m in response.context["messages"]]
        self.assertIn("Photo réaffichée.", messages)

    # -- Never deletes -----------------------------------------------------------------

    def test_toggle_never_deletes_row_or_file(self):
        self.client.login(username="staffer", password="pw12345")
        self._mock_channel_layer()
        image_path = self.photo.image.path

        self.client.post(self.toggle_url)  # hide
        self.assertTrue(Photo.objects.filter(pk=self.photo.pk).exists())
        self.assertTrue(os.path.exists(image_path))

        self.client.post(self.toggle_url)  # unhide
        self.assertTrue(Photo.objects.filter(pk=self.photo.pk).exists())
        self.assertTrue(os.path.exists(image_path))

    def test_toggle_is_idempotent_flip_flip(self):
        self.client.login(username="staffer", password="pw12345")
        self._mock_channel_layer()
        self.client.post(self.toggle_url)
        self.photo.refresh_from_db()
        self.assertTrue(self.photo.hidden)
        self.client.post(self.toggle_url)
        self.photo.refresh_from_db()
        self.assertFalse(self.photo.hidden)
