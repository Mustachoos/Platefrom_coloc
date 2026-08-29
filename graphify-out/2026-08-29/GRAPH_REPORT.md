# Graph Report - Platefrom_coloc  (2026-08-29)

## Corpus Check
- 63 files · ~33,322 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 441 nodes · 734 edges · 66 communities (21 shown, 45 thin omitted)
- Extraction: 89% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 77 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7c1f09f7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- models.py
- views.py
- drive_service.py
- whiteboard_draw.html page (/whiteboard/)
- admin_views.py
- User types
- Stack technique (Django+Channels+Daphne+PostgreSQL+qrcode)
- PhotosConsumer
- tv.js
- whiteboard_service.py
- FirstRunRedirectMiddleware
- signals.py
- icons.py
- AppRun
- UI Confirmation / Approve Action
- 0001_initial.py
- 0002_slideshowsettings.py
- 0003_useridentity.py
- 0005_like.py
- 0007_eventsettings_likes_enabled.py
- 0008_photo_drive_file_id_and_more.py
- 0009_eventsettings_drive_sharing_enabled_and_more.py
- 0011_alter_event_drive_folder_id_alter_event_is_active.py
- 0013_event_wifi_password_event_wifi_qr_enabled_and_more.py
- 0014_event_tv_bottom_right.py
- start.sh script
- Heart Icon (outline)
- Zoom In Icon
- 0014_sitesettings.py
- .card content wrapper guideline
- no_active_event.html page
- Administrateur (staff actor)
- Dashboard staff (/dashboard/)
- Écran TV (passive display actor)
- Invité (Guest actor)
- Pillow
- 0015_alter_sitesettings_server_host.py
- Adjustments Horizontal Icon
- Alert Triangle Icon
- Arrow Left Icon
- Camera Icon
- Color Picker Icon
- Eraser Icon
- Hand Move Icon
- Maximize Icon (Expand/Fullscreen)
- Palette Icon
- Photo Icon (photo.svg)
- Upload Icon
- 0016_sitesettings_drive_root_folder_id.py
- 0017_merge_20260822_2002.py
- 0018_admininvite.py
- 0019_admininvite_invitee_name_admininvite_revoked_at.py
- 0020_remove_sitesettings_server_host.py
- 0021_sitesettings_server_host.py
- 0022_sitesettings_support_email_and_more.py
- 0023_sitesettings_support_email_verified.py
- 0024_remove_sitesettings_support_email_app_password_and_more.py

## God Nodes (most connected - your core abstractions)
1. `Event` - 29 edges
2. `admin_management_view()` - 21 edges
3. `whiteboard_draw.html page (/whiteboard/)` - 21 edges
4. `DriveError` - 19 edges
5. `Photo` - 18 edges
6. `SiteSettings` - 16 edges
7. `_get_service()` - 15 edges
8. `_get_user_identity()` - 15 edges
9. `dashboard_view()` - 14 edges
10. `AdminInvite` - 12 edges

## Surprising Connections (you probably didn't know these)
- `WhiteboardDrawing (data model)` --semantically_similar_to--> `dashboard.html page (/dashboard/)`  [INFERRED] [semantically similar]
  README.md → photos/templates/photos/dashboard.html
- `dashboard.html page (/dashboard/)` --conceptually_related_to--> `Colors/spacing/typography CSS custom properties`  [AMBIGUOUS]
  photos/templates/photos/dashboard.html → docs/ui-guidelines/README.md
- `Stack technique (Django+Channels+Daphne+PostgreSQL+qrcode)` --conceptually_related_to--> `psycopg2-binary`  [INFERRED]
  README.md → requirements.txt
- `_page_header.html partial` --implements--> `.page-header component guideline`  [INFERRED]
  photos/templates/photos/_page_header.html → docs/ui-guidelines/README.md
- `_footer_nav.html partial` --implements--> `.footer-nav component`  [INFERRED]
  photos/templates/photos/_footer_nav.html → docs/ui-guidelines/README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Guest page shell (header + card + footer-nav) used across guest-facing pages** — photos_templates_photos__page_header_page_header, photos_templates_photos__footer_nav_footer_nav, docs_ui_guidelines_readme_page_shell, photos_templates_photos_upload_upload_page, photos_templates_photos_gallery_gallery_page, photos_templates_photos_my_photos_my_photos_page, photos_templates_photos_whiteboard_draw_whiteboard_page [INFERRED 0.85]
- **Google Drive OAuth2 integration: env vars, config, and Python client libraries** — readme_google_drive_integration, docker_compose_web_service, requirements_google_api_python_client, requirements_google_auth_httplib2, requirements_google_auth_oauthlib [INFERRED 0.90]
- **Pages participating in the /ws/tv/ realtime update flow (uploaded/deleted/settings/liked/whiteboard_updated/tv_layout_changed/event_switched)** — readme_websocket_channel, photos_templates_photos_tv_tv_page, photos_templates_photos_whiteboard_draw_whiteboard_page, photos_templates_photos_dashboard_dashboard_page, photos_templates_photos_upload_upload_page [INFERRED 0.80]

## Communities (66 total, 45 thin omitted)

