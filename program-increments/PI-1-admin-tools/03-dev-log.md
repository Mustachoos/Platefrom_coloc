# PI-1 dev log

Status per story, filled in as wave 1 / wave 2 close. Per `program-increments/README.md`'s
Definition of Done: a story is only marked done once its own test(s) pass **and** the full
existing test suite for the PI still passes (regression), not just the new test.

| Story | Status | Tests | Commit | Notes |
|---|---|---|---|---|
| US-A1 | done | 3/3 pass | e2bc766 | Delete button also gated on `user.is_superuser` in the template (beyond literal contract text) so a non-admin never sees a no-op button |
| US-B1 | not started | — | — | |
| US-C1 | done | 4/4 pass | 2bb6672 | Placed next to "Switch to this event" (Delete didn't exist yet in that worktree); merged fine into the same action-row wrapper |
| US-D1 | done | 12/12 pass | 9bd448e | Added a `photo_hidden` consumer handler (not in story's file list) — required for Channels to route the new `"photo.hidden"` group_send to a method, same as existing `photo_uploaded`/`photo_deleted` |
| US-B1 | done | 5/5 pass | edd0179 | Added one line to `dashboard_view`'s context (`guest_identity = _get_user_identity(request)`) — story predicted template-only, but the template had no way to know if this session already holds an identity |
| US-B2 | not started | — | — | unblocked — US-B1 merged |
| US-D2 | not started | — | — | unblocked — US-D1 merged |
| US-E1 | not started | — | — | wave 3 — no dependency, can run independently of B2/D2 |
| US-F1 | not started | — | — | wave 3 — no dependency, can run independently of B2/D2 |

**Wave 1 integration check** (after merging all four branches into `pi-1-admin-tools`, one manual
conflict resolution needed in `dashboard.html`/`urls.py`/`views.py` where A1/C1 both touched the
events-tab action row — additive, not contradictory): full suite `python manage.py test photos`
→ **24/24 pass**, `makemigrations --check --dry-run` → no drift.

**Gotcha for local dev after merging US-D1** (or any future migration-adding story): the `web`
service's `docker-compose.yml` command only runs `migrate` once, at container startup
(`sh -c "python manage.py migrate && python manage.py runserver ..."`). Django's autoreload
picks up new code live but never reruns that outer command, so a new migration merged into a
running dev environment needs a manual `docker compose exec web python manage.py migrate` (or a
container restart) before the affected page works — otherwise it 500s with
`column ... does not exist` even though the code and migration file are both correct.
