# PI-2 dev log

| Story | Status | Tests | Commit | Notes |
|---|---|---|---|---|
| US-A1 | done | 93/93 pass | 66a8ab2 | implemented directly, no subagent dispatch |
| US-B1 | done | 93/93 pass (no new tests — pure static JS/CSS, no Django-testable behavior yet) | (pending commit) | implemented directly; --info-bg/#dbe9fb, --info-ink/#1d5aa8 added to tokens.css |
| US-B2 | done | 107/107 pass (agent) → 115/115 pass (integrated) | 72818c3 | Merge left a real bug: `notify.js` `<script>` included twice in `upload.html` (once by B2, once by B3) — fixed by removing the redundant one, kept the correctly-positioned one before the inline script that calls `window.notify` |

**Feature B integration check**: full suite → **115/115 pass**, no migration drift. All of PI-2
(US-A1, B1, B2, B3) is now merged on `pi-2-upload-dashboard-nav`.
| US-B3 | done | 101/101 pass | 7d41764 | Fast-forward merge, no conflicts (US-B2 not yet landed); dropped in-flight "Envoi…" call per story's design rationale, removed dead `#upload-status`/`showStatus()` |
| C1/C2 | done | 130/130 pass | (pending commit) | Implemented directly, no separate story files (feature description in 00-features.md is the record) — `<details>`→`<div class="hub-section">` across all 4 hub sections, dead `.hub-details` CSS removed, `notify()` call added to IP-verified poll branch |
| D1 | done | 130/130 pass | (pending commit) | Implemented directly. New `SiteSettings.wifi_verified` tri-state field (migration 0031) drives the Wi-Fi status dot; `save_wifi_config`→`verify_wifi_config` (also resets `wifi_verified`, redirects with `?wifi_check=1`); new admin-only `wifi-qr-preview` endpoint (shared `build_wifi_qr_payload` factored into `admin_views.py`, imported by `views.py`'s guest-facing `wifi_qr_code` to avoid duplicating the WIFI: payload logic — required moving the payload builder to admin_views.py rather than views.py, since views.py already imports `superuser_required` from admin_views.py and the reverse direction would be circular); `wifi_verify_ok`/`wifi_verify_broken` POST handlers. Updated 7 pre-existing tests across 4 files that referenced the old `save_wifi_config` field name or asserted the old format-check-drives-the-dot behavior (retired, superseded by the manual-verification dot) — see `test_wifi_credential_format_check.py`'s updated tests and the new `test_admin_dashboard_polish.py`. |
