"""US-A1 — a "back to Dashboard" link on the upload page, visible only to
staff/admin (a session that also holds a guest identity, per PI-1's dual
session feature).
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from photos.models import Event, UserIdentity


class UploadDashboardNavTests(TestCase):
    def setUp(self):
        self.client = Client()
        # FirstRunRedirectMiddleware funnels every request to /create-admin/
        # until a superuser exists — make this install "claimed" so /upload/
        # is actually reachable.
        get_user_model().objects.create_superuser(
            username="owner", password="pw12345", email="owner@example.com"
        )
        self.event = Event.objects.create(name="Launch Party", is_active=True)

    def _join_as_guest(self, pseudo):
        session = self.client.session
        session.save()
        UserIdentity.objects.create(event=self.event, pseudo=pseudo, session_key=session.session_key)

    def test_guest_only_session_sees_no_dashboard_link(self):
        self._join_as_guest("PartyGuest")

        response = self.client.get(reverse("upload"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Retour au dashboard")

    def test_staff_session_with_guest_identity_sees_dashboard_link(self):
        get_user_model().objects.create_user(username="staffer", password="s3cret-pass", is_staff=True)
        self.client.login(username="staffer", password="s3cret-pass")
        self._join_as_guest("PartyGuest")

        response = self.client.get(reverse("upload"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Retour au dashboard")
        self.assertContains(response, f'href="{reverse("dashboard")}"')
