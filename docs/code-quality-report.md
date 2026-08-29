# Code quality report

Generated 2026-08-29, against commit `7c1f09f7` (branch `admin_credentials_retrieval`). Covers the whole
repo: `photos/`, `config/`, `packaging/`, static assets, templates, migrations, and `docs/`. Produced by
reading every Python module under those paths in full, cross-referencing every template/icon/CSS class
against its call sites, and inspecting the full migration history — not a sampling pass.

Nothing here is urgent. The codebase is small, has no dead files, no `TODO`/`FIXME` debt, no bare
`except:` clauses, and no import cycles (confirmed separately by `graphify-out/GRAPH_REPORT.md`). The
findings below are mostly minor cleanup and a few real documentation gaps.

**Status**: every finding below marked ✅ was applied immediately after this audit (same session),
verified with `manage.py check` plus a live functional test against the running dev container, and is
kept here as the historical record of *why* — same rationale as the migration-history section not being
rewritten away. Findings without a checkmark were deliberately left as-is; each says why inline (usually
because the report itself only flagged it as worth a look, not a clear "do this"). The two doc rewrites
this drove are `README.md` (root) and `docs/ui-guidelines/README.md`, both now current as of this
writing — treat their content as trustworthy again, not stale.

## Obsolete files

**None.** Every `.py` file under `photos/`, `config/`, `packaging/` is imported and reachable. Every
template under `photos/templates/photos/` is reached by a `render()` call, a `template_name=` on a
class-based view, or an `{% include %}`. There is no `{% extends %}` anywhere in the template set — it's
a flat, non-inheriting structure by design, not an oversight.

One repo-hygiene note, not a code issue: `graphify-out/` (a third-party code-graph tool's generated
output — `GRAPH_REPORT.md`, `graph.json`, `graph.html`, plus a `cache/` directory of AST fragments) is
checked into git. It's a build artifact that gets fully rewritten on every `graphify update .` run (see
the diff from this session: ~17,500 line changes to `graph.json` alone for what was, semantically, an
incremental update). Keeping it versioned is a deliberate choice if the team wants graph history
alongside code history; if not, it's a candidate for `.gitignore` plus a "how to regenerate" note in this
guide. Not recommending either way — flagging the tradeoff.

## Obsolete code chunks

