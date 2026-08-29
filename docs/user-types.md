# User types

Three kinds of visitor exist in this app, backed by two entirely separate
identity mechanisms — that split is the source of most "why can't this
guest do X" or "why does staff need a password but guests don't" questions,
so it's worth understanding before anything else here.

## Guest

**Identity**: no account, no password. A guest is a `UserIdentity` row
(`photos/models.py`) tied to their browser session and the currently active
`Event` — a pseudo, unique only within that event (`unique_together =
(("event", "pseudo"), ("event", "session_key"))`). The same pseudo becomes
available again once the event changes. Set once via `/pseudo/`
(`_get_user_identity()` in `photos/views.py` is the single lookup used
everywhere a view needs "who is this guest").

**Data held**: pseudo, an optional email (only ever collected once, on
`/pseudo/share-drive/`, for read access to the event's Google Drive folder
— not used for anything else), and internal bookkeeping for that Drive
share (`drive_shared`, `drive_permission_id`).

**Can do**:
- Choose a pseudo and, optionally, share an email for Drive access
- Upload photos (`/upload/`), from the camera or the phone's gallery
- Browse the shared gallery (`/gallery/`) and like/unlike photos (if the
  event has likes enabled)
- View and delete **their own** photos only (`/my-photos/`) — enforced
  server-side by event + pseudo + identity, not just hidden in the UI
- Draw on the collective whiteboard (`/whiteboard/`), if enabled for the
  event, subject to a 30-second cooldown between submissions
- View their own account info — pseudo and email if set — on `/account/`

**Cannot**: see any other guest's identity beyond their pseudo on shared
content, delete anyone else's photos, reach `/dashboard/` or anything
staff-only, or change a "password" (none exists for a guest — there's
nothing to authenticate, the session cookie *is* the identity).

## Staff (subadmin)

**Identity**: a Django `User` with `is_staff=True`, `is_superuser=False`.
Never self-registered — only created by accepting a one-time invite link an
admin generates (`AdminInvite` model, `/admin-account/invite/<token>/`,
expires after use or revocation). Authenticates with a username + password
via `/staff-login/`, gated on staff/admin pages by the
`@staff_member_required` decorator throughout `photos/views.py`.

**Data held**: username, email, password (hashed, standard Django auth).

**Can do**, from `/dashboard/`:
- Create events and switch the active event — switching requires every
  photo of the outgoing event to be confirmed on Drive first (a hard
  guard against data loss, not just a warning)
- Toggle Drive-sharing-with-participants, photo likes, and the whiteboard
  feature per event; reconnect Google Drive if the existing connection
  breaks
- Configure the TV screen's layout (slideshow vs. whiteboard) and its
  bottom-right zone (leaderboard vs. nothing), and the event's Wi-Fi QR
  code (SSID/password/security type)
- Review the whiteboard's composite image and delete individual
  submitted drawings
- View all guests of the active event (pseudo, email, Drive-share status,
  join time) and remove one
- View and delete **any** photo of the active event, not just their own
- View their own account info and **change their own password** (needs
  the current password — `/account/`, via Django's `PasswordChangeForm`)

**Cannot**: invite other subadmins, reach `/admin-account/`, connect or
disconnect the account-wide Google Drive OAuth credentials, verify/set the
server's network address, or do anything else scoped to the admin account
below.

## Admin (superuser)

**Identity**: a Django `User` with `is_superuser=True`. Exactly one gets
created this way, ever — the very first account, via `/create-admin/`
(only reachable while no superuser exists yet, or by that superuser
revisiting it afterward). There is no in-app path to promote an existing
staff account to admin; that would need direct database/shell access.

**Can do**: everything staff can, plus, from `/admin-account/`:
- Generate, copy, revoke, and delete subadmin invite links
- Connect Google Drive account-wide: upload the OAuth client credentials,
  connect a Google account, choose or create the root Drive folder events
  live under, or disconnect entirely
- Verify and set the server's LAN address used to build the QR codes
  guests scan — a live round-trip check (the server calls itself back at
  the typed address), not a trust-what-was-typed field
- Reach Django's own `/admin/` as a technical fallback for anything not
  covered by the dashboard (raw model access to Photos, Identities,
  Likes, Slideshow settings, Events)

Nothing here is staff-only-but-hidden-from-admin — an admin account is a
strict superset of a staff account, by design (per the person who asked
for this doc: "for admin, the same [as staff]" on the account page
specifically, and the wider app follows the same shape).
