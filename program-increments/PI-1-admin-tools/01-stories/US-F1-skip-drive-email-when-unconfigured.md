# US-F1 — Skip the Drive-share email step when Drive isn't configured

**As** a guest, **I want** to skip straight to uploading when the event has no Drive folder,
**so that** I'm not asked for an email address that has nothing to connect to.

**Feature:** F. **Depends on:** none.

## Contract

- `choose_pseudo` (`photos/views.py`): after creating the `UserIdentity`
  (`request.session["pseudo"] = pseudo`), currently always `return redirect("share-drive")`.
  Change to check `active_event.drive_folder_id` first: if blank, `return redirect("upload")`
  instead; if set, keep the existing `redirect("share-drive")`.
- `share_drive_view` (`photos/views.py`): add the same guard at the top, right after resolving
  `user`/`active_event` — if `active_event.drive_folder_id` is blank, `return redirect("upload")`
  immediately, before rendering the form. This covers a guest who reaches the URL directly
  (bookmark, back button, stale link) after the event's Drive folder was disconnected mid-session.
- No change to either view when `drive_folder_id` **is** set — the email form and "Skip" button
  behave exactly as today.

## Acceptance criteria

- Given an event with no Drive folder connected, when a guest picks a pseudo, they land directly
  on `/upload/`, never seeing `/pseudo/share-drive/`.
- Given an event with no Drive folder connected, when a guest navigates to
  `/pseudo/share-drive/` directly, they're redirected to `/upload/`.
- Given an event **with** a Drive folder connected, both flows are unchanged from today — the
  email form still appears, "Skip" still works.

## Files touched

`photos/views.py`.
