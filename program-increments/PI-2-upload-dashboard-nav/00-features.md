# PI-2: Upload ↔ Dashboard navigation, standardized notifications, admin dashboard polish

Four features so far (more may be added later, per the user — no need to force 3-5).

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

---

## Feature C — Admin dashboard: no collapsing panels, IP-verified notification

**Problem.** The admin dashboard's four hub sections (network address, Wi-Fi, Google Drive,
recovery email) were `<details>`/`<summary>` accordions — click the heading to expand/collapse.
The admin wants them always fully visible, no click-to-open step. Separately, successfully
verifying the network address updated the status dot but gave no explicit confirmation — wanted
a notification (using Feature B's new component) on success.

**Scope.**
- **C1**: convert all four `<details class="hub-details">` sections in `admin_management.html`
  to plain `<div class="hub-section">` — same heading/status-dot/body content, no native
  `<details>` disclosure semantics. Removed the now-dead `.hub-details` collapse CSS.
- **C1b** (amendment, after testing): the admin still wanted collapse/expand, but explicitly
  *not* tied to any server-side condition (the old `<details {% if verify_token %}open{% endif
  %}>` etc. auto-opened a section whenever an unrelated action happened — e.g. starting an IP
  check, or a Drive error). Added a dedicated `.hub-toggle-btn` (▸, rotates on toggle)
  positioned in each box's top-right corner; a single shared click handler toggles that
  section's `.details-body[hidden]` — nothing else in the page ever touches it. Sections start
  expanded on every fresh page load (no persistence across reloads — not asked for).
- **C2**: the IP-verification poll's success branch now also calls
  `window.notify('Adresse réseau vérifiée !', 'success')`.

**Actors.** Admin only (this page is `@superuser_required` already).

---

## Feature D — Wi-Fi credentials: manual verification via QR scan

**Problem.** PI-1's Wi-Fi box (US-E3) only ever did an automated format/policy check — deemed
safe but limited: "looks well-formed" is not "actually connects". The admin wants a real,
human-driven test: save credentials, scan the resulting QR code with an actual phone, and
confirm whether it truly works — replacing the "Enregistrer" (Save) button with "Vérifier"
(Verify) as the single action.

**Scope.** New tri-state `SiteSettings.wifi_verified` (`None` = never tested, `True` = admin
confirmed it works, `False` = admin confirmed it's broken) drives the Wi-Fi status dot instead
of the format check (grey / green / red — mirroring the network-address box's own
verified/failed states). Clicking "Vérifier" saves the credentials (resetting `wifi_verified` to
`None`, since a fresh save invalidates any prior confirmation) and, if the format check still
passes, auto-opens a popup with a QR code (from a new admin-only preview endpoint that bypasses
any per-event `wifi_qr_enabled` toggle — it's testing the credentials themselves, not a specific
event's display setting) plus a "?" button explaining the admin should forget the Wi-Fi network
on their phone and try reconnecting via the scan. Two outcome buttons — "C'est cassé" / "Ça
marche du feu de Dieu !" — set `wifi_verified` accordingly and close the loop. Format-check
validation (`wifi_credentials_check`) stays as a pre-condition (no popup for garbage
credentials) and its inline error message is unchanged.

**Out of scope.** No automated/live network join attempt anywhere — this remains a
human-driven confirmation by design (see PI-1 US-E3's rationale, still valid: an automated join
risks dropping the server's own connection at a live event).

**Actors.** Admin only.

---

## Feature E — Simple, non-technical error pages

**Problem.** `DEBUG = True` was hardcoded unconditionally, including in the packaged .exe/.dmg
distribution — meaning a real end user (per the README's own framing: "un ordinateur unique,
pas de compte technique") would see Django's full technical debug page — source snippets,
settings dump, full traceback — on any unhandled error. Django only ever uses custom error
templates when `DEBUG` is `False`; while `DEBUG=True` (unconditionally, before this feature),
they'd have been completely inert regardless of whether they existed.

**Scope.**
- `DEBUG` is now `os.environ.get("DJANGO_DEBUG", "0" if IS_FROZEN else "1") == "1"` —
  off by default in the packaged build, on by default everywhere else (Docker/dev), so tracebacks
  stay visible during active development; `DJANGO_DEBUG=0`/`=1` overrides either default (e.g. to
  preview these pages locally: `DJANGO_DEBUG=0 docker compose up`).
- Four templates at the project's template root (`photos/templates/{400,403,404,500}.html`) —
  Django's default error views find these automatically by name, no custom handler functions
  needed. Same minimal centered-card style as `no_active_event.html`; a short French message, no
  exception/traceback content, one link back to `/`.
- **Real bug caught and fixed along the way**: media serving (`config/urls.py`) was wired via
  `if settings.DEBUG: urlpatterns += static(...)` — `django.conf.urls.static.static()`
  deliberately no-ops when `DEBUG` is `False`, which would have silently taken down every guest
  photo/whiteboard image in the packaged build the moment `DEBUG` became conditional. Media is
  now served by a URL pattern wired directly (independent of `DEBUG`) — this app has no reverse
  proxy in front of it in any deployment mode, so it must always serve its own media itself.

**Out of scope.** No change to `photos/admin.py`/Django's own `/admin/` site styling (already a
documented exclusion in this PI, see Feature C/D above) — the custom templates are Django's
generic site-wide error pages, not admin-specific.

**Actors.** Everyone — this is what any user, guest or staff, sees on an unhandled error once
the app runs with `DEBUG=False` (the packaged build's default).
