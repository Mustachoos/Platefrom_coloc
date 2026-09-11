"""US-B2 — /account/ shows both staff and guest identity panels together.

`account_view` already computes `identity = _get_user_identity(request)`
unconditionally. These tests cover the template-level fix: the staff panel
and the guest panel must render independently (not as mutually-exclusive
branches of the same if/else), so a staff session that also holds a guest
`UserIdentity` (acquired via US-B1's "Start a guest session" entry point)
sees both.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from photos.models import Event, UserIdentity


class DualSessionProfileTests(TestCase):
    def setUp(self):
        # FirstRunRedirectMiddleware funnels every request to /create-admin/
        # until a superuser exists — make this install "claimed" so /account/
        # is actually reachable.
        User.objects.create_superuser(username="owner", password="s3cret-pass", email="owner@example.com")
        self.event = Event.objects.create(name="Launch Party", is_active=True)

    def test_staff_only_session_shows_staff_panel_only(self):
        staff_user = User.objects.create_user(
            username="staffer", password="s3cret-pass", is_staff=True
        )
        self.client.login(username="staffer", password="s3cret-pass")

        response = self.client.get(reverse("account"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Type de compte :")
        self.assertContains(response, "Staff")
        self.assertContains(response, "staffer")
        self.assertNotContains(response, "Type de compte : <strong>Invité</strong>")
        self.assertNotContains(response, "aucun email enregistré")

    def test_guest_only_session_shows_guest_panel_only(self):
        session = self.client.session
        session.save()
        UserIdentity.objects.create(
            event=self.event, pseudo="PartyGuest", session_key=session.session_key
        )

        response = self.client.get(reverse("account"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Type de compte : <strong>Invité</strong>")
        self.assertContains(response, "PartyGuest")
        self.assertNotContains(response, "Changer le mot de passe")
        self.assertNotContains(response, "Se déconnecter")

    def test_dual_session_shows_both_panels_together(self):
        staff_user = User.objects.create_user(
            username="staffer", password="s3cret-pass", is_staff=True
        )
        self.client.login(username="staffer", password="s3cret-pass")

        # Acquire a guest identity on top of the staff session, the way
        # US-B1's dashboard entry point does: POST to choose-pseudo while
        # already staff-authenticated. This fixture event has no Drive
        # folder, so US-F1's redirect goes straight to upload — irrelevant
        # to this test's actual point (session coexistence), just the
        # correct post-F1 behavior for a no-Drive event.
        post_response = self.client.post(reverse("choose-pseudo"), {"pseudo": "PartyGuest"})
        self.assertRedirects(post_response, reverse("upload"))

        response = self.client.get(reverse("account"))

        self.assertEqual(response.status_code, 200)
        # Staff panel present.
        self.assertContains(response, "Staff")
        self.assertContains(response, "staffer")
        self.assertContains(response, "Changer le mot de passe")
        # Guest panel present too.
        self.assertContains(response, "Type de compte : <strong>Invité</strong>")
        self.assertContains(response, "PartyGuest")

        # Staff login must not have been disturbed by acquiring the guest identity.
        self.assertEqual(str(staff_user.pk), self.client.session.get("_auth_user_id"))
