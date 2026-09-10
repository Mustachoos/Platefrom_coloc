# US-A1 — Admin deletes an event

**As** an admin, **I want** to delete an event from the dashboard's event list, **so that**
old/test events don't accumulate with no way to remove them.

**Feature:** A. **Depends on:** none.

## Contract

- New URL: `dashboard/events/<int:event_id>/delete/`, name `event-delete`, POST only.
- New view `event_delete_view(request, event_id)` in `photos/views.py`.
- Permission: `superuser_required` — the existing decorator in `photos/admin_views.py`
  (`user_passes_test(lambda u: u.is_authenticated and u.is_superuser, login_url="dashboard")`),
  imported into `views.py`. Not `@staff_member_required` — this is admin-only, deliberately
  stricter than `create_event_view`/`event_switch_view`.
- Guard: if `event.is_active`, do nothing but set an error message ("Switch to another event
  before deleting this one.") and redirect back — same rejection style as
  `event_switch_view`'s existing guards, no exception raised.
- On a valid POST: delete the `Event` row. `Photo`/`WhiteboardDrawing`/`UserIdentity` cascade via
  the existing `on_delete=CASCADE` FKs — but Django's cascade only removes DB rows, not files on
  disk. Before calling `event.delete()`, iterate `event.photos.all()` and
  `event.whiteboard_drawings.all()` and call `.image.delete(save=False)` on each, so orphaned
  media files aren't left behind (mirrors what `signals.py`'s `remove_file_and_notify_tv`
  already does for a single-photo delete).
- Success message names the deleted event; redirect to `_dashboard_redirect(tab="events")`.
- UI: a `<form method="post">` + `btn btn--danger btn--sm` "Delete" button in the dashboard's
  events tab, matching the existing delete-guest/delete-photo pattern in `dashboard.html` (no
  confirmation modal — the app has none anywhere today; don't introduce a new UI pattern for
  this one action). Hide/disable the button for the row where `event.is_active` is true.

## Acceptance criteria

- Given a non-active event with photos, when an admin POSTs to `event-delete`, then the event,
  its photos (DB rows + files), whiteboard drawings, and guest identities are all gone, and the
  dashboard shows a success message.
- Given the currently active event, when an admin POSTs to `event-delete`, then nothing is
  deleted, an error message explains why, and the event still appears in the list.
- Given a staff (non-superuser) user, when they POST to `event-delete`, then they're redirected
  to `dashboard` without anything being deleted (decorator's `login_url="dashboard"`).

## Files touched

`photos/views.py`, `photos/urls.py`, `photos/templates/photos/dashboard.html`.
