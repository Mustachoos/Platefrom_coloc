# US-D1 — Staff can hide/unhide a photo

**As** staff, **I want** to toggle a photo's visibility without deleting it, **so that** I can
pull something from view and still restore it later.

**Feature:** D. **Depends on:** none.

## Contract

- New field on `Photo` (`photos/models.py`): `hidden = models.BooleanField(default=False)`. New
  migration (`python manage.py makemigrations photos`).
- New URL: `dashboard/photos/<int:photo_id>/toggle-hidden/`, name `dashboard-toggle-photo-hidden`,
  POST only. New view `dashboard_toggle_photo_hidden(request, photo_id)` in `photos/views.py`,
  decorated `@staff_member_required(login_url="staff-login")` — same tier as
  `dashboard_delete_photo` (a per-photo dashboard action, same pattern, dedicated endpoint rather
  than folded into `dashboard_view`'s monolithic POST handling).
- Toggling flips `photo.hidden` and saves (`update_fields=["hidden"]`), then redirects to
  `_dashboard_redirect(tab="photos")` with a message ("Photo hidden." / "Photo unhidden.").
- Broadcast the change live (mirrors `remove_file_and_notify_tv` in `signals.py`, which already
  broadcasts on hard delete): on hide, `channel_layer.group_send("tv_updates", {"type":
  "photo.hidden", "url": photo.image.url})`; on unhide, reuse the existing `"photo.uploaded"`
  message shape (`{"type": "photo.uploaded", "photo": _photo_payload(photo)}`) — the TV's
  client-side `photos` array only ever grows by appending "uploaded" events (see
  `static/photos/tv.js`), so re-appearing after an unhide is handled the same way a fresh upload
  is; no new client-side "unhidden" case needed.
- UI: in the dashboard's photos tab (`dashboard.html`), add a toggle button next to the existing
  Delete button per photo — "Hide" when `not photo.hidden`, "Unhide" when `photo.hidden` — and a
  visible "Hidden" badge on the thumbnail when `photo.hidden` is true, so staff can tell at a
  glance without opening anything.

## Acceptance criteria

- Given a visible photo, when staff POSTs the toggle, then `photo.hidden` becomes `True`, TV
  removes it live via the new `"photo.hidden"` WS message, and the dashboard shows it as hidden.
- Given a hidden photo, when staff POSTs the toggle again, then `photo.hidden` becomes `False`
  and TV re-adds it live via the reused `"photo.uploaded"` message.
- The photo is never deleted by this action — the DB row and image file are untouched either way.

## Files touched

`photos/models.py` (+ migration), `photos/views.py`, `photos/urls.py`, `static/photos/tv.js`
(new `"hidden"` case in the WS `onmessage` handler, splicing by `url` the same way `"deleted"`
already does), `photos/templates/photos/dashboard.html`.
