"""US-B1 — Staff starts a guest session without logging out.

Covers the dashboard's "Démarrer une session invité" / "Continuer en tant qu'invité" entry
point: it should link to the existing `choose-pseudo` URL, flip its label
once the staff user's session already holds a guest identity, and never
disturb the staff auth session itself.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from photos.models import Event, UserIdentity


class GuestSessionEntryPointTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staffer", password="s3cret-pass", is_staff=True
        )
        # FirstRunRedirectMiddleware funnels every request to /create-admin/
        # until a superuser exists — make this install "claimed" so the
        # dashboard/pseudo flow under test is actually reachable.
        User.objects.create_superuser(username="owner", password="s3cret-pass", email="owner@example.com")
        self.event = Event.objects.create(name="Launch Party", is_active=True)
        self.client.login(username="staffer", password="s3cret-pass")

    def _staff_still_authenticated(self):
        # Cheap, direct check that the staff auth session survived, without
        # depending on any particular dashboard markup.
        return str(self.staff_user.pk) == self.client.session.get("_auth_user_id")

    def test_dashboard_offers_start_guest_session_when_no_identity_yet(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Démarrer une session invité")
        self.assertNotContains(response, "Continuer en tant qu'invité")
        self.assertContains(response, reverse("choose-pseudo"))

    def test_clicking_entry_point_lands_on_pseudo_page_staff_session_untouched(self):
        response = self.client.get(reverse("choose-pseudo"))

        # status_code 200 (not a 302) already proves choose_pseudo did not
        # redirect us away to /upload/, since no guest identity exists yet.
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "photos/choose_pseudo.html")
        self.assertTrue(self._staff_still_authenticated())

    def test_picking_a_pseudo_keeps_staff_logged_in_and_shares_the_session_key(self):
        response = self.client.post(reverse("choose-pseudo"), {"pseudo": "PartyGuest"})

        # self.event has no drive_folder_id, so per US-F1 this skips
        # share-drive and lands straight on upload.
        self.assertRedirects(response, reverse("upload"))
        self.assertTrue(self._staff_still_authenticated())

        identity = UserIdentity.objects.get(event=self.event, pseudo="PartyGuest")
        self.assertEqual(identity.session_key, self.client.session.session_key)

    def test_dashboard_reflects_existing_guest_identity_as_continue_as_guest(self):
        session_key = self.client.session.session_key
        self.assertTrue(session_key, "staff login should have produced a saved session")
        UserIdentity.objects.create(event=self.event, pseudo="ExistingGuest", session_key=session_key)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continuer en tant qu'invité")
        self.assertNotContains(response, "Démarrer une session invité")
        self.assertContains(response, reverse("upload"))

    def test_clicking_continue_as_guest_redirects_straight_to_upload(self):
        session_key = self.client.session.session_key
        UserIdentity.objects.create(event=self.event, pseudo="ExistingGuest", session_key=session_key)

        response = self.client.get(reverse("choose-pseudo"))

        self.assertRedirects(response, reverse("upload"))
        self.assertTrue(self._staff_still_authenticated())
