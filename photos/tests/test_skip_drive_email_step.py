"""US-F1 — Skip the Drive-share email step when Drive isn't configured.

Covers `choose_pseudo` and `share_drive_view` (`photos/views.py`): a guest
should never see the /pseudo/share-drive/ email form for an event that has
no Drive folder connected, whether they arrive there via the normal
choose-pseudo flow or by hitting the URL directly. Events that DO have a
Drive folder connected must keep behaving exactly as before.
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from photos.models import Event, UserIdentity


class SkipDriveEmailStepTests(TestCase):
    def setUp(self):
        self.client = Client()
        # FirstRunRedirectMiddleware funnels every request to /create-admin/
        # until a superuser exists — make this install "claimed" so the
        # pseudo/upload flow under test is actually reachable.
        User.objects.create_superuser(
            username="owner", password="s3cret-pass", email="owner@example.com"
        )

    def test_choosing_pseudo_skips_to_upload_when_no_drive_folder(self):
        Event.objects.create(name="Launch Party", is_active=True, drive_folder_id="")

        response = self.client.post(reverse("choose-pseudo"), {"pseudo": "PartyGuest"})

        self.assertRedirects(response, reverse("upload"))
        self.assertTrue(
            UserIdentity.objects.filter(pseudo="PartyGuest").exists(),
            "the identity should still be created even though share-drive is skipped",
        )

    def test_choosing_pseudo_still_goes_to_share_drive_when_drive_folder_set(self):
        Event.objects.create(
            name="Launch Party", is_active=True, drive_folder_id="folder-123"
        )

        response = self.client.post(reverse("choose-pseudo"), {"pseudo": "PartyGuest"})

        self.assertRedirects(response, reverse("share-drive"))

    def test_direct_hit_on_share_drive_redirects_to_upload_when_no_drive_folder(self):
        event = Event.objects.create(name="Launch Party", is_active=True, drive_folder_id="")
        session = self.client.session
        session.save()
        UserIdentity.objects.create(
            event=event, pseudo="PartyGuest", session_key=session.session_key
        )

        response = self.client.get(reverse("share-drive"))

        self.assertRedirects(response, reverse("upload"))

    def test_direct_hit_on_share_drive_still_renders_form_when_drive_folder_set(self):
        event = Event.objects.create(
            name="Launch Party", is_active=True, drive_folder_id="folder-123"
        )
        session = self.client.session
        session.save()
        UserIdentity.objects.create(
            event=event, pseudo="PartyGuest", session_key=session.session_key
        )

        response = self.client.get(reverse("share-drive"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "photos/share_drive.html")

    def test_skip_button_still_works_when_drive_folder_set(self):
        event = Event.objects.create(
            name="Launch Party", is_active=True, drive_folder_id="folder-123"
        )
        session = self.client.session
        session.save()
        UserIdentity.objects.create(
            event=event, pseudo="PartyGuest", session_key=session.session_key
        )

        response = self.client.post(reverse("share-drive"), {"skip": "1"})

        self.assertRedirects(response, reverse("upload"))