- ✅ **`photos/models.py:250-252`** — `AdminInvite.is_used` was a dead property; `AdminInvite.status`
  re-implemented the same check inline instead of calling it. Fixed by having `status` call `is_used`
  (kept the property — it's clearer domain vocabulary — removed the duplication).
- ✅ **`photos/views.py:3`** — unused `import os`. Removed.
- ✅ **`static/photos/icons/heart.svg`** — unused (the gallery's like button uses `heart-filled.svg`
  only; the TV leaderboard's heart is a hand-copied inline SVG in `tv.js`, not this file). Deleted.
- ✅ **Dead CSS classes** — `.gap-3xs`, `.gap-md`, `.text-faint`, `.w-full` (`base.css`) and
  `.input--mono` (`components.css`) removed. **`.sr-only` kept**, per the hedge below — it's the
  standard accessibility "visually hidden, screen-reader-only" utility; its lack of current use likely
  means no screen-reader-only text has been needed yet, not that the class is wrong to have on hand.

## Migration history (informational, not action items)

The migration history is clean — no orphaned dependencies, no duplicate field additions outside what's
noted below. Three points worth understanding if you're new to this codebase, none requiring any fix:

- **`0020_remove_sitesettings_server_host.py` → `0021_sitesettings_server_host.py`** (13 minutes apart):
  a genuine remove-then-readd of the exact same field, just to update its help text. Already applied
  everywhere; not worth squashing.
- **`0014_event_tv_bottom_right.py` and `0014_sitesettings.py`** sharing the number `0014`, reconciled by
  **`0017_merge_20260822_2002.py`** (an empty-operations Django merge migration) — this is normal
  behavior when two branches each add a migration before merging, not a mistake.
- **`0022` → `0023` → `0024`** chronicle the recovery-email feature's within-session pivot: app-password
  design (`0022`) → added a click-to-verify flag (`0023`) → removed both once the design moved to OAuth2
  (`0024`). Reading `0022`-`0024` back to back is a faster way to understand *why* `SiteSettings` looks
  the way it does today than reading the current model alone.

## Duplication worth refactoring

- ✅ **OAuth credential-path env-var readers, tripled.** `GOOGLE_OAUTH_CLIENT_SECRET_FILE` and
  `GOOGLE_OAUTH_TOKEN_FILE` were each read via `os.environ.get(...).strip()` in three separate places
  under three different names. Fixed: `drive_service.py` now owns the one implementation
  (`token_file()`/`client_secret_file()`, made public — no leading underscore — since they're now
  imported cross-module); `admin_views.py` and `google_drive_auth.py` both import and use them instead
  of re-reading the env var locally.
- ✅ **`port = host.split(":", 1)[1] if ":" in host else "8000"`**, tripled in `admin_views.py`. Fixed:
  extracted to `_request_port(request)`, used at all three call sites.
- **OAuth `Flow` construction, four places** — left as-is; lower confidence than the two above, since the scopes and
  `Flow` subclass genuinely differ: `drive_service.build_oauth_flow()` (`drive_service.py:87-97`,
  Drive-only scope, web `Flow`), `admin_views._google_flow()` (`admin_views.py:181-189`, combined
  Drive+Gmail scope, web `Flow`), an inline validation-only construction at `admin_views.py:356`, and
  `InstalledAppFlow.from_client_secrets_file(...)` in the CLI-only `google_drive_auth.py:33` (a different
  `Flow` subclass, since it's meant to run interactively from a terminal). Worth a look if this file
  grows further, not a clean 1:1 duplicate today.
- **`connectWebSocket()`**, implemented near-identically in `static/photos/tv.js:158-216` and inline in
  `photos/templates/photos/whiteboard_draw.html:355-368` — same protocol detection, same `ws://`/`wss://`
  construction against `/ws/tv/`, same 3-second reconnect-on-close. Left as-is; each has a different
  `onmessage` handler so unifying isn't free, and the report's own framing ("low severity... not
  necessarily worth fixing") didn't clear the bar for a change with no test coverage to catch a mistake.

## Error handling

- ✅ **`photos/admin_views.py:358`** (inside `admin_management_view`, validating an uploaded OAuth
  credentials file) — was `except Exception: client_secret_valid = False`, completely silent. Fixed with
  a `logger.debug` (not `warning`/`exception` — this re-validates on every dashboard render while a bad
  file sits there, so a louder level would spam the log; debug is enough to diagnose "why won't step 1
  go green" without noise).
- ✅ **`photos/admin_views.py:288`** (the "send test email" button's error path) — the exception was
  shown to the admin but never logged server-side. Added `logger.exception(...)` alongside the existing
  user-facing message (safe here — only fires on an actual button click, not a per-render check).
- **Systemic, and already deliberate — noted for awareness, not as a bug**: `drive_service.py`'s
  live-check helpers (e.g. `folder_exists()`, `:234-246`) intentionally collapse every failure mode —
  not-found, trashed, expired auth, a network blip — into a single `False`, with no logging, by design
  (documented in the docstring: "any failure ... is reported simply as False"). That's the right call
  for a status indicator that must degrade gracefully, but it means a transient network hiccup and an
  actually-deleted Drive folder look identical from the dashboard *and* the server logs. If Drive
  flakiness ever becomes a real support question, this is the first place to add a debug-level log line
  without changing the user-facing behavior.
- No bare `except:` clauses anywhere in `photos/`, `config/`, or `packaging/`.

## Documentation gaps (the biggest finding in this report)

- ✅ **Root `README.md` was stale and self-contradictory.** It stated Google Drive is optional in the
  intro and then stated the opposite in "Règles métier notables" — a direct contradiction. Fixed (the
  "optional" version was the true one — confirmed against `views.py`'s `create_event_view`, which
  creates an `Event` unconditionally and only attempts a Drive folder `if drive_service.is_configured()`).
  Also fixed: added a "Email de récupération" section documenting the Gmail OAuth2 feature, added the
  `/account/` profile page to the functional walkthrough, replaced every stale `/admin-account/drive/`
  sub-page reference with the real single `/admin-account/` page, added a "Distribution standalone
  (PartyBooth)" section, and added `GMAIL_SEND_TOKEN_FILE` (plus a note that the OAuth vars are now
  shared between Drive and recovery-email) to the env-var table.
- ✅ **`docs/ui-guidelines/README.md` was stale**, documenting the pre-redesign CSS system (`site.css`,
  `.btn.primary`, tokens like `--ink`/`--card`). Rewritten from scratch against the actual current
  `tokens.css`/`base.css`/`components.css` and the real templates that use them — every class name,
  token, and code example in it now corresponds to something that actually exists. The valuable "why"
  lessons from the old version (the Android fixed-positioning bug, the `.card`/`.photo-card` collision
  bug, the bottom-sheet opacity-vs-pointer-events bug) were preserved, re-scoped where the underlying
  mechanism changed (e.g. only `.bottom-nav` is fixed-position now, the header no longer is).
- **`docs/user-types.md` is accurate** — spot-checked several claims (the 30s whiteboard cooldown, the
  `@staff_member_required` gating, the guest/staff/admin permission boundaries) against the actual code
  and all held up. No action needed here; it's a model for what the other docs should look like.
- **No test suite exists anywhere in the repo — left as-is.** Not a single `test*.py` file. This is
  flagged as the single highest-leverage change for this codebase's long-term health, but deliberately
  *not* attempted as part of "apply the report's suggestions": deciding test framework conventions,
  coverage priorities, and structure for a from-scratch suite is a real design decision for whoever
  owns this codebase next, not something to guess at silently under a blanket cleanup pass. Worth its
  own dedicated task.
- **No `CLAUDE.md` or equivalent project-instructions file** — `docs/developer-guide.md` (added
  alongside this report) is a first step in that direction, aimed at any future developer, human or AI.

## What this report deliberately does not cover

Runtime performance, security review beyond what surfaced incidentally (the error-handling section
above), and dependency-vulnerability scanning were out of scope for this pass — a "code quality" read
of correctness/maintainability/documentation, not a security or performance audit.
