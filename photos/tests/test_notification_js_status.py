"""US-B3 — wire upload/whiteboard JS status feedback into the shared notify.js
component.

Most of this story's acceptance criteria are about client-side JS behavior
(the notify() queue animating, the whiteboard's terminal calls using the
right level) that Django's test client can't execute — there's no JS engine
here. What we *can* verify with `Client`/`assertContains` is the
server-rendered contract this story changes:

- upload.html no longer server-renders "Envoi réussi" as the status box's
  displayed content, and no longer carries the old `data-just-uploaded`
  attribute the previous (pre-notify.js) JS used to detect that state --
  the box's initial/default content is now always the empty state, and the
  `just_uploaded` context value is now only consumed to conditionally call
  `window.notify(...)` from the inline script.
- both templates include notify.js before their own inline <script>.
- whiteboard_draw.html has no remaining #upload-status element, showStatus
  function, or its dead CSS.
- the whiteboard template's terminal notify() calls use the right level,
  and the dropped in-flight "Envoi..." call is gone.

Not meaningfully testable here (documented rather than faked): that
notify() actually renders/animates/queues in the browser, that the status
box visually reflects "no file selected" the instant the notification
appears, and that file selection (camera/gallery) still updates the box --
all of that requires a JS-executing browser, not Client/assertContains.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from photos.models import Event, UserIdentity


class UploadNotifyStatusTests(TestCase):
    def setUp(self):
        self.client = Client()
        # FirstRunRedirectMiddleware funnels every request to /create-admin/
        # until a superuser exists.
        get_user_model().objects.create_superuser(
            username="owner", password="pw12345", email="owner@example.com"
        )
        self.event = Event.objects.create(name="Launch Party", is_active=True)

    def _join_as_guest(self, pseudo):
        session = self.client.session
        session.save()
        UserIdentity.objects.create(event=self.event, pseudo=pseudo, session_key=session.session_key)

    def test_initial_load_has_empty_state_and_no_old_markup(self):
        self._join_as_guest("PartyGuest")

        response = self.client.get(reverse("upload"))

        self.assertEqual(response.status_code, 200)
        # The persistent status box always starts in the empty state now.
        self.assertContains(response, 'id="photo-status"')
        self.assertContains(response, "Pas encore de photo :(")
        # The old detection attribute is gone entirely.
        self.assertNotContains(response, "data-just-uploaded")
        # The status box itself no longer server-renders the success text
        # as its displayed content (it's JS-driven via notify() now).
        self.assertNotContains(response, ">Envoi réussi<")

    def test_just_uploaded_still_passed_and_box_stays_empty_state(self):
        self._join_as_guest("PartyGuest")

        response = self.client.get(reverse("upload"), {"uploaded": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["just_uploaded"])
        # Box content/markup is unaffected by just_uploaded now -- still the
        # plain empty-state box, no data-just-uploaded, no success class
        # baked onto #photo-status itself.
        self.assertContains(response, 'id="photo-status" class="alert alert--boxed">Pas encore de photo :(')
        self.assertNotContains(response, "data-just-uploaded")
        # The one-time success feedback is wired as a JS call driven by the
        # server-provided flag, not as server-rendered box content.
        self.assertContains(response, "window.notify('Envoi réussi', 'success')")

    def test_just_uploaded_false_does_not_trigger_notify_flag(self):
        self._join_as_guest("PartyGuest")

        response = self.client.get(reverse("upload"))

        self.assertFalse(response.context["just_uploaded"])
        self.assertContains(response, "const justUploaded = false;")

    def test_notify_js_included_before_inline_script(self):
        self._join_as_guest("PartyGuest")

        response = self.client.get(reverse("upload"))
        content = response.content.decode()

        # ManifestStaticFilesStorage hashes the filename (notify.<hash>.js),
        # so match on the static path prefix rather than the literal name.
        notify_pos = content.find('src="/static/photos/notify.')
        inline_pos = content.find("(function(){")
        self.assertNotEqual(notify_pos, -1, "notify.js should be included on upload.html")
        self.assertLess(notify_pos, inline_pos, "notify.js must load before the page's inline script")


class WhiteboardNotifyStatusTests(TestCase):
    def setUp(self):
        self.client = Client()
        get_user_model().objects.create_superuser(
            username="owner", password="pw12345", email="owner@example.com"
        )
        self.event = Event.objects.create(name="Launch Party", is_active=True, whiteboard_enabled=True)

    def _join_as_guest(self, pseudo):
        session = self.client.session
        session.save()
        UserIdentity.objects.create(event=self.event, pseudo=pseudo, session_key=session.session_key)

    def test_no_dead_upload_status_markup_remains(self):
        self._join_as_guest("PartyGuest")

        response = self.client.get(reverse("whiteboard-draw"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("upload-status", content)
        self.assertNotIn("showStatus", content)
        self.assertNotIn("statusHideTimeout", content)

    def test_notify_js_included_before_inline_script(self):
        self._join_as_guest("PartyGuest")

        response = self.client.get(reverse("whiteboard-draw"))
        content = response.content.decode()

        notify_pos = content.find('src="/static/photos/notify.')
        inline_pos = content.find("(function () {")
        self.assertNotEqual(notify_pos, -1, "notify.js should be included on whiteboard_draw.html")
        self.assertLess(notify_pos, inline_pos, "notify.js must load before the page's inline script")

    def test_terminal_notify_calls_use_expected_levels(self):
        self._join_as_guest("PartyGuest")

        response = self.client.get(reverse("whiteboard-draw"))

        self.assertContains(response, "notify('Ajouté au tableau !', 'success')")
        self.assertContains(response, "notify('Attends un peu avant de renvoyer.', 'warning')")
        self.assertContains(response, "notify(data.error || 'Impossible d\\'envoyer le dessin.', 'error')")
        self.assertContains(response, "notify('Erreur réseau, réessaie.', 'error')")

    def test_in_flight_sending_notification_is_not_migrated(self):
        self._join_as_guest("PartyGuest")

        response = self.client.get(reverse("whiteboard-draw"))

        # The in-flight "Envoi..." call is deliberately dropped, not moved
        # to notify() -- uploadBtn.disabled is the in-flight indicator now.
        self.assertNotContains(response, "Envoi…")
