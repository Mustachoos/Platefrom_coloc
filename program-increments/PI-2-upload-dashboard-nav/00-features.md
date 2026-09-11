# PI-2: Upload ↔ Dashboard navigation

One feature so far (more may be added later, per the user — no need to force 3-5).

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
