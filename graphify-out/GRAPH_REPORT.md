# Graph Report - .  (2026-08-22)

## Corpus Check
- Corpus is ~22,330 words - fits in a single context window. You may not need a graph.

## Summary
- 310 nodes · 434 edges · 57 communities (22 shown, 35 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 55 edges (avg confidence: 0.67)
- Token cost: 0 input · 496,550 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Django Admin & Data Migrations|Django Admin & Data Migrations]]
- [[_COMMUNITY_Core Views & Forms|Core Views & Forms]]
- [[_COMMUNITY_Google Drive Service Layer|Google Drive Service Layer]]
- [[_COMMUNITY_UI Design System & Templates|UI Design System & Templates]]
- [[_COMMUNITY_Multi-Event Drive Orchestration|Multi-Event Drive Orchestration]]
- [[_COMMUNITY_Whiteboard Drawing Frontend (JS)|Whiteboard Drawing Frontend (JS)]]
- [[_COMMUNITY_Deployment Stack & Docker Compose|Deployment Stack & Docker Compose]]
- [[_COMMUNITY_WebSocket Consumers (Realtime)|WebSocket Consumers (Realtime)]]
- [[_COMMUNITY_TV Slideshow Frontend (JS)|TV Slideshow Frontend (JS)]]
- [[_COMMUNITY_Whiteboard Compositing Service|Whiteboard Compositing Service]]
- [[_COMMUNITY_Google Drive Auth CLI Command|Google Drive Auth CLI Command]]
- [[_COMMUNITY_Django App Config|Django App Config]]
- [[_COMMUNITY_Icon Loading Utility|Icon Loading Utility]]
- [[_COMMUNITY_LAN IP Detection Script|LAN IP Detection Script]]
- [[_COMMUNITY_Confirm Action Icon|Confirm Action Icon]]
- [[_COMMUNITY_Initial Migration|Initial Migration]]
- [[_COMMUNITY_Slideshow Settings Migration|Slideshow Settings Migration]]
- [[_COMMUNITY_User Identity Migration|User Identity Migration]]
- [[_COMMUNITY_Like Model Migration|Like Model Migration]]
- [[_COMMUNITY_Likes Toggle Migration|Likes Toggle Migration]]
- [[_COMMUNITY_Photo Drive Fields Migration|Photo Drive Fields Migration]]
- [[_COMMUNITY_Drive Sharing Toggle Migration|Drive Sharing Toggle Migration]]
- [[_COMMUNITY_Event Drive Fields Migration|Event Drive Fields Migration]]
- [[_COMMUNITY_Wi-Fi QR Migration|Wi-Fi QR Migration]]
- [[_COMMUNITY_TV Bottom-Right Migration|TV Bottom-Right Migration]]
- [[_COMMUNITY_Startup Script (start.sh)|Startup Script (start.sh)]]
- [[_COMMUNITY_LikeHeart Icons|Like/Heart Icons]]
- [[_COMMUNITY_Zoom InOut Icons|Zoom In/Out Icons]]
- [[_COMMUNITY_Card Component Guideline|Card Component Guideline]]
- [[_COMMUNITY_No Active Event Page|No Active Event Page]]
- [[_COMMUNITY_Admin Actor (Persona)|Admin Actor (Persona)]]
- [[_COMMUNITY_Staff Dashboard Page|Staff Dashboard Page]]
- [[_COMMUNITY_TV Screen Actor (Persona)|TV Screen Actor (Persona)]]
- [[_COMMUNITY_Guest Actor (Persona)|Guest Actor (Persona)]]
- [[_COMMUNITY_Pillow Dependency|Pillow Dependency]]
- [[_COMMUNITY_Adjustments Icon|Adjustments Icon]]
- [[_COMMUNITY_Alert Triangle Icon|Alert Triangle Icon]]
- [[_COMMUNITY_Back Arrow Icon|Back Arrow Icon]]
- [[_COMMUNITY_Camera Icon|Camera Icon]]
- [[_COMMUNITY_Color Picker Icon|Color Picker Icon]]
- [[_COMMUNITY_Eraser Icon|Eraser Icon]]
- [[_COMMUNITY_PanMove Icon|Pan/Move Icon]]
- [[_COMMUNITY_Fullscreen Icon|Fullscreen Icon]]
- [[_COMMUNITY_Palette Icon|Palette Icon]]
- [[_COMMUNITY_Photo Icon|Photo Icon]]
- [[_COMMUNITY_Upload Icon|Upload Icon]]