### Community 0 - "models.py"
Cohesion: 0.09
Nodes (13): EventAdmin, LikeAdmin, PhotoAdmin, SiteSettingsAdmin, SlideshowSettingsAdmin, UserIdentityAdmin, Migration, Migration (+5 more)

### Community 1 - "views.py"
Cohesion: 0.07
Nodes (58): PasswordChangeForm, folder_exists(), Live check (never cached) that folder_id still exists, isn't trashed, and is…, backup_pending_photos(), _clear_local_photos(), drive_photo_count(), ensure_drive_folder(), invalidate_drive_backups() (+50 more)

### Community 2 - "drive_service.py"
Cohesion: 0.07
Nodes (50): BaseCommand, build_oauth_flow(), _client_secret_file(), _configured_root_folder_id(), connect_existing_folder(), connected_email_address(), create_root_folder(), download_file() (+42 more)

### Community 3 - "whiteboard_draw.html page (/whiteboard/)"
Cohesion: 0.06
Nodes (43): Bottom sheet pattern (Whiteboard tools panel reference impl), Button variants guideline (.btn.primary/.secondary/.neutral/.delete), Colors/spacing/typography CSS custom properties, Fixed positioning, not flow (Android viewport-height bug rationale), .footer-nav component, Self-hosted Tabler icons + {% icon %} tag guideline, .page-header component guideline, Page shell pattern (header/card/footer-nav) (+35 more)

### Community 4 - "admin_views.py"
Cohesion: 0.05
Nodes (59): AuthenticationForm, BaseEmailBackend, PasswordResetForm, _admin_creation_open(), admin_management_view(), _client_secret_path(), create_admin_view(), delete_invite_view() (+51 more)

### Community 5 - "User types"
Cohesion: 0.40
Nodes (4): Admin (superuser), Guest, Staff (subadmin), User types

### Community 6 - "Stack technique (Django+Channels+Daphne+PostgreSQL+qrcode)"
Cohesion: 0.14
Nodes (17): db service (postgres:16-alpine), web service (Django/Daphne app container), tv.html page (/tv/), Google Drive integration (OAuth2 personal account, best-effort backup), Upload QR code (/qr/upload.png), Wi-Fi QR code (two separate QR codes, WIFI: format), SlideshowSettings (data model), Stack technique (Django+Channels+Daphne+PostgreSQL+qrcode) (+9 more)

### Community 7 - "PhotosConsumer"
Cohesion: 0.11
Nodes (3): PyInstaller entry point: boots Django against a per-user app-data directory…, PhotosConsumer, WebsocketConsumer

### Community 8 - "tv.js"
Cohesion: 0.31
Nodes (13): advance(), announceNewPhoto(), applyBottomRightWidget(), applyTvLayout(), applyTvSettings(), applyWhiteboardImage(), applyWifiQr(), connectWebSocket() (+5 more)

### Community 9 - "whiteboard_service.py"
Cohesion: 0.39
Nodes (8): add_layer(), _blank_board(), _ensure_size(), Compositing the collective whiteboard. Each guest draws on a transparent canvas…, Composite one freshly uploaded drawing on top of the current board., Recompute the board from every surviving drawing, oldest first., rebuild_board(), _save_board()

### Community 11 - "signals.py"
Cohesion: 0.27
Nodes (7): AppConfig, PhotosConfig, notify_tv_of_interval_change(), notify_tv_of_settings_change(), remove_file_and_notify_tv(), remove_whiteboard_drawing_file(), receiver

### Community 12 - "icons.py"
Cohesion: 0.50
Nodes (4): icon(), _load(), Inline SVG icons (Tabler Icons, MIT-licensed, self-hosted in…, simple_tag

## Ambiguous Edges - Review These
- `Colors/spacing/typography CSS custom properties` → `dashboard.html page (/dashboard/)`  [AMBIGUOUS]
  photos/templates/photos/dashboard.html · relation: conceptually_related_to
- `.photo-card tile (deliberately distinct from .card, past collision bug)` → `dashboard.html page (/dashboard/)`  [AMBIGUOUS]
  photos/templates/photos/dashboard.html · relation: conceptually_related_to

## Knowledge Gaps
- **64 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Migration` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **45 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Colors/spacing/typography CSS custom properties` and `dashboard.html page (/dashboard/)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `.photo-card tile (deliberately distinct from .card, past collision bug)` and `dashboard.html page (/dashboard/)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `SiteSettings` connect `admin_views.py` to `models.py`, `views.py`, `drive_service.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `Event` connect `views.py` to `models.py`, `drive_service.py`, `signals.py`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `Event` (e.g. with `connect_existing_folder()` and `ensure_drive_folder()`) actually correct?**
  _`Event` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `admin_management_view()` (e.g. with `_run_ip_check()` and `DriveClientSecretForm`) actually correct?**
  _`admin_management_view()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `whiteboard_draw.html page (/whiteboard/)` (e.g. with `Fixed positioning, not flow (Android viewport-height bug rationale)` and `Self-hosted Tabler icons + {% icon %} tag guideline`) actually correct?**
  _`whiteboard_draw.html page (/whiteboard/)` has 2 INFERRED edges - model-reasoned connections that need verification._