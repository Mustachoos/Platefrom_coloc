import io
import shutil
import tempfile
import zipfile

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from photos.models import Event, Photo

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="photos-export-test-")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class EventExportViewTests(TestCase):
    """Covers US-C1 — download an event's photos as a ZIP."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # The app funnels every request to /create-admin/ until a superuser
        # exists (FirstRunRedirectMiddleware) — create one so login/redirect
        # behavior under test reflects a claimed install, not first-run setup.
        User.objects.create_superuser(
            username="root", password="pw12345", email="root@example.com"
        )
        self.staff_user = User.objects.create_user(
            username="staffer", password="pw12345", is_staff=True
        )
        self.event = Event.objects.create(name="Summer Party", is_active=True)

    def _make_photo(self, filename="pic.jpg", content=b"fake-image-bytes"):
        return Photo.objects.create(
            event=self.event,
            username="alice",
            image=self._uploaded_file(filename, content),
        )

    @staticmethod
    def _uploaded_file(filename, content):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile(filename, content, content_type="image/jpeg")

    def test_download_zip_contains_every_photo_correctly_named(self):
        photo1 = self._make_photo("one.jpg", b"content-one")
        photo2 = self._make_photo("two.jpg", b"content-two")

        client = Client()
        client.login(username="staffer", password="pw12345")
        response = client.get(reverse("event-export", args=[self.event.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="summer-party-photos.zip"',
        )

        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = set(zf.namelist())
        self.assertEqual(names, {photo1.filename, photo2.filename})
        self.assertEqual(zf.read(photo1.filename), b"content-one")
        self.assertEqual(zf.read(photo2.filename), b"content-two")

    def test_event_with_zero_photos_returns_empty_zip(self):
        client = Client()
        client.login(username="staffer", password="pw12345")
        response = client.get(reverse("event-export", args=[self.event.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")

        zf = zipfile.ZipFile(io.BytesIO(response.content))
        self.assertEqual(zf.namelist(), [])

    def test_unauthenticated_request_redirects_to_staff_login(self):
        client = Client()
        response = client.get(reverse("event-export", args=[self.event.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("staff-login"), response["Location"])

    def test_guest_non_staff_request_redirects_to_staff_login(self):
        User.objects.create_user(username="guest", password="pw12345", is_staff=False)
        client = Client()
        client.login(username="guest", password="pw12345")
        response = client.get(reverse("event-export", args=[self.event.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("staff-login"), response["Location"])