## God Nodes (most connected - your core abstractions)
1. `whiteboard_draw.html page (/whiteboard/)` - 21 edges
2. `Photo` - 17 edges
3. `Event` - 16 edges
4. `DriveError` - 15 edges
5. `_get_service()` - 12 edges
6. `_get_user_identity()` - 12 edges
7. `PhotosConsumer` - 11 edges
8. `SlideshowSettings` - 11 edges
9. `gallery.html page (/gallery/)` - 10 edges
10. `UserIdentity` - 9 edges

## Surprising Connections (you probably didn't know these)
- `WhiteboardDrawing (data model)` --semantically_similar_to--> `dashboard.html page (/dashboard/)`  [INFERRED] [semantically similar]
  README.md → photos/templates/photos/dashboard.html
- `dashboard.html page (/dashboard/)` --conceptually_related_to--> `Colors/spacing/typography CSS custom properties`  [AMBIGUOUS]
  photos/templates/photos/dashboard.html → docs/ui-guidelines/README.md
- `whiteboard_draw.html page (/whiteboard/)` --implements--> `Self-hosted Tabler icons + {% icon %} tag guideline`  [INFERRED]
  photos/templates/photos/whiteboard_draw.html → docs/ui-guidelines/README.md
- `WhiteboardDrawing (data model)` --references--> `whiteboard_draw.html page (/whiteboard/)`  [EXTRACTED]
  README.md → photos/templates/photos/whiteboard_draw.html
- `Collective whiteboard feature` --references--> `whiteboard_draw.html page (/whiteboard/)`  [EXTRACTED]
  README.md → photos/templates/photos/whiteboard_draw.html

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Guest page shell (header + card + footer-nav) used across guest-facing pages** — photos_templates_photos__page_header_page_header, photos_templates_photos__footer_nav_footer_nav, docs_ui_guidelines_readme_page_shell, photos_templates_photos_upload_upload_page, photos_templates_photos_gallery_gallery_page, photos_templates_photos_my_photos_my_photos_page, photos_templates_photos_whiteboard_draw_whiteboard_page [INFERRED 0.85]
- **Google Drive OAuth2 integration: env vars, config, and Python client libraries** — readme_google_drive_integration, docker_compose_web_service, requirements_google_api_python_client, requirements_google_auth_httplib2, requirements_google_auth_oauthlib [INFERRED 0.90]
- **Pages participating in the /ws/tv/ realtime update flow (uploaded/deleted/settings/liked/whiteboard_updated/tv_layout_changed/event_switched)** — readme_websocket_channel, photos_templates_photos_tv_tv_page, photos_templates_photos_whiteboard_draw_whiteboard_page, photos_templates_photos_dashboard_dashboard_page, photos_templates_photos_upload_upload_page [INFERRED 0.80]

## Communities (57 total, 35 thin omitted)

### Community 0 - "Django Admin & Data Migrations"
Cohesion: 0.09
Nodes (16): EventAdmin, LikeAdmin, PhotoAdmin, SlideshowSettingsAdmin, UserIdentityAdmin, Migration, Migration, Migration (+8 more)

### Community 1 - "Core Views & Forms"
Cohesion: 0.13
Nodes (26): PseudoForm, ShareDriveForm, One guest's contribution to the collective whiteboard: a transparent     PNG lay, WhiteboardDrawing, choose_pseudo(), dashboard_delete_photo(), dashboard_delete_whiteboard_drawing(), _dashboard_redirect() (+18 more)

### Community 2 - "Google Drive Service Layer"
Cohesion: 0.12
Nodes (29): Exception, connect_existing_folder(), download_file(), DriveError, extract_folder_id(), folder_exists(), _get_credentials(), get_or_create_event_folder() (+21 more)

### Community 3 - "UI Design System & Templates"
Cohesion: 0.09
Nodes (28): Button variants guideline (.btn.primary/.secondary/.neutral/.delete), Colors/spacing/typography CSS custom properties, .footer-nav component, Self-hosted Tabler icons + {% icon %} tag guideline, .page-header component guideline, Page shell pattern (header/card/footer-nav), .photo-card tile (deliberately distinct from .card, past collision bug), .segmented two-way toggle component (+20 more)

