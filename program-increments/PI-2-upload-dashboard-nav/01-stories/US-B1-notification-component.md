# US-B1 — Shared notification component (CSS + JS)

**As** a developer of this app, **I want** one reusable notification component, **so that** every
other part of the app (US-B2, US-B3) can show consistent, animated feedback with a single call.

**Feature:** B. **Depends on:** none.

## Contract

This story builds the component only — no template wiring yet (that's US-B2/US-B3).

- **Tokens** (`static/photos/tokens.css`): add `--info-bg` and `--info-ink` (a neutral blue tint,
  no info/neutral color exists yet — pick values consistent with the existing
  `--success-bg`/`--success-ink`, `--warning-bg`/`--warning-ink` pairs' saturation/lightness).
- **CSS** (`static/photos/components.css`, appended near the existing `.alert` rules — don't
  remove `.alert`/`.alert--boxed`/`.alert--success` yet, US-B2 retires their usage):
  ```css
  .notify-container {
    position: fixed;
    top: var(--space-md);
    left: 50%;
    transform: translateX(-50%);
    z-index: 50;
    pointer-events: none;
  }
  .notify {
    min-width: 220px;
    max-width: min(90vw, 420px);
    padding: var(--space-sm) var(--space-md);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    font-size: var(--text-sm);
    font-weight: 700;
    text-align: center;
    opacity: 0;
    transform: translateY(-12px);
    transition: opacity var(--base) var(--ease), transform var(--base) var(--ease);
  }
  .notify.is-visible { opacity: 1; transform: translateY(0); }
  .notify--success { background: var(--success-bg); color: var(--success-ink); }
  .notify--error { background: rgba(227, 74, 83, 0.14); color: var(--danger); }
  .notify--warning { background: var(--warning-bg); color: var(--warning-ink); }
  .notify--info { background: var(--info-bg); color: var(--info-ink); }
  ```
  The `.notify--error` background mirrors how `.badge--danger` already derives its background
  from `--danger` at low opacity (`components.css`) — reuse that exact approach for consistency.
  The transition uses the existing `--base`/`--ease` tokens (200ms, the app's standard transition
  timing) for both the fade and the small `translateY` — this is the "subtle descend + fade in/
  fade out" motion the user asked for, not a hard slide from off-screen.
- **JS** (new file `static/photos/notify.js`):
  - Exposes a single global `window.notify(text, level)` function (`level` one of `"success"`,
    `"error"`, `"warning"`, `"info"`; default `"info"` if omitted/unrecognized).
  - Maintains an internal queue: calling `notify()` while one is already showing enqueues rather
    than showing immediately — mirrors the `overlayQueue`/`showNextOverlay` pattern already in
    `static/photos/tv.js` for the same "don't show two things at once" problem.
  - Lazily creates one `.notify-container` div appended to `<body>` on first use.
  - Each notification: create a `.notify.notify--{level}` div with `textContent = text`, append,
    add `.is-visible` on the next animation frame (so the CSS transition actually plays instead
    of snapping to the visible state), hold for 3000ms, remove `.is-visible`, wait for the CSS
    transition duration (`--base`, 200ms) before removing the element from the DOM and advancing
    to the next queued notification.
  - On `DOMContentLoaded`, scan for `<span class="server-message" hidden data-text="..."
    data-level="...">` nodes, call `window.notify(node.dataset.text, node.dataset.level)` for each
    in document order, then remove the node. This is the hook US-B2 depends on — a template only
    needs to emit these hidden spans, nothing else, to get Django messages through this
    component.

## Acceptance criteria

- Calling `window.notify("Test", "success")` from the browser console on any page that includes
  `notify.js` shows a green rounded rectangle that fades/descends in, holds ~3s, fades/retreats
  out, and is removed from the DOM afterward.
- Calling `notify()` twice in quick succession shows the first fully (enter → hold → exit) before
  the second one starts — never both on screen at once.
- A page with one `<span class="server-message" hidden data-text="Hi" data-level="info">` in it
  automatically shows that notification on load, with no other JS call needed.
- No existing page is visually affected yet — nothing currently includes `notify.js` or emits
  `.server-message` spans.

## Files touched

`static/photos/tokens.css`, `static/photos/components.css`, `static/photos/notify.js` (new).
