# US-D2 — Hidden photos excluded from guest-facing views, visible in "My photos"

**As** a guest, **I want** a hidden photo to disappear from the shared gallery/TV/ranking, but
still show up in my own "My photos" (labeled), **so that** moderation is transparent, not a
silent disappearance.

**Feature:** D. **Depends on:** US-D1 (needs the `hidden` field to exist).

## Contract

Three separate query sites need the exclusion — there is no single shared choke point:

- `gallery_view` (`photos/views.py`): `Photo.objects.filter(event=active_event)` →
  `.filter(event=active_event, hidden=False)`. This is what `/gallery/` renders, and what feeds
  the likes/Top-3 ranking client-side in `static/photos/gallery.js` (if the ranking is computed
  there) — excluding at the query covers ranking automatically, no separate ranking code path.
- `photo_list_api` (`photos/views.py`, `/api/photos/`): same `.filter(hidden=False)` addition,
  for whatever consumes this endpoint (kept in scope even though TV itself doesn't call it — see
  `graphify query "what calls photo-list-api"` if it's unclear who else depends on it before
  changing its shape).
- TV's live feed (`static/photos/tv.js`): **not a query** — TV holds an in-memory `photos` array
  built purely from WS events, no initial snapshot fetch. US-D1 already covers this side (hiding
  broadcasts `"photo.hidden"` to remove it live; unhiding reuses `"photo.uploaded"` to re-add
  it) — nothing further needed here, don't duplicate that work in this story.
- `my_photos_view` (`photos/views.py`): **no filtering change** — it already queries
  `Photo.objects.filter(event=user.event, username=user.pseudo)` with no `hidden` exclusion, and
  should stay that way. Add a "Hidden by staff" label in `my_photos.html`, shown per-photo when
  `photo.hidden` is true (template-only change, `hidden` is already a plain field on each
  `photo` object in context — no view change needed).
- `like_toggle_api`: add a `hidden` check — reject liking a hidden photo (`403`, same style as
  the existing "likes are disabled" rejection) since it shouldn't be likeable while pulled from
  view.

## Acceptance criteria

- Given a hidden photo, it does not appear in `/gallery/`, is excluded from `/api/photos/`, and
  cannot be liked via `like_toggle_api` (403).
- Given a hidden photo already visible on a connected TV screen, it disappears live (covered by
  US-D1's broadcast — verify here as an integration check across both stories).
- Given a hidden photo belonging to a guest, `/my-photos/` still lists it, labeled "Hidden by
  staff".
- Given the same photo unhidden, all of the above reverse — it reappears everywhere and can be
  liked again.

## Files touched

`photos/views.py`, `photos/templates/photos/my_photos.html`.
