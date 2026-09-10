# US-B2 — Profile page shows both staff and guest identity

**As** a staff/admin user who also holds a guest session, **I want** `/account/` to show both my
staff account and my guest identity together, **so that** I don't lose visibility into either.

**Feature:** B. **Depends on:** US-B1 (needs a way to actually acquire a guest identity while
staff-authenticated to be testable end to end — the template/view change here is independent
code, but meaningless to verify without B1's entry point).

## Contract

- `account_view` (`photos/views.py`) already computes `identity = _get_user_identity(request)`
  unconditionally, regardless of `request.user.is_authenticated` — no view-layer change needed,
  the data is already there.
- The gap is entirely in `photos/templates/photos/account.html`: today it's a single
  `{% if request.user.is_authenticated %} ... {% else %} ... {% endif %}` — the guest panel
  (lines ~82-93, "Account type: Guest") only ever renders in the `{% else %}` branch, so it's
  unreachable whenever staff is authenticated, even if `identity` is truthy.
- Change: render the staff panel whenever `request.user.is_authenticated`, **and separately**
  render the guest identity panel whenever `identity` is truthy — the two conditions are
  independent, not mutually exclusive. When both are true, show both panels (e.g. staff panel,
  then a divider, then the guest identity panel underneath).
- When only one is true, behavior is unchanged from today.

## Acceptance criteria

- Given a session with only a staff login (no guest identity), `/account/` shows the staff panel
  only — same as before this change.
- Given a session with only a guest identity (no staff login), `/account/` shows the guest panel
  only — same as before this change.
- Given a session with both (via US-B1's entry point), `/account/` shows both panels together.

## Files touched

`photos/templates/photos/account.html`.
