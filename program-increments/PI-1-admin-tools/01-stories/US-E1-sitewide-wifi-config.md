# US-E1 — Wi-Fi config becomes a site-wide, admin-only setting

**As** an admin, **I want** Wi-Fi network details set once for the whole install instead of
re-entered per event, **so that** I don't repeat the same venue's Wi-Fi info every time I create
a new event.

**Feature:** E. **Depends on:** none.

## Contract

- **Model**: add `wifi_ssid` (`CharField`, blank), `wifi_password` (`CharField`, blank),
  `wifi_security` (`CharField`, same `choices=Event.WIFI_SECURITY_CHOICES` shape — move the
  choices constants too, e.g. onto `SiteSettings` or a shared module, whichever keeps
  `WIFI_SECURITY_CHOICES` importable from one place), `wifi_qr_enabled` (`BooleanField`, default
  `False`) to `SiteSettings` in `photos/models.py`.
- **Data migration**: before dropping the four `wifi_*` fields from `Event`, write a migration
  (`RunPython`) that copies the currently-active event's values into the `SiteSettings` singleton
  (`SiteSettings.get_solo()` — `pk=1`) if that event has a non-blank `wifi_ssid`; if no event is
  active or none has Wi-Fi configured, leave `SiteSettings`'s new fields at their defaults. Then a
  second migration drops the four fields from `Event`. Two separate migrations, in that order —
  don't collapse the data copy and the schema drop into one, so the copy runs against the
  still-intact `Event` columns.
- **Write handlers**: move `save_wifi_config` and `toggle_wifi_qr` (currently inline in
  `dashboard_view`'s POST branch, `photos/views.py` around lines 584-604) into
  `admin_management_view` (`photos/admin_views.py`), operating on `site_settings =
  SiteSettings.get_solo()` instead of `active_event`. `admin_management_view` is already
  `@superuser_required` — no new decorator needed, this makes Wi-Fi editing admin-only for free.
- **Read sites** — update all three to read from `SiteSettings.get_solo()` instead of
  `Event.get_active()`'s wifi fields: `tv_view`, `slideshow_settings_api`, `wifi_qr_code` (all in
  `photos/views.py`). These no longer depend on which event is active at all.
- **Templates**: remove the Wi-Fi block (SSID/password/security form, QR toggle, QR preview —
  `dashboard.html` lines ~182-214) from the dashboard's TV-layout tab. Add the equivalent block to
  `admin_management.html`, next to the existing `#network-details` LAN-address section (both are
  physical-network configuration, natural neighbors).

## Acceptance criteria

- Given an admin sets Wi-Fi details on `/admin-account/`, when any event is active (or switched),
  the TV screen's Wi-Fi QR code reflects those details — not tied to which event is active.
- Given a staff (non-superuser) user, there is no Wi-Fi editing UI reachable from `/dashboard/`
  anymore, and posting the old `save_wifi_config`/`toggle_wifi_qr` fields to `admin-management`
  directly is rejected by the existing `@superuser_required` decorator.
- Given an event had Wi-Fi configured before this migration ran, its values survive into
  `SiteSettings` after migrating (verify via the data migration, not just the schema one).
- `Event` no longer has `wifi_ssid`/`wifi_password`/`wifi_security`/`wifi_qr_enabled` fields.

## Files touched

`photos/models.py`, `photos/migrations/` (two new migrations), `photos/views.py`,
`photos/admin_views.py`, `photos/templates/photos/dashboard.html`,
`photos/templates/photos/admin_management.html`.
