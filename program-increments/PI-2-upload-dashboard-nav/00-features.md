# PI-2: Upload ↔ Dashboard navigation, standardized notifications

Two features so far (more may be added later, per the user — no need to force 3-5).

## Feature A — Navigate between the upload page and the Dashboard

**Problem.** A staff/admin user who reaches `/upload/` (e.g. via the dashboard's "Start a guest
session" / "Continue as guest" entry point from PI-1) has no way back to `/dashboard/` except the
browser's back button — no link on the page itself.

**Already satisfied, no new work needed:** the reverse direction — Dashboard → Upload — already
exists. PI-1's US-B1 added "Start a guest session" / "Continue as guest" buttons to
`dashboard.html` that link to `choose-pseudo` / `upload` directly.

**Scope.** Add a link on `/upload/` back to `/dashboard/`, visible only to authenticated staff/admin
(`request.user.is_authenticated` — already available in every template via Django's auth context
processor, no view change needed). Admin's own path to `/admin-account/` already exists from
*inside* `/dashboard/` (PI-1's "Dashboard admin" button) — this story doesn't need to duplicate
that, landing on `/dashboard/` is enough for both tiers.

**Out of scope.** No change to guest-facing behavior — a guest (no staff session) sees nothing new
on `/upload/`.

**Actors.** Staff, Admin.

---

## Feature B — Standardized notification component

**Problem.** Message/status feedback is inconsistent across the app today:
- Django's `messages` framework renders as a static inline box at the top of a card
  (`.alert.alert--boxed`), present on 7 templates (`account.html`, `dashboard.html`,
  `my_photos.html`, `share_drive.html`, `event_switch_confirm.html`, `upload.html`, plus 5
  separate tag-filtered blocks in `admin_management.html`) — no animation, doesn't auto-dismiss,
  and **error messages render in the same orange as warnings** (`.alert--boxed` has no error/red
  variant, even though `--danger`/`--danger-ink` tokens already exist unused in `tokens.css`).
- Client-side JS status feedback (`upload.html`'s `#photo-status`, `whiteboard_draw.html`'s
  `#upload-status`) is bespoke per page, with its own fade timing and no shared styling.

**Scope.** One shared notification component — a rounded rectangle, customizable text +
semantic color — used everywhere feedback currently appears. Animation: fades and slightly
descends into view, holds 3 seconds, then fades and retreats back up (a subtle motion + opacity
cross-fade, not a hard slide from off-screen — refined after the first pass). Four color
variants: success (green), error (red — fixing the current orange-for-errors gap), warning
(orange), info (neutral, new token). Multiple messages queue one at a time, each getting its own
full cycle, mirroring the queuing pattern `static/photos/tv.js` already uses for new-photo
announcements.

Split into three stories since the foundation has to exist before anything can be wired to it:
- **US-B1** — the component itself (CSS + JS), no template integration.
- **US-B2** — wire Django's `messages` framework into it, replacing every current inline alert
  block.
- **US-B3** — wire the JS-triggered status feedback on `/upload/` and `/whiteboard/` into it,
  replacing their bespoke pill logic.

**Out of scope.** The TV screen's "new photo" announcement banner (`tv.html`'s
`#new-photo-overlay`) stays exactly as-is — it shows a photo + username, not just text, and
already has its own working animation/queue.

**Actors.** Everyone — guests and staff/admin alike, since messages appear across guest and
staff pages.
