# US-E3 — Green indicator for Wi-Fi credentials that pass a format/policy check

**As** an admin, **I want** a visual confirmation that the Wi-Fi credentials I entered look
correct, **so that** I'm not guessing whether the SSID/password/security combination will
actually produce a working QR code.

**Feature:** E. **Depends on:** none (independent of US-E2 — this only touches the
credential-entry side on the admin page, not the per-event toggle).

## Contract — what "validated" means here, and why

This is a **format/policy check, not a live network test** (decided explicitly, given a real
join attempt risks disconnecting the server from its own network at a live event — see
`00-features.md`). The green indicator means "these credentials are well-formed for the chosen
security type," not "this Wi-Fi network is confirmed reachable." Label it accordingly in the UI
— don't imply a stronger guarantee than what's actually checked, unlike the IP-address check
(`admin_views.py`'s `_run_ip_check`) which really is a live round-trip and can honestly claim
more.

- **Validation function** (`photos/models.py` or a small helper in `photos/admin_views.py` —
  whichever keeps it next to `SiteSettings`'s existing Wi-Fi fields): given
  `(ssid, password, security)`:
  - `ssid` must be non-blank.
  - If `security == WIFI_SECURITY_NOPASS`: `password` must be blank.
  - If `security == WIFI_SECURITY_WPA`: `password` must be 8-63 characters.
  - If `security == WIFI_SECURITY_WEP`: `password` must be exactly 5 or 13 characters (the two
    common WEP ASCII key lengths — not attempting to also validate 10/26-digit hex keys, that's
    a real gap but out of scope for a policy check, not a live test).
  - Returns a simple valid/invalid boolean (and optionally a reason string for an error message).
- **Where it runs**: computed synchronously in `admin_management_view` (`photos/admin_views.py`)
  every time the page renders, against `SiteSettings.get_solo()`'s current stored values — no
  background thread, no polling, unlike the IP check. Recomputed immediately on `save_wifi_config`
  too, so saving new credentials updates the indicator without a page reload being required
  beyond the existing post-save redirect.
- **Template** (`photos/templates/photos/admin_management.html`): a small green badge/checkmark
  next to the Wi-Fi section's heading when the check passes, styled consistently with the
  existing green "confirmed" state in the `#network-details` IP-verification section (reuse
  whatever badge/icon that uses). No red/error badge for "invalid" — blank credentials are a
  normal not-yet-configured state, not an error; only show something when a security-specific
  rule is actually violated (e.g. a WPA password under 8 characters), as an inline error message
  near the field, same style as other form validation errors on this page.

## Acceptance criteria

- Given a blank SSID, no green indicator shows and no error is shown (neutral "not configured").
- Given a WPA security type with a 12-character password, the green indicator shows.
- Given a WPA security type with a 4-character password, no green indicator shows, and an inline
  message explains the WPA length requirement.
- Given `NOPASS` security with a non-blank password, no green indicator shows, with an inline
  message explaining that open networks can't have a password.
- The indicator's label makes clear this is a format check, not a live connectivity test (e.g.
  "Credentials look valid" rather than "Wi-Fi confirmed working").

## Files touched

`photos/models.py` (or `photos/admin_views.py` — dev's call where the helper lives),
`photos/admin_views.py`, `photos/templates/photos/admin_management.html`.