### Community 4 - "Multi-Event Drive Orchestration"
Cohesion: 0.11
Nodes (21): backup_pending_photos(), _clear_local_photos(), drive_photo_count(), ensure_drive_folder(), _guess_username(), invalidate_drive_backups(), Multi-event orchestration: connecting an event to its Drive folder, backing up l, Upload every local photo of `event` that isn't on Drive yet.     Returns (upload (+13 more)

### Community 5 - "Whiteboard Drawing Frontend (JS)"
Cohesion: 0.12
Nodes (15): Bottom sheet pattern (Whiteboard tools panel reference impl), Fixed positioning, not flow (Android viewport-height bug rationale), applyTransform(), clampPan(), computeFitZoom(), connectWebSocket(), endPointer(), handleResize() (+7 more)

### Community 6 - "Deployment Stack & Docker Compose"
Cohesion: 0.14
Nodes (17): db service (postgres:16-alpine), web service (Django/Daphne app container), tv.html page (/tv/), Google Drive integration (OAuth2 personal account, best-effort backup), Upload QR code (/qr/upload.png), Wi-Fi QR code (two separate QR codes, WIFI: format), SlideshowSettings (data model), Stack technique (Django+Channels+Daphne+PostgreSQL+qrcode) (+9 more)

### Community 8 - "TV Slideshow Frontend (JS)"
Cohesion: 0.24
Nodes (12): advance(), announceNewPhoto(), applyBottomRightWidget(), applyTvLayout(), applyTvSettings(), applyWhiteboardImage(), applyWifiQr(), displayPhoto() (+4 more)

### Community 9 - "Whiteboard Compositing Service"
Cohesion: 0.39
Nodes (8): add_layer(), _blank_board(), _ensure_size(), Compositing the collective whiteboard.  Each guest draws on a transparent canvas, Composite one freshly uploaded drawing on top of the current board., Recompute the board from every surviving drawing, oldest first., rebuild_board(), _save_board()

### Community 10 - "Google Drive Auth CLI Command"
Cohesion: 0.40
Nodes (3): BaseCommand, Command, One-time interactive Google Drive authorization.  Run this locally (not inside t

### Community 12 - "Icon Loading Utility"
Cohesion: 0.67
Nodes (3): icon(), _load(), Inline SVG icons (Tabler Icons, MIT-licensed, self-hosted in static/photos/icons

## Ambiguous Edges - Review These
- `Colors/spacing/typography CSS custom properties` → `dashboard.html page (/dashboard/)`  [AMBIGUOUS]
  photos/templates/photos/dashboard.html · relation: conceptually_related_to
- `.photo-card tile (deliberately distinct from .card, past collision bug)` → `dashboard.html page (/dashboard/)`  [AMBIGUOUS]
  photos/templates/photos/dashboard.html · relation: conceptually_related_to

## Knowledge Gaps
- **52 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Migration` (+47 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Colors/spacing/typography CSS custom properties` and `dashboard.html page (/dashboard/)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `.photo-card tile (deliberately distinct from .card, past collision bug)` and `dashboard.html page (/dashboard/)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `whiteboard_draw.html page (/whiteboard/)` connect `Whiteboard Drawing Frontend (JS)` to `UI Design System & Templates`, `Deployment Stack & Docker Compose`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `Event` connect `Django Admin & Data Migrations` to `Core Views & Forms`, `Google Drive Service Layer`, `Multi-Event Drive Orchestration`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `whiteboard_draw.html page (/whiteboard/)` (e.g. with `Fixed positioning, not flow (Android viewport-height bug rationale)` and `Self-hosted Tabler icons + {% icon %} tag guideline`) actually correct?**
  _`whiteboard_draw.html page (/whiteboard/)` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `Photo` (e.g. with `EventAdmin` and `LikeAdmin`) actually correct?**
  _`Photo` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `Event` (e.g. with `EventAdmin` and `LikeAdmin`) actually correct?**
  _`Event` has 7 INFERRED edges - model-reasoned connections that need verification._