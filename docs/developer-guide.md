# Developer guide

A map of this codebase and the conventions it follows, written so someone (human or AI) picking this
project up cold can stay consistent with what's already here instead of re-deriving it — or worse,
drifting away from it one file at a time. Pairs with `docs/code-quality-report.md` (what's rough today)
and `docs/user-types.md` (what each kind of visitor can do).

## What this app is

PartyBooth ("Platefrom_coloc" in the repo) is a local-network party photo wall: guests scan a QR code,
upload photos from their phones, photos appear live on a TV via WebSocket. Full functional spec (in
French) is in the root `README.md` — treat its *behavioral* description as generally trustworthy, but see
`docs/code-quality-report.md`'s "Documentation gaps" section for where it's known to be stale or
self-contradictory before relying on it for something load-bearing.

Two ways this app runs, and both matter when you're deciding where a change belongs:
- **Dev**: Docker Compose, PostgreSQL, `docker compose up --build`.
- **Packaged**: a standalone PyInstaller build ("PartyBooth.exe" and equivalents), SQLite, no Docker,
  built by `.github/workflows/release.yml` from `packaging/`. `config/settings.py`'s `IS_FROZEN` branch
  is the fork point between the two — check it before assuming an env var or file path works the same in
  both modes.

## Where things live

- `photos/` — the one Django app. Almost everything is here.
  - `views.py` — guest-facing + staff dashboard views (function-based, no class-based views here).
  - `admin_views.py` — superuser-only admin account/hub views, plus the two auth exceptions that run
    logged-out (accepting a subadmin invite, the network-verification landing page). Read its module
    docstring first; it explains the access-rule split from `views.py` explicitly.
  - `models.py`, `forms.py`, `urls.py`, `signals.py`, `middleware.py`, `consumers.py` (WebSocket) — as
    named.
  - `drive_service.py`, `gmail_service.py`, `email_service.py`, `event_service.py`,
    `whiteboard_service.py` — the "service layer": each wraps one external integration or one piece of
    business logic behind a small function API, kept out of `views.py`/`admin_views.py`. Follow this
    split for new integrations rather than inlining API calls into a view.
  - `templatetags/icons.py` — inlines self-hosted SVGs (see "Icons" below).
  - `management/commands/` — CLI-only entry points (currently just the interactive Drive auth command).
- `static/photos/` — `tokens.css` (CSS custom properties), `base.css`, `components.css` (the design
  system — see below), `icons/*.svg`, `tv.js`.
- `photos/templates/photos/` — flat, no `{% extends %}` anywhere in this template set. Shared chrome is
  done via `{% include %}` partials (`_page_header.html`, `_footer_nav.html`, `_account_button.html`,
  `_photos_segmented.html`), not template inheritance.
- `photos/migrations/` — see `docs/code-quality-report.md`'s migration-history section before assuming a
  remove-then-readd or a duplicate-numbered pair is a mistake; it's usually not.
- `packaging/` — PyInstaller spec, launcher, per-OS installer config. `.github/workflows/release.yml`
  drives the actual release build.
- `docs/` — this file, `code-quality-report.md`, `ui-guidelines/README.md` (design system, kept current
  as of this writing — see below), `user-types.md` (accurate, models the target for the others).
- `graphify-out/` — a generated code-graph (see "Keeping the code graph current" below). Not
  hand-maintained; don't hand-edit anything in it.

## The design system (frontend conventions)

Three files, loaded in this order on every page: `tokens.css` → `base.css` → `components.css`. Classes
are BEM-ish: `.card`, `.card--solid`, `.btn`, `.btn--dark`/`.btn--light`/`.btn--outline`/`.btn--danger`,
`.field`/`.input`, `.badge`/`.badge--success`/`.badge--warning`/`.badge--danger`, `.alert`/
`.alert--boxed`/`.alert--success`, `.fab`/`.fab--light`/`.fab--dark`.

`docs/ui-guidelines/README.md` documents this current system in depth (page shell, buttons, icons,
every reusable component, plus the *why* behind several non-obvious decisions — the Android
fixed-positioning bug, the `.card`/`.photo-card` naming collision bug, the bottom-sheet
opacity-vs-pointer-events bug). It used to describe a previous CSS system (`site.css`, `.btn.primary`,
tokens like `--ink`/`--card`) that no longer exists anywhere in the codebase; it was rewritten to match
current reality as part of the same pass that produced this file and `code-quality-report.md`. If you
ever find it drifting from the code again (a new component added without updating it, a class renamed
in one place but not the other), fixing it is cheap and high-value — much cheaper than a future reader
copying a pattern that no longer exists.

Before adding a new CSS class, check `components.css`/`base.css` for one that already does what you
need — the utility classes (`.flex`, `.gap-2xs`/`.gap-xs`/`.gap-sm`, `.text-muted`/`.text-sm`,
`.items-center`, `.justify-between`) cover most one-off layout needs without a new rule.

## Icons

Self-hosted Tabler Icons SVGs, one file per icon under `static/photos/icons/*.svg`, inlined at the call
site via `{% load icons %}{% icon 'name' size=20 %}` (`photos/templatetags/icons.py`). Cross-file `<use
href="sprite.svg#name">` was deliberately avoided (documented in that file) for Safari/iOS reliability,
since guests hit this app on whatever phone they own.

**The exact failure mode to know about**: `{% icon 'name' %}` raises `TemplateSyntaxError: Unknown icon
'name'` if the SVG file is missing, and this has bitten a real packaged release before —
`django.contrib.staticfiles.finders.find()` (which the tag uses) only searches the raw `static/` source
tree, not `STATIC_ROOT`/collectstatic output. `packaging/launcher.spec` bundles both the raw `static/`
tree and the collected `staticfiles/` output specifically to defend against this — if you ever touch that
spec file, keep both.

Before adding a new icon file, grep for whether one you need already exists — an unused `heart.svg` sat
in the icon set for a while because a near-duplicate (`heart-filled.svg`) already covered the actual
need (removed once `code-quality-report.md` caught it; the lesson is the point, not that specific file).

## Google OAuth2 integration pattern

Drive backup and the recovery-email sender share **one OAuth2 client** (`client_secret.json`, uploaded
once via the admin dashboard) and, since this session, **one combined authorization** — connecting from
either the Drive box or the Recovery-email box on `/admin-account/` requests both scopes together
(`drive_service.SCOPES + gmail_service.SCOPES` in `admin_views._google_flow()`) and writes the resulting
credentials to both services' token files. Disconnecting from either box disconnects both, since they're
the same underlying grant. If you add a third Google-API integration, extend this same combined flow
rather than starting a fourth separate OAuth dance. The credential-path readers live in one place now
(`drive_service.token_file()` / `drive_service.client_secret_file()`, imported by `admin_views.py` and
the `google_drive_auth` management command) — add a new service's path reader there too rather than
re-reading the env var locally.

Two easy-to-relearn-the-hard-way facts about this pattern, both currently handled and worth preserving if
you touch this code:
- Gmail's `users.getProfile` rejects a `gmail.send`-only token with a 403 ("insufficient authentication
  scopes") — sending mail and reading account info are gated separately. The "which account is this"
  check goes through the standard OAuth2 `userinfo.email` scope instead (`gmail_service.py`), not through
  the Gmail API itself.
- Google silently adds `openid` to whatever scope set includes `userinfo.email`. `oauthlib` treats any
  requested/granted scope mismatch as a hard exception by default —
  `OAUTHLIB_RELAX_TOKEN_SCOPE=1` (set in `admin_views.py`, alongside the existing
  `OAUTHLIB_INSECURE_TRANSPORT=1` for the localhost-only redirect) is what stops that from 500ing the
  callback.

## The "live-check, don't trust a cached flag" principle

Recurring pattern across `drive_service.py`, `gmail_service.py`, and the verify-IP flow in
`admin_views.py`: a "connected"/"verified" status is never just "a file exists" or "a DB flag is true" —
it's re-proven with a real API call (or a real round-trip request, for the IP-verify case) on every
render of the admin dashboard. Follow this for any new "is X set up correctly" indicator; a stale green
checkmark is worse than a slow page load.

## No automated tests

There is currently no test suite anywhere in this repo (confirmed in `docs/code-quality-report.md`).
Every feature has been verified manually against the running `docker compose` dev container. Until that
changes, the established manual-verification pattern for a change is:

1. `docker compose exec web python manage.py check` after any model/view/URL change.
2. Exercise the actual flow — either via `docker compose exec web python manage.py shell` with Django's
   `django.test.Client` (fast, in-process, easy to mock external services like Gmail/Drive), or via
   `curl`/browser against the live container for things that need real HTTP semantics (cookies, redirects
   you want to see with your own eyes).
3. **Never touch real data while doing this.** Use `_tmp_`-prefixed throwaway usernames/records, and
   delete them again — in the same shell call if possible, so a script failure can't strand test data.
   `stafftest`/`admintest` (created this session) are the two standing exceptions: real, persistent
   accounts meant for manual browser testing, not throwaway.
4. If a test touches anything that survives a container restart (uploaded credential files, OAuth token
   files, `SiteSettings` fields) — redirect the relevant env var to a temp path *before* exercising
   destructive branches like a "disconnect" action, not just the path you think is relevant. A real
   incident this session: forgetting to redirect `GOOGLE_OAUTH_CLIENT_SECRET_FILE` alongside
   `GOOGLE_OAUTH_TOKEN_FILE` before testing a disconnect action deleted the real, uploaded
   `client_secret.json`. Redirect every env var the code path under test can reach, not just the
   obviously-relevant one.

Adding a real `pytest`/`django.test` suite is the single highest-leverage change for this codebase's
long-term health — nothing here currently stops a regression from reaching a real user.

## Keeping the code graph current

`graphify-out/` is generated by the third-party `graphifyy` CLI (`pip install graphifyy`), not
hand-maintained. Two update paths:
- **No API key needed**: `graphify update <path>` — re-runs AST-level extraction against current code,
  refreshes `graph.json`/`graph.html`/`GRAPH_REPORT.md`. Safe to run any time, free, and what generated
  the version currently in the repo (see `GRAPH_REPORT.md`'s "Graph Freshness" section for the commit it
  was built from — compare against `git rev-parse HEAD` to check staleness).
- **Full LLM-semantic re-extraction** (community naming, INFERRED semantic edges): `graphify extract
  <path> --force`, needs an API key for one of gemini/kimi/claude/openai/deepseek/ollama set as an env
  var. Not run this session (no key configured in this environment) — the current graph's community
  labels for anything added/changed this session are filename-based fallbacks (`"admin_views.py"`, etc.)
  rather than the LLM-generated names the older communities have (`"Google Drive Service Layer"`, etc.).
  Re-running this with a key would restore consistent naming across old and new communities.

## Git conventions observed in this repo

- Feature branches per task, merged (not rebased) into whatever the current integration branch is.
  Commit messages lead with *why*, not *what* — read a few recent ones (`git log --oneline`) for tone
  before writing your own.
- Nothing gets pushed or merged to `main` without explicit sign-off — this repo's owner verifies features
  by hand (e.g. real email delivery) before a branch is allowed to merge, and pushes are never assumed
  even after a merge is approved.
