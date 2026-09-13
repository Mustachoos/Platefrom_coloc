"""US-B2 — Wire Django's `messages` framework into the notify.js notification
component.

Covers the 7 templates that used to render `.alert.alert--boxed` blocks for
`django.contrib.messages` and now emit hidden `<span class="server-message">`
data-carriers instead (picked up by `static/photos/notify.js` on
`DOMContentLoaded`). Since Django's test client can't run JS, these tests
check the server-rendered contract notify.js depends on:
  - the right `data-text`/`data-level` span is present for a given message,
  - the old `.alert.alert--boxed` box is no longer rendered for that message,
  - `notify.js` is included on the page.

admin_management.html gets its own test: it used to have five separate
per-tag `{% for message in messages %}{% if "<tag>" in message.tags %}...`
blocks (one per card) — this story collapses them into one instance of the
pattern near the top of the page. That collapse is checked for: no
duplicated/missing notifications, and multiple queued messages (from two
separate requests, since nothing in the current admin_management_view code
sets two messages within a single request) all show up as distinct spans.
"""

import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.html import escape

from photos import drive_service
from photos.models import Event, Photo, UserIdentity

User = get_user_model()

# Whitenoise's CompressedManifestStaticFilesStorage renames notify.js to
# something like notify.<hash>.js in {% static %} output, so a literal
# "photos/notify.js" substring check would never match a real response —
# match the hashed filename pattern instead.
NOTIFY_JS_SRC_RE = re.compile(r'<script src="[^"]*/photos/notify(?:\.[0-9a-f]+)?\.js">')


def assert_includes_notify_js(testcase, response):
    testcase.assertRegex(response.content.decode(), NOTIFY_JS_SRC_RE)


class AccountNotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        # FirstRunRedirectMiddleware funnels every request to /create-admin/
        # until a superuser exists — make this install "claimed" so /account/
        # is actually reachable.
        User.objects.create_superuser(username="owner", password="s3cret-pass", email="owner@example.com")
        self.client.login(username="owner", password="s3cret-pass")

    def test_success_message_renders_as_notification_span(self):
        response = self.client.post(
            reverse("account"), {"update_email": "1", "email": "owner@example.org"}, follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-text="Email mis à jour."')
        self.assertContains(response, 'data-level="success"')
        # Old inline box for this same message is gone.
        self.assertNotContains(response, "Email mis à jour.</div>")
        assert_includes_notify_js(self, response)

    def test_page_has_no_leftover_alert_boxed_markup(self):
        response = self.client.get(reverse("account"))

        self.assertNotContains(response, "alert--boxed")
        self.assertNotContains(response, "alert--success")


class DashboardNotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_superuser(username="owner", password="s3cret-pass", email="owner@example.com")
        staff = User.objects.create_user(username="staffer", password="s3cret-pass", is_staff=True)
        self.client.login(username="staffer", password="s3cret-pass")

    def test_error_message_renders_as_red_notification_span_not_orange(self):
        # No active event exists, so POSTing to the dashboard hits the
        # "Aucun évènement actif" error branch — a genuine reachable error
        # path that used to render as an (incorrectly orange) inline box.
        response = self.client.post(reverse("dashboard"), {"recreate_drive_folder": "1"}, follow=True)

        message_text = "Aucun évènement actif — crée-en un ci-dessous d'abord."
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-text="{escape(message_text)}"')
        self.assertContains(response, 'data-level="error"')
        self.assertNotContains(response, f"{message_text}</div>")
        assert_includes_notify_js(self, response)

    def test_page_has_no_leftover_alert_boxed_markup(self):
        response = self.client.get(reverse("dashboard"))

        self.assertNotContains(response, "alert--boxed")


class MyPhotosNotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_superuser(username="owner", password="s3cret-pass", email="owner@example.com")
        self.event = Event.objects.create(name="Launch Party", is_active=True)
        session = self.client.session
        session.save()
        self.identity = UserIdentity.objects.create(
            event=self.event, pseudo="PartyGuest", session_key=session.session_key
        )

    def test_success_message_renders_as_notification_span(self):
        photo = Photo.objects.create(event=self.event, username="PartyGuest")
        response = self.client.post(
            reverse("delete-own-photo", args=[photo.id]), {}, follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-text="Photo supprimée."')
        self.assertContains(response, 'data-level="success"')
        self.assertNotContains(response, "Photo supprimée.</div>")
        assert_includes_notify_js(self, response)

    def test_page_has_no_leftover_alert_boxed_markup(self):
        response = self.client.get(reverse("my-photos"))

        self.assertNotContains(response, "alert--boxed")
        self.assertNotContains(response, "alert--success")


class ShareDriveNotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_superuser(username="owner", password="s3cret-pass", email="owner@example.com")
        self.event = Event.objects.create(name="Launch Party", is_active=True, drive_folder_id="folder-123")
        session = self.client.session
        session.save()
        UserIdentity.objects.create(event=self.event, pseudo="PartyGuest", session_key=session.session_key)

    def test_error_message_renders_as_red_notification_span(self):
        with patch("photos.views.drive_service.test_share", side_effect=drive_service.DriveError("boom")):
            response = self.client.post(
                reverse("share-drive"), {"email": "guest@example.com"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-text="Impossible de partager le dossier Drive, réessaie."')
        self.assertContains(response, 'data-level="error"')
        self.assertNotContains(response, "Impossible de partager le dossier Drive, réessaie.</div>")
        assert_includes_notify_js(self, response)

    def test_page_has_no_leftover_alert_boxed_markup(self):
        response = self.client.get(reverse("share-drive"))

        self.assertNotContains(response, "alert--boxed")
        self.assertNotContains(response, "alert--success")


class EventSwitchConfirmNotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_superuser(username="owner", password="s3cret-pass", email="owner@example.com")
        staff = User.objects.create_user(username="staffer", password="s3cret-pass", is_staff=True)
        self.client.login(username="staffer", password="s3cret-pass")
        self.active = Event.objects.create(name="Current Party", is_active=True)
        self.target = Event.objects.create(name="Next Party", is_active=False)

    def test_error_message_renders_as_red_notification_span(self):
        response = self.client.post(
            reverse("event-switch", args=[self.target.id]),
            {"relink_folder": "1", "broken_event_id": self.active.id, "drive_folder_id_or_url": ""},
            follow=True,
        )

        message_text = "Colle l'ID ou l'URL d'un dossier Drive."
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-text="{escape(message_text)}"')
        self.assertContains(response, 'data-level="error"')
        self.assertNotContains(response, f"{message_text}</div>")
        assert_includes_notify_js(self, response)


class UploadNotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_superuser(username="owner", password="s3cret-pass", email="owner@example.com")
        self.event = Event.objects.create(name="Launch Party", is_active=True)
        session = self.client.session
        session.save()
        UserIdentity.objects.create(
            event=self.event, pseudo="PartyGuest", session_key=session.session_key
        )

    def test_error_message_renders_as_red_notification_span(self):
        response = self.client.post(reverse("upload"), {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-text="Choisis au moins une photo."')
        self.assertContains(response, 'data-level="error"')
        self.assertNotContains(response, "Choisis au moins une photo.</div>")
        assert_includes_notify_js(self, response)

    def test_unrelated_photo_status_alert_boxed_pill_is_untouched(self):
        # upload.html still legitimately uses .alert.alert--boxed for the
        # #photo-status pill, which has nothing to do with django.contrib
        # .messages — this story must not have touched it.
        response = self.client.get(reverse("upload"))

        self.assertContains(response, 'id="photo-status"')
        self.assertContains(response, 'class="alert alert--boxed')


class AdminManagementNotificationTests(TestCase):
    """The tricky one: five per-card tag-filtered message blocks collapse
    into one instance of the pattern, placed once near the top of the page.
    """

    def setUp(self):
        self.client = Client()
        User.objects.create_superuser(username="owner", password="s3cret-pass", email="owner@example.com")
        self.client.login(username="owner", password="s3cret-pass")

    def test_single_message_renders_exactly_one_notification_span(self):
        response = self.client.post(
            reverse("admin-management"), {"generate_invite": "1", "invitee_name": ""}, follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-text="{escape("Entre un nom pour l\'invitation.")}"')
        self.assertContains(response, 'data-level="error"')
        # Exactly one server-message span for this one queued message — the
        # old five-blocks-per-tag setup could not duplicate a single message
        # (each block filtered a disjoint tag), but this pins the collapsed
        # behavior down explicitly.
        self.assertEqual(response.content.decode().count('class="server-message"'), 1)

    def test_two_messages_queued_across_requests_both_show_once_each(self):
        # Nothing in the current admin_management_view code sets two
        # messages within a single request/response cycle (every POST
        # branch calls messages.error/success at most once before
        # redirecting) — so the genuinely reachable multi-message case is
        # two separate actions (e.g. two quick form submissions) whose
        # messages both stay queued in the session until the next page
        # render actually iterates `messages` and displays them.
        # assertRedirects's default fetch_redirect_response=True would GET
        # the redirect target itself to confirm it's a 200 — but that GET
        # renders admin_management.html and would consume the very message
        # this test is trying to keep queued, so check the redirect target
        # without letting it follow through.
        response1 = self.client.post(
            reverse("admin-management"), {"generate_invite": "1", "invitee_name": ""}
        )
        self.assertRedirects(response1, reverse("admin-management"), fetch_redirect_response=False)

        response2 = self.client.post(
            reverse("admin-management"), {"start_verify_ip": "1", "ip_address": ""}
        )
        self.assertRedirects(response2, reverse("admin-management"), fetch_redirect_response=False)

        response3 = self.client.get(reverse("admin-management"))

        self.assertEqual(response3.status_code, 200)
        self.assertContains(response3, f'data-text="{escape("Entre un nom pour l\'invitation.")}"')
        self.assertContains(response3, 'data-text="Entre une adresse IP à vérifier."')
        content = response3.content.decode()
        self.assertEqual(content.count('class="server-message"'), 2)
        # No message rendered as an old inline box tied to a specific card.
        self.assertNotContains(response3, "Entre un nom pour l'invitation.</div>")
        self.assertNotContains(response3, "Entre une adresse IP à vérifier.</div>")

    def test_wifi_tagged_message_shows_once_near_top_not_inside_its_old_card(self):
        # Before this story, a "wifi"-tagged message rendered only inside
        # the Wi-Fi card's own block. Now every message renders once, in
        # the single collapsed block near the top of the page — confirm the
        # notification appears before the per-card content (Staff card,
        # then the Wi-Fi card further down), not duplicated into the card.
        response = self.client.post(
            reverse("admin-management"),
            {"save_wifi_config": "1", "wifi_ssid": "PartyWifi", "wifi_password": "s3cretpw12", "wifi_security": "wpa"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertEqual(content.count('data-text="Détails Wi-Fi enregistrés."'), 1)
        notify_index = content.index('data-text="Détails Wi-Fi enregistrés."')
        staff_card_index = content.index('Staff (')
        wifi_card_index = content.index('id="wifi-details"')
        self.assertLess(
            notify_index, staff_card_index,
            "the collapsed notification block should sit near the top of the page, before the Staff card",
        )
        self.assertLess(notify_index, wifi_card_index)
        assert_includes_notify_js(self, response)
