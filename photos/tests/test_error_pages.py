"""Custom error pages (400/403/404/500): simple, French, no technical
details — only ever shown when DEBUG is False (Django's own technical
debug page takes over unconditionally otherwise, which is why DEBUG is now
conditional in settings.py: off by default in the packaged/frozen build,
on by default everywhere else so tracebacks stay visible during dev).

Also covers the media-serving fix this required: django.conf.urls.static's
static() helper — which the project used to gate media behind `if
settings.DEBUG` — silently serves nothing once DEBUG=False, which would
have taken down every guest photo/whiteboard image in the packaged build.
Media is now wired directly in config/urls.py, independent of DEBUG.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.test import TestCase, override_settings


class ErrorTemplatesRenderTests(TestCase):
    """Each template loads and renders standalone, independent of the
    view machinery that dispatches to it — catches template-location/
    syntax mistakes directly."""

    def test_all_four_templates_exist_and_render(self):
        for name in ("400.html", "403.html", "404.html", "500.html"):
            try:
                template = get_template(name)
            except TemplateDoesNotExist:
                self.fail(f"{name} not found by Django's template loader")
            content = template.render({})
            self.assertIn("<html", content)
            self.assertIn('lang="fr"', content)

    def test_no_technical_details_leak_into_any_error_template(self):
        for name in ("400.html", "403.html", "404.html", "500.html"):
            content = get_template(name).render({})
            for leaky_word in ("Traceback", "Exception", "exception_value", "Request Method"):
                self.assertNotIn(leaky_word, content)

    def test_each_template_has_a_way_back_into_the_app(self):
        for name in ("400.html", "403.html", "404.html", "500.html"):
            content = get_template(name).render({})
            self.assertIn('href="/"', content)


@override_settings(DEBUG=False)
class ErrorViewDispatchTests(TestCase):
    """End-to-end: a real 404 is actually routed to the custom template,
    not Django's own technical debug page. DEBUG=False is required for
    Django to use custom error templates at all — with DEBUG=True (this
    project's dev default), it always shows its own debug page instead,
    regardless of what these templates say."""

    def test_unknown_url_renders_custom_404_not_djangos_technical_page(self):
        # FirstRunRedirectMiddleware funnels every request to /create-admin/
        # until a superuser exists — "claim" the install first, so this
        # request actually reaches URL resolution instead of being
        # redirected before Django even gets a chance to 404.
        get_user_model().objects.create_superuser(
            username="owner", password="pw12345", email="owner@example.com"
        )
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        content = response.content.decode()
        self.assertIn("Page introuvable", content)
        self.assertNotIn("Django tried these URL patterns", content)


class MediaServingIndependentOfDebugTests(TestCase):
    """django.conf.urls.static.static() no-ops when DEBUG is False — the
    real bug this would have caused in the packaged build, now fixed by
    wiring the media urlpattern directly in config/urls.py instead.

    Deliberately does NOT override_settings(MEDIA_ROOT=...): the urlpattern
    in config/urls.py captures settings.MEDIA_ROOT once, at Django startup
    (same as django.conf.urls.static.static() itself does) — an
    override_settings in a test never reaches an already-built urlpattern,
    so this writes into the real configured MEDIA_ROOT instead, cleaned up
    afterward."""

    def _write_test_media_file(self):
        Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
        test_file = Path(settings.MEDIA_ROOT) / "error_pages_test.txt"
        test_file.write_text("test")
        self.addCleanup(test_file.unlink, missing_ok=True)
        return test_file

    @override_settings(DEBUG=True)
    def test_media_still_served_with_debug_true(self):
        self._write_test_media_file()
        response = self.client.get("/media/error_pages_test.txt")
        self.assertEqual(response.status_code, 200)

    @override_settings(DEBUG=False)
    def test_media_still_served_with_debug_false(self):
        # This is the case django.conf.urls.static.static() would have
        # broken silently (its URL pattern simply wouldn't exist).
        self._write_test_media_file()
        response = self.client.get("/media/error_pages_test.txt")
        self.assertEqual(response.status_code, 200)
