# US-C1 — Download an event's photos as a ZIP

**As** a staff/admin user, **I want** to download all of an event's photos as a ZIP, **so that**
events with no Drive folder have a manual backup path before being deleted (US-A1).

**Feature:** C. **Depends on:** none (usable standalone; nudged from A1's delete UI per the
soft-nudge decision, not gated).

## Contract

- New URL: `dashboard/events/<int:event_id>/export/`, name `event-export`, GET.
- New view `event_export_view(request, event_id)` in `photos/views.py`, decorated
  `@staff_member_required(login_url="staff-login")` — same tier as event create/switch, **not**
  admin-only (unlike US-A1's delete).
- Build the ZIP in-memory with the stdlib `zipfile` module over an `io.BytesIO()`, iterating
  `event.photos.all()` and adding each via `photo.image.path` (local disk path) under
  `photo.filename` (the existing `Photo.filename` property strips the `photos/` prefix already
  baked into `photo_upload_path`). Return via `HttpResponse(..., content_type="application/zip")`
  with `Content-Disposition: attachment; filename="<event-name-slugified>-photos.zip"`.
- An event with zero photos still produces a (empty) ZIP rather than erroring — simplest
  behavior, no special-case needed.
- UI: a "Download photos" link/button next to each event's Delete button in the dashboard's
  events tab (plain `<a href="{% url 'event-export' event.id %}">`, no form needed — it's a GET).

## Acceptance criteria

- Given an event with photos, when staff hits `event-export`, then a ZIP downloads containing
  every one of that event's photo files, correctly named.
- Given an event with zero photos, the endpoint returns a valid (empty) ZIP, not an error.
- Given an unauthenticated or guest request, the endpoint redirects to `staff-login` (decorator
  behavior, unchanged from every other `@staff_member_required` view).

## Files touched

`photos/views.py`, `photos/urls.py`, `photos/templates/photos/dashboard.html`.
