# US-E2 — Move the "show Wi-Fi QR on TV" toggle back to per-event

**As** staff, **I want** to choose whether *this event's* TV shows the Wi-Fi QR code, **so that**
the credentials being site-wide (US-E1) doesn't force every event to display it.

**Feature:** E. **Depends on:** US-E1 (splits what E1 centralized: credentials stay on
`SiteSettings`, the on/off toggle moves back to `Event`).

## Contract

Post-E1, `wifi_qr_enabled` lives on `SiteSettings` alongside `wifi_ssid`/`wifi_password`/
`wifi_security`. This story splits it back out: **credentials stay site-wide**, but **whether to
show the QR code is per-event again**.

- **Model**: add `wifi_qr_enabled` (`BooleanField`, default `False`) back onto `Event`
  (`photos/models.py`). Remove it from `SiteSettings` — credentials (`wifi_ssid`/
  `wifi_password`/`wifi_security`) stay put there, only the enabled flag moves.
- **Migrations**: one migration adding `Event.wifi_qr_enabled`, with a data step copying
  `SiteSettings.get_solo().wifi_qr_enabled`'s current value onto the active event (if one exists)
  before a second migration drops `wifi_qr_enabled` from `SiteSettings` — same two-migration
  data-then-schema shape US-E1 itself used, just in reverse.
- **Read sites** (`photos/views.py`): `tv_view`, `slideshow_settings_api`, `wifi_qr_code` — change
  the `wifi_qr_shown`/availability check from `site_settings.wifi_qr_enabled and
  site_settings.wifi_ssid` to `active_event.wifi_qr_enabled and site_settings.wifi_ssid` (still
  need `Event.get_active()`, credentials still come from `SiteSettings.get_solo()`).
- **Write handler**: move `toggle_wifi_qr` (currently in `admin_management_view`,
  `photos/admin_views.py:275-283`) back into `dashboard_view` (`photos/views.py`), operating on
  `active_event.wifi_qr_enabled`. Guard: reject the toggle (error message, no state change) if
  `SiteSettings.get_solo().wifi_ssid` is blank — matches the "no toggling in an unavailable
  state" rule the whiteboard/leaderboard toggles already use elsewhere in this same view.
- **Template**: add the toggle button back to `dashboard.html`'s TV-layout tab (it was removed by
  US-E1), in the same "Top right — QR codes" card it used to live in. Grey it out
  (`{% if not wifi_configured %}disabled{% endif %}`, same pattern as the existing whiteboard/
  leaderboard buttons at lines ~159-165/221-228) and show a tooltip/helper text reading "Requires
  admin to set up Wi-Fi credentials" when `SiteSettings.get_solo().wifi_ssid` is blank —
  `dashboard_view` needs to pass a `wifi_configured` boolean (or the `site_settings` object
  itself) into its render context for the template to check. Remove the enabled/disabled toggle
  button from `admin_management.html` (US-E1 added it there) — the admin page keeps only the
  credential-entry form (SSID/password/security) plus US-E3's validity indicator, not the on/off
  switch.

## Acceptance criteria

- Given `SiteSettings` has no Wi-Fi SSID set, the dashboard's Wi-Fi QR toggle is disabled and
  shows "Requires admin to set up Wi-Fi credentials"; POSTing the toggle directly is rejected.
- Given `SiteSettings` has an SSID set, staff can toggle `active_event.wifi_qr_enabled` on/off
  per event from the dashboard; switching the active event preserves each event's own choice.
- Given one event has the QR enabled and another doesn't, switching the active event changes
  whether the TV shows the Wi-Fi QR code, without touching the underlying credentials.
- `SiteSettings` no longer has a `wifi_qr_enabled` field; `admin_management.html` no longer has
  an enable/disable toggle for it.

## Files touched

`photos/models.py`, two new migrations, `photos/views.py`, `photos/admin_views.py`,
`photos/templates/photos/dashboard.html`, `photos/templates/photos/admin_management.html`.
