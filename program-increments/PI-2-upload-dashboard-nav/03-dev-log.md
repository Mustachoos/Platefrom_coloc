# PI-2 dev log

| Story | Status | Tests | Commit | Notes |
|---|---|---|---|---|
| US-A1 | done | 93/93 pass | 66a8ab2 | implemented directly, no subagent dispatch |
| US-B1 | done | 93/93 pass (no new tests — pure static JS/CSS, no Django-testable behavior yet) | (pending commit) | implemented directly; --info-bg/#dbe9fb, --info-ink/#1d5aa8 added to tokens.css |
| US-B2 | not started | — | — | wave 3 — depends on US-B1 |
| US-B3 | done | 101/101 pass | 7d41764 | Fast-forward merge, no conflicts (US-B2 not yet landed); dropped in-flight "Envoi…" call per story's design rationale, removed dead `#upload-status`/`showStatus()` |
