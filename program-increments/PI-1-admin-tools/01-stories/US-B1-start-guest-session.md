# US-B1 — Staff starts a guest session without logging out

**As** a staff/admin user, **I want** a dedicated action to start a guest session in my current
browser, **so that** I can experience the guest flow without logging out of my staff account.

**Feature:** B. **Depends on:** none.

## Contract

- `_get_user_identity(request)` (`photos/views.py`) is already keyed purely on
  `request.session.session_key` + the active `Event` — it has no dependency on
  `request.user.is_authenticated`. `choose_pseudo` (the `/pseudo/` view) already works
  regardless of staff-auth status; nothing about the underlying identity mechanism needs to
  change. This story is entry-point-only: today nothing links to `/pseudo/` from an
  authenticated context.
- Add a "Start a guest session" button/link in the dashboard (and/or `/account/`, see US-B2) for
  authenticated staff users, pointing at the existing `choose-pseudo` URL. No new view needed.
- If a staff user already has a guest identity on this session (i.e. `_get_user_identity(request)`
  returns something), the button should instead read "Continue as guest" / link straight to
  `/upload/` — `choose_pseudo` already redirects there itself when `existing` is found, so this
  is a label-only nicety, not new logic.

## Acceptance criteria

- Given a staff user with no guest identity yet on this session, when they click "Start a guest
  session" from the dashboard, then they land on `/pseudo/` and can pick a pseudo as normal,
  while remaining logged in as staff (staff session untouched).
- Given a staff user who already picked a pseudo this session, when they revisit the dashboard,
  then the entry point reflects that they already have an active guest identity.
- Given a guest identity created this way, `UserIdentity.session_key` equals the staff user's
  current `request.session.session_key` — confirms both identities now share one session.

## Files touched

`photos/templates/photos/dashboard.html` (new entry point only — no Python changes expected).
