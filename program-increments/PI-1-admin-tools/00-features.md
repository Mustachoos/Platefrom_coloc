# PI-1: Admin tools

Six features, formalized from the intake conversation (A-D) plus a wave-3 addition (E-F)
surfaced while manually testing waves 1-2. Grounded against the current code
(`photos/models.py`, `photos/views.py`, `docs/user-types.md`) — each states what exists today and
the gap being closed, not a rewrite of working behavior.

## Feature A — Delete events from the event list

**Problem.** `Event` has `create_event_view` and `event_switch_view` but no delete path. The
event list only ever grows; old/test events accumulate with no way to remove them.

**Scope.** A delete action on the dashboard's event list. Cascades already defined on the model
(`Photo`, `WhiteboardDrawing`, `UserIdentity` all `on_delete=CASCADE` from `Event`) — the delete
removes the event and everything scoped to it in one transaction. Requires a confirmation step
(destructive, irreversible).

**Out of scope.** No soft-delete/undo. No change to the Drive folder itself — a connected Drive
folder is left alone (it's the backup); only local DB rows and local media files are removed.

**Assumed rule** (flag if wrong): the currently active event (`is_active=True`) cannot be
deleted — must be switched away from first, same guard style as `event_switch_view` already uses
for Drive confirmation.

**Actors.** Admin (superuser) only — deliberately stricter than `create_event_view`/
`event_switch_view`, which stay staff-reachable.

---

## Feature B — Dual session (staff + guest), visible on the profile page

**Problem.** A staff/admin browser session and a guest `UserIdentity` are two independent
mechanisms that happen to share one session cookie, but `/account/` only ever renders one panel —
whichever identity "wins" — never both, even when both exist on the same session.

**Scope.** A dedicated "Start a guest session" action in the dashboard/profile (not the plain
`/pseudo/` page reused as-is) that lets a staff-authenticated session also hold a guest
`UserIdentity`. Update `/account/` to render both panels together when both are present: the
existing staff account panel, and the existing guest identity panel, side by side.

**Out of scope.** No capability merge — a dual-session admin still goes through
guest-only screens as a guest and staff-only screens as staff; this is about identity
*coexistence and visibility*, not a permissions change anywhere else.

**Actors.** Staff, Admin.

---

## Feature C — Export an event's photos before deleting it

**Problem.** Per the `Event` model's own docstring, an event with no Drive folder keeps its
photos local with no off-machine backup. Feature A's delete would destroy that only copy with no
way to get the photos out first.

**Scope.** A "Download photos" action (dashboard event list / event detail) that zips all of an
event's photos and serves it as a download to staff/admin. Offered as a nearby convenience action
next to delete on a no-Drive-folder event, not a hard gate — deletion still works without it, but
the delete confirmation for such an event states plainly that no backup exists.

**Out of scope.** No scheduled/automatic backups — on-demand only. No change to how
Drive-connected events already back up.

**Actors.** Staff, Admin.

---

## Feature D — Photo moderation: hide without deleting

**Problem.** Staff's only lever on an unwanted photo today is `dashboard_delete_photo` —
permanent. There's no way to pull something from view temporarily.

**Scope.** A `hidden` state on `Photo`, toggled by staff from the dashboard. A hidden photo is
excluded from the gallery, the TV slideshow, and the likes/Top-3 ranking, but not deleted — staff
can un-hide it, or still hard-delete it later. Its owner still sees it in `/my-photos/`, labeled
as hidden by staff — moderation stays transparent to the guest, not a silent disappearance.

**Out of scope.** No automated/AI moderation — a manual staff toggle only.

**Actors.** Staff, Admin (toggle). Guest (sees hidden-status label on their own photo only).

---

## Feature E — Wi-Fi config becomes site-wide, admin-only

**Problem.** `wifi_ssid`/`wifi_password`/`wifi_security`/`wifi_qr_enabled` live on `Event` today,
edited by staff from the dashboard's TV-layout tab — re-entered per event even though the venue's
Wi-Fi network is almost always the same across events held there. The server's LAN address is
already a global admin-only `SiteSettings` field for the same underlying reason (`admin_views.py`,
`admin_management_view`, already `@superuser_required`) — Wi-Fi should follow that pattern.

**Scope.** Move the four `wifi_*` fields from `Event` to `SiteSettings` (a migration copies the
currently-active event's non-blank values forward before the columns are dropped from `Event`, so
existing config isn't silently lost). Move the write handlers (`save_wifi_config`,
`toggle_wifi_qr` — currently inline in `dashboard_view`'s POST handling) into
`admin_management_view`, operating on `SiteSettings.get_solo()` instead of `active_event`. Update
the three read sites — `tv_view`, `slideshow_settings_api`, `wifi_qr_code` — to read from
`SiteSettings` instead of the active event. Remove the Wi-Fi block from `dashboard.html`'s
TV-layout tab; add it to `admin_management.html`, naturally alongside the existing
`#network-details` LAN-address section since both are physical-network config.

**Out of scope.** No per-event Wi-Fi override — after this, Wi-Fi is one setting for the whole
install, full stop. No change to how the Wi-Fi QR code itself is generated/encoded.

**Actors.** Admin (superuser) only — same tier as every other `admin_management_view` action.

**Amendment after manual testing** (split into US-E2, US-E3): E1 centralized *everything*
Wi-Fi-related onto `SiteSettings`, including whether the QR code shows on TV. Testing surfaced
that the on/off choice should be per-event again (credentials stay site-wide, the toggle doesn't)
— see US-E2. A green "credentials look valid" indicator was also requested, modeled loosely on
the IP-address verification's live/green dynamic, but a real network-join test would risk
dropping the server's own connection at a live event — resolved as a format/policy check only,
not a live test (see US-E3, and the "Decisions locked" entry below).

---

## Feature F — Skip the Drive-share email step when Drive isn't configured

**Problem.** `share_drive_view` (`/pseudo/share-drive/`) always asks a guest for an email to
share Drive access, even when the active event has no `drive_folder_id` at all — there's nothing
to share, so the ask is pure friction. A "Skip" button already exists, but the step still
interrupts the upload flow for no reason.

**Scope.** In `choose_pseudo`, redirect straight to `/upload/` instead of `/share-drive/` after
creating the `UserIdentity` when `active_event.drive_folder_id` is blank. Add the same guard at
the top of `share_drive_view` itself (redirect to `upload` immediately) so directly hitting the
URL can't resurface the step either.

**Out of scope.** No change to the flow when Drive *is* configured — the email ask and "Skip"
button behave exactly as they do today in that case.

**Actors.** Guest (experience only — no staff/admin-facing change).

---

## Decisions locked

Resolved with the user before story-splitting; folded into each feature's scope above.

1. **A — permission tier**: admin (superuser) only.
2. **A↔C dependency**: soft nudge, not a hard gate.
3. **B — entry point**: dedicated dashboard action, not the plain `/pseudo/` page.
4. **D — guest-facing visibility**: visible in "My photos", labeled as hidden.
5. **E — Wi-Fi scope**: becomes site-wide (`SiteSettings`), not just relocated-but-per-event.
6. **Item "TV features gated by availability"** (raised alongside E/F): already implemented —
   `photos/views.py:564-628` already disables/rejects/auto-resets unavailable TV options and
   propagates live via the existing `Event` post-save broadcast. No new story; flag a concrete
   failing scenario later if one turns up.
7. **E2/E3 — Wi-Fi credential validation approach**: format/policy check only (SSID set +
   security-appropriate password length), not a live OS-level network join. Reason: a real join
   attempt could disconnect the server from its own network mid-event, taking the whole app
   offline for every connected guest — too large a risk for what's a checkbox-level feature.
