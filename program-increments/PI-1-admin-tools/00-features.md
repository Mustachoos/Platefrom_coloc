# PI-1: Admin tools

Four features, formalized from the intake conversation. Grounded against the current code
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

## Decisions locked

Resolved with the user before story-splitting; folded into each feature's scope above.

1. **A — permission tier**: admin (superuser) only.
2. **A↔C dependency**: soft nudge, not a hard gate.
3. **B — entry point**: dedicated dashboard action, not the plain `/pseudo/` page.
4. **D — guest-facing visibility**: visible in "My photos", labeled as hidden.
