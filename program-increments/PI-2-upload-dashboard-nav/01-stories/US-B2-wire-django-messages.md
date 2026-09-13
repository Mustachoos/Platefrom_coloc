# US-B2 — Wire Django's `messages` framework into the notification component

**As** any user of the app, **I want** every server-rendered success/error/warning message to
show as the new standardized notification, **so that** feedback looks and behaves consistently
everywhere, and errors finally render as red instead of orange.

**Feature:** B. **Depends on:** US-B1 (needs `notify.js` and the `.notify` CSS/tokens to exist).

## Contract

Replace every current inline `.alert.alert--boxed` message block with a hidden data-carrier that
`notify.js` (US-B1) picks up on `DOMContentLoaded`, and include `notify.js` on each page.

- **The replacement pattern**, used in every file below:
  ```html
  {% for message in messages %}
  <span
    class="server-message" hidden
    data-text="{{ message }}"
    data-level="{% if 'error' in message.tags %}error{% elif 'success' in message.tags %}success{% elif 'warning' in message.tags %}warning{% else %}info{% endif %}"
  ></span>
  {% endfor %}
  ```
  (Django's built-in message levels always appear as one of `debug`/`info`/`success`/`warning`/
  `error` inside `message.tags`, regardless of any `extra_tags` also present — the `elif` chain
  above is safe against `extra_tags` like `"wifi"`/`"network"` sitting alongside the level tag.)
- Add `<script src="{% static 'photos/notify.js' %}"></script>` before `</body>` on each page
  (all of them already `{% load static %}`).
- **Files with a single `{% if messages %}...{% endif %}` block to replace this way:**
  `photos/templates/photos/account.html`, `dashboard.html`, `my_photos.html`,
  `share_drive.html`, `event_switch_confirm.html`, `upload.html`.
- **`photos/templates/photos/admin_management.html` is a special case**: it currently has
  **five** separate `{% for message in messages %}{% if "<tag>" in message.tags %}...{% endif %}
  {% endfor %}` blocks (tags: `staff`, `network`, `wifi`, `drive`, `support-email`), each
  rendering only messages meant for that specific card. Collapse all five into **one single**
  instance of the replacement pattern above, placed once near the top of the page (e.g. right
  after `{% include "photos/_account_button.html" %}`) — not one per card. Iterating Django's
  `messages` context variable more than once per render is fragile; the per-card routing this
  tag-filtering did no longer matters once every message is a global floating notification
  instead of an inline box tied to a specific card.
  - The `extra_tags` passed in `photos/admin_views.py` (`extra_tags="staff"`, `"network"`,
    `"wifi"`, `"drive"`, `"support-email"`) become vestigial once display no longer routes by
    them. Leaving them in `admin_views.py` is harmless (they just become unused metadata) — don't
    spend time stripping them out; that's cleanup, not part of this story's contract.
- **Do not remove** `.alert`/`.alert--boxed`/`.alert--success` from `components.css` — other
  non-message uses may still reference them (check before touching that CSS; if genuinely
  unused after this story, note it in your report rather than deleting speculatively).

## Acceptance criteria

- Given `messages.success(request, "X")` on any of the 7 affected views, the resulting page shows
  "X" as a green notification (fade+descend in, 3s hold, fade+retreat out) instead of a static
  inline box.
- Given `messages.error(request, "Y")`, the notification is red, not orange (the bug this story
  fixes).
- Given two messages queued on one request (e.g. `admin_management_view` after an action that
  sets both a `"staff"`-tagged and a `"network"`-tagged message in the same response — check
  whether this combination is actually reachable in the current code before writing a test for
  it, and use whatever multi-message case genuinely exists instead if not), both notifications
  show, one after the other, never simultaneously.
- No page shows a duplicate or missing notification because of the admin_management.html
  five-blocks-into-one collapse.

## Files touched

The 6 templates listed above, `photos/templates/photos/admin_management.html`.
