"""US-D2 — Hidden photos excluded from guest-facing views, visible in
"My photos".

Covers the three query sites named in the story contract:
- `gallery_view` (/gallery/) excludes hidden photos.
- `photo_list_api` (/api/photos/) excludes hidden photos.
- `like_toggle_api` rejects liking a hidden photo with a 403.

Plus the "no filtering change, just a label" side of the contract:
- `my_photos_view` (/my-photos/) still lists a guest's own hidden photo,
  with a "Hidden by staff" label shown only for that photo.

And the reversal: unhiding a photo restores it everywhere and makes it
likeable again.

TV's live feed is explicitly out of scope here (US-D1 already covers it via
WS broadcasts) and is not tested in this file.
"""

import json
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from photos.models import Event, Photo, UserIdentity

# A minimal valid 1x1 GIF, good enough to round-trip through an ImageField
# without needing real Pillow-validated content for these tests.
TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04"
    b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)

MEDIA_ROOT = tempfile.mkdtemp(prefix="partybooth-test-media-")


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class HiddenPhotoFilteringTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        # FirstRunRedirectMiddleware funnels every request to /create-admin/
        # until a superuser exists at all, regardless of who's requesting.
        get_user_model().objects.create_superuser(
            username="owner", password="pw12345", email="owner@example.com"
        )
        self.event = Event.objects.create(name="Test Event", is_active=True)
        self.visible_photo = Photo.objects.create(
            event=self.event,
            username="alice",
            image=SimpleUploadedFile("visible.gif", TINY_GIF, content_type="image/gif"),
        )
        self.hidden_photo = Photo.objects.create(
            event=self.event,
            username="bob",
            image=SimpleUploadedFile("hidden.gif", TINY_GIF, content_type="image/gif"),
            hidden=True,
        )

    def _join_as_guest(self, pseudo):
        """Create a real guest identity tied to the test client's session,
        the same way a guest would via the pseudo-picker flow. This fixture
        event has no Drive folder, so US-F1's redirect goes straight to
        upload rather than share-drive — irrelevant to what these tests
        actually check (hidden-photo filtering), just the correct post-F1
        behavior for a no-Drive event."""
        response = self.client.post(reverse("choose-pseudo"), {"pseudo": pseudo})
        self.assertRedirects(response, reverse("upload"))
        return UserIdentity.objects.get(event=self.event, pseudo=pseudo)

    # -- gallery_view -------------------------------------------------------

    def test_gallery_excludes_hidden_photo(self):
        response = self.client.get(reverse("gallery"))

        self.assertEqual(response.status_code, 200)
        photo_ids = {p["id"] for p in response.context["photos"]}
        self.assertIn(self.visible_photo.id, photo_ids)
        self.assertNotIn(self.hidden_photo.id, photo_ids)
        self.assertContains(response, f'data-id="{self.visible_photo.id}"')
        self.assertNotContains(response, f'data-id="{self.hidden_photo.id}"')

    def test_gallery_shows_previously_hidden_photo_once_unhidden(self):
        self.hidden_photo.hidden = False
        self.hidden_photo.save(update_fields=["hidden"])

        response = self.client.get(reverse("gallery"))

        photo_ids = {p["id"] for p in response.context["photos"]}
        self.assertIn(self.hidden_photo.id, photo_ids)

    # -- photo_list_api -------------------------------------------------------

    def test_photo_list_api_excludes_hidden_photo(self):
        response = self.client.get(reverse("photo-list-api"))

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        photo_ids = {p["id"] for p in payload}
        self.assertIn(self.visible_photo.id, photo_ids)
        self.assertNotIn(self.hidden_photo.id, photo_ids)

    def test_photo_list_api_includes_previously_hidden_photo_once_unhidden(self):
        self.hidden_photo.hidden = False
        self.hidden_photo.save(update_fields=["hidden"])

        response = self.client.get(reverse("photo-list-api"))

        payload = json.loads(response.content)
        photo_ids = {p["id"] for p in payload}
        self.assertIn(self.hidden_photo.id, photo_ids)

    # -- like_toggle_api -------------------------------------------------------

    def test_liking_hidden_photo_is_rejected_with_403(self):
        self._join_as_guest("carol")
        like_url = reverse("photo-like-api", args=[self.hidden_photo.id])

        response = self.client.post(like_url)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.hidden_photo.likes.exists())

    def test_liking_visible_photo_still_succeeds(self):
        self._join_as_guest("carol")
        like_url = reverse("photo-like-api", args=[self.visible_photo.id])

        response = self.client.post(like_url)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload["liked"])

    def test_liking_previously_hidden_photo_succeeds_once_unhidden(self):
        self.hidden_photo.hidden = False
        self.hidden_photo.save(update_fields=["hidden"])
        self._join_as_guest("carol")
        like_url = reverse("photo-like-api", args=[self.hidden_photo.id])

        response = self.client.post(like_url)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload["liked"])

    # -- my_photos_view -------------------------------------------------------

    def test_my_photos_still_lists_own_hidden_photo_labeled(self):
        self._join_as_guest("bob")

        response = self.client.get(reverse("my-photos"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-id="{self.hidden_photo.id}"')
        self.assertContains(response, "Hidden by staff")

    def test_my_photos_does_not_label_a_visible_photo(self):
        self._join_as_guest("alice")

        response = self.client.get(reverse("my-photos"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-id="{self.visible_photo.id}"')
        self.assertNotContains(response, "Hidden by staff")
