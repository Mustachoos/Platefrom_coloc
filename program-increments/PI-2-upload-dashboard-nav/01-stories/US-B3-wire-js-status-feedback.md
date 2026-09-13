# US-B3 — Wire upload/whiteboard JS status feedback into the notification component

**As** a guest, **I want** the upload and whiteboard pages' feedback (success, cooldown, errors)
to look and animate the same as everywhere else, **so that** the app feels consistent.

**Feature:** B. **Depends on:** US-B1 (needs `notify.js`/`.notify` CSS to exist). Independent of
US-B2 (different call sites — JS-triggered, not Django `messages` — though both touch
`upload.html`, so expect a merge conflict there if run in parallel with US-B2; resolve
additively).

## Contract — a real design split, not a 1:1 swap

`notify.js` (US-B1) is a fixed-duration (3s), queued, discrete-message component — it has no
concept of an indeterminate "in progress" state. Both pages currently conflate two different
things in one pill: a **persistent state indicator** and a **transient result message**. This
story separates them; only the transient one moves to `notify()`.

### `photos/templates/photos/upload.html`

- `#photo-status` **stays**, but becomes purely a persistent selection-state indicator:
  "Pas encore de photo :(" / the chosen filename / "Jolie photo !" (camera). Remove:
  - The `data-just-uploaded` attribute and server-rendered "Envoi réussi" initial content — the
    div's initial/default content is now always the empty state.
  - The `justUploaded`-branch in the `DOMContentLoaded` handler and its `setTimeout` that used to
    revert the box back to empty after 3s — no longer needed, since the box no longer displays
    the transient success message at all.
  - `update()` now always runs unconditionally on `DOMContentLoaded` (it already correctly shows
    "Pas encore de photo :(" for an empty file input, which is always the case right after the
    redirect-and-reload following a successful upload).
- Add: if `just_uploaded` is true (still passed from `upload_view`, `photos/views.py` — no view
  change needed, only how the template uses it), call `window.notify("Envoi réussi", "success")`
  once on load.
- Include `<script src="{% static 'photos/notify.js' %}"></script>` before the page's own
  `<script>` block (so `window.notify` exists when the inline script runs).

### `photos/templates/photos/whiteboard_draw.html`

- Replace the **terminal** `showStatus(...)` calls with `window.notify(text, level)`:
  - `showStatus('Ajouté au tableau !', 2500)` → `notify('Ajouté au tableau !', 'success')`
  - `showStatus('Attends un peu avant de renvoyer.', 2500)` → `notify('Attends un peu avant de
    renvoyer.', 'warning')`
  - `showStatus(data.error || 'Impossible d\'envoyer le dessin.', 3000)` →
    `notify(data.error || 'Impossible d\'envoyer le dessin.', 'error')`
  - `showStatus('Erreur réseau, réessaie.', 3000)` → `notify('Erreur réseau, réessaie.', 'error')`
- **Deliberately out of scope**: the in-flight `showStatus('Envoi…')` call (shown the instant the
  upload starts, with no auto-hide). `notify()` has no indeterminate/loading state and forcing
  "Envoi…" through its fixed 3s queue would delay the real result notification behind it. Drop
  this call — `uploadBtn.disabled = true` (already set when upload starts) is the in-flight
  indicator now. If that reads as insufficient feedback once this ships, it's a follow-up story,
  not a reason to bend `notify()`'s contract here.
- Remove the now-unused `#upload-status` element, `showStatus()` function, and its CSS
  (`#upload-status` rules in this template's own `<style>` block) once nothing calls it anymore.
- Include `<script src="{% static 'photos/notify.js' %}"></script>` before this page's own
  `<script>` block.

## Acceptance criteria

- Uploading a photo successfully shows a green "Envoi réussi" notification that fades in, holds
  ~3s, fades out; the persistent status box immediately reflects "no file selected" underneath
  it, not a stale "Envoi réussi" that later reverts.
- Selecting a file (camera or gallery) still updates the persistent status box exactly as before
  — this story doesn't touch that behavior, only the post-submit success feedback.
- Submitting a whiteboard drawing successfully shows a green "Ajouté au tableau !" notification;
  hitting the cooldown shows an orange warning notification; a server/network error shows a red
  error notification — each using the shared component's animation, not the old pill.
- No `#upload-status` element or dead CSS remains in `whiteboard_draw.html` once this lands.

## Files touched

`photos/templates/photos/upload.html`, `photos/templates/photos/whiteboard_draw.html`.
