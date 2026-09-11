"""Tests for US-A1: admin-only event deletion (photos/views.py:event_delete_view).

Covers the acceptance criteria in
program-increments/PI-1-admin-tools/01-stories/US-A1-delete-event.md:

- A non-active event with photos, drawings and guests is fully removed (DB
  rows + media files on disk) when a superuser POSTs to it.
- The currently active event can't be deleted; nothing is removed and an
  error message explains why.
- A staff (non-superuser) user is redirected to the dashboard without
  anything being deleted.
"""

import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from photos.models import Event, Photo, UserIdentity, WhiteboardDrawing

_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="partybooth-test-media-")


def _fake_image(name):
    return SimpleUploadedFile(name, b"not-a-real-image-but-good-enough-for-storage", content_type="image/jpeg")


@override_settings(MEDIA_ROOT=_TEST_MEDIA_ROOT)
class DeleteEventTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser("root", "root@example.com", "password123")
        self.staffer = User.objects.create_user("staffer", "staffer@example.com", "password123", is_staff=True)

    def _build_event(self, name, is_active=False):
        event = Event.objects.create(name=name, is_active=is_active)
        photo = Photo.objects.create(event=event, username="alice", image=_fake_image(f"{name}-photo.jpg"))
        drawing = WhiteboardDrawing.objects.create(
            event=event, username="alice", image=_fake_image(f"{name}-drawing.png")
        )
        identity = UserIdentity.objects.create(event=event, pseudo="alice", session_key="session-key-1")
        return event, photo, drawing, identity

    def test_superuser_deletes_non_active_event_and_its_media(self):
        event, photo, drawing, identity = self._build_event("Old Party")
        photo_path = photo.image.path
        drawing_path = drawing.image.path
        self.assertTrue(os.path.exists(photo_path))
        self.assertTrue(os.path.exists(drawing_path))

        self.client.force_login(self.superuser)
        response = self.client.post(reverse("event-delete", args=[event.id]))

        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        self.assertFalse(Event.objects.filter(id=event.id).exists())
        self.assertFalse(Photo.objects.filter(id=photo.id).exists())
        self.assertFalse(WhiteboardDrawing.objects.filter(id=drawing.id).exists())
        self.assertFalse(UserIdentity.objects.filter(id=identity.id).exists())
        self.assertFalse(os.path.exists(photo_path))
        self.assertFalse(os.path.exists(drawing_path))

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("Old Party" in m for m in messages))

    def test_cannot_delete_the_active_event(self):
        event, photo, drawing, identity = self._build_event("Current Party", is_active=True)

        self.client.force_login(self.superuser)
        response = self.client.post(reverse("event-delete", args=[event.id]))

        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        self.assertTrue(Event.objects.filter(id=event.id).exists())
        self.assertTrue(Photo.objects.filter(id=photo.id).exists())
        self.assertTrue(WhiteboardDrawing.objects.filter(id=drawing.id).exists())
        self.assertTrue(UserIdentity.objects.filter(id=identity.id).exists())
        self.assertTrue(os.path.exists(photo.image.path))

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("Bascule sur un autre évènement avant de supprimer celui-ci" in m for m in messages))

    def test_staff_non_superuser_cannot_delete(self):
        event, photo, drawing, identity = self._build_event("Someone Else's Party")

        self.client.force_login(self.staffer)
        response = self.client.post(reverse("event-delete", args=[event.id]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("dashboard")))
        self.assertTrue(Event.objects.filter(id=event.id).exists())
        self.assertTrue(Photo.objects.filter(id=photo.id).exists())
        self.assertTrue(WhiteboardDrawing.objects.filter(id=drawing.id).exists())
        self.assertTrue(UserIdentity.objects.filter(id=identity.id).exists())
