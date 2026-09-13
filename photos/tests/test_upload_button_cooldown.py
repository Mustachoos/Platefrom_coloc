"""New feature: clicking Upload disables the button for 1s (the time for
the in-flight submission to actually go through), so a fast double
click/tap can't fire two submissions of the same photo. This is a plain
(non-AJAX) form submit, so the check is at the JS-source level — the
Django test client can't execute it (same approach as the IP-verify
notification check in test_admin_dashboard_polish.py).
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from photos.models import Event, UserIdentity


class UploadButtonCooldownTests(TestCase):
    def setUp(self):
        self.client = Client()
        get_user_model().objects.create_superuser(
            username="owner", password="pw12345", email="owner@example.com"
        )
        self.event = Event.objects.create(name="Launch Party", is_active=True)
        session = self.client.session
        session.save()
        UserIdentity.objects.create(event=self.event, pseudo="Guest", session_key=session.session_key)

    def test_submit_disables_the_button_for_one_second(self):
        response = self.client.get(reverse("upload"))
        content = response.content.decode()
        self.assertIn("btn.disabled = true;", content)
        self.assertIn("setTimeout(function () { btn.disabled = false; }, 1000);", content)

    def test_a_second_submit_while_disabled_is_prevented(self):
        response = self.client.get(reverse("upload"))
        content = response.content.decode()
        self.assertIn("if (btn.disabled) {", content)
