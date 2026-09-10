# PI-1 dev log

Status per story, filled in as wave 1 / wave 2 close. Per `program-increments/README.md`'s
Definition of Done: a story is only marked done once its own test(s) pass **and** the full
existing test suite for the PI still passes (regression), not just the new test.

| Story | Status | Tests | Commit | Notes |
|---|---|---|---|---|
| US-A1 | done | 3/3 pass | e2bc766 | Delete button also gated on `user.is_superuser` in the template (beyond literal contract text) so a non-admin never sees a no-op button |
| US-B1 | not started | — | — | |
| US-C1 | done | 4/4 pass | 2bb6672 | Placed next to "Switch to this event" (Delete didn't exist yet in that worktree); merged fine into the same action-row wrapper |
| US-D1 | not started | — | — | |
| US-B2 | not started | — | — | waits on US-B1 |
| US-D2 | not started | — | — | waits on US-D1 |
