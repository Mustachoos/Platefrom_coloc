# PI-2 dev log

| Story | Status | Tests | Commit | Notes |
|---|---|---|---|---|
| US-A1 | done | 93/93 pass | 66a8ab2 | implemented directly, no subagent dispatch |
| US-B1 | done | 93/93 pass (no new tests — pure static JS/CSS, no Django-testable behavior yet) | (pending commit) | implemented directly; --info-bg/#dbe9fb, --info-ink/#1d5aa8 added to tokens.css |
| US-B2 | done | 107/107 pass (agent) → 115/115 pass (integrated) | 72818c3 | Merge left a real bug: `notify.js` `<script>` included twice in `upload.html` (once by B2, once by B3) — fixed by removing the redundant one, kept the correctly-positioned one before the inline script that calls `window.notify` |

**Feature B integration check**: full suite → **115/115 pass**, no migration drift. All of PI-2
(US-A1, B1, B2, B3) is now merged on `pi-2-upload-dashboard-nav`.
| US-B3 | done | 101/101 pass | 7d41764 | Fast-forward merge, no conflicts (US-B2 not yet landed); dropped in-flight "Envoi…" call per story's design rationale, removed dead `#upload-status`/`showStatus()` |
