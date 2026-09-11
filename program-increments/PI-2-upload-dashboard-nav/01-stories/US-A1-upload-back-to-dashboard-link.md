# US-A1 — "Back to Dashboard" link on the upload page

**As** staff/admin, **I want** a link back to the Dashboard from the upload page, **so that** I
don't have to rely on the browser's back button after using "Continue as guest".

**Feature:** A. **Depends on:** none.

## Contract

- `photos/templates/photos/upload.html`: right after the existing `<p class="text-muted
  text-sm">Envoi en tant que <strong>{{ pseudo }}</strong></p>` line, add:
  ```html
  {% if request.user.is_authenticated %}
  <p class="text-sm" style="margin-top:var(--space-3xs);">
    <a class="link" href="{% url 'dashboard' %}">← Retour au dashboard</a>
  </p>
  {% endif %}
  ```
  `request.user` is already available in every template via Django's built-in auth context
  processor — no change to `upload_view` (`photos/views.py`) needed.
- Nothing changes for a guest session with no staff login: `request.user.is_authenticated` is
  `False`, so the link doesn't render.

## Acceptance criteria

- Given a staff or admin user with a guest identity on `/upload/`, the page shows a "Retour au
  dashboard" link pointing at `/dashboard/`.
- Given a guest with no staff session, `/upload/` shows no such link.

## Files touched

`photos/templates/photos/upload.html`.
