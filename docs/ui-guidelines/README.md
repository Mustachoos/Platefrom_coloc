# UI guidelines — guest-facing pages

Design system for the pages guests reach from the footer nav (Upload,
Gallery/My photos, Whiteboard) and any future page in that same family.
Extracted from the Upload page, which was the reference implementation for
this pass. **Not** for the admin dashboard or the TV screen — those are
separate contexts with their own constraints and already have their own
local styles.

All shared rules live in `static/photos/site.css`. Page-specific CSS should
be the exception, not the norm — if you're writing more than a few
one-off rules in a page's local `<style>` block, check whether it belongs
in `site.css` as a named, reusable class instead.

## Page shell

Every guest page follows the same three-part shell:

```
┌─────────────────────────────┐
│ .page-header (fixed, 56px)  │  icon + title only
├─────────────────────────────┤
│                              │
│   .card (content, ≤620px,   │  page content goes here
│   centered)                  │
│                              │
├─────────────────────────────┤
│ .footer-nav (fixed, 56px)   │  Upload / Photos / Whiteboard
└─────────────────────────────┘
```

Minimal template for a new page:

```django
{% load static %}
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Page title</title>
  <link rel="stylesheet" href="{% static 'photos/site.css' %}">
</head>
<body class="has-footer-nav has-page-header">
  {% include "photos/_page_header.html" with page_icon="icon-name" page_title="Page title" %}
  <main class="card">
    <!-- page content -->
  </main>
  {% include "photos/_footer_nav.html" %}
</body>
</html>
```

### `.page-header`

- Partial: `photos/templates/photos/_page_header.html`. Takes two params:
  `page_icon` (a name from `static/photos/icons/`) and `page_title` (plain
  text, shown as the page's `<h1>`).
- Icon + title **only** — no subtitle, no back button. It answers "what
  page am I on", nothing else. Root guest pages (Upload/Gallery/Whiteboard)
  are peers reachable from the footer, so there's never a "back" to show;
  if a future page is a genuine sub-page (e.g. a single-photo detail view),
  don't stretch the header for it — carve out a different pattern rather
  than growing this partial's responsibility.
- `position:fixed`, not flow-positioned — see [Fixed positioning](#fixed-positioning-not-flow).
  Height is hardcoded to `56px` in `site.css` (`.page-header`), the single
  source of truth. Anything that needs to know the header's height for its
  own layout math (see Whiteboard) reads `56px` from a comment pointing
  back here — don't let a second copy of that number drift.
- `body.has-page-header` reserves `56px + 20px` of top padding: the header
  itself plus a deliberate breathing gap before content starts. That gap is
  a real padding value, not an accident of a centered layout — a
  vertically-centered page (`.centered-page`, e.g. Upload) will *look*
  like it has a gap below the header even with zero padding, purely from
  flexbox centering, but that gap shrinks or vanishes on a shorter viewport
  or a taller card. A top-aligned page (Gallery, My photos) has no such
  accidental gap at all, which is exactly the "card touching the header"
  bug this padding fixes. Don't remove it on the assumption that centering
  already handles it.
- Contextual info that isn't the page identity (e.g. "Uploading as
  {pseudo}") does **not** go in the header. Put it at the top of the
  content card instead (see Upload, Whiteboard's tools sheet).

### `.card` (content wrapper)

- `width:min(100%,620px)`, centered, light frosted surface
  (`var(--card)`), soft shadow, `24px` radius. On phones (<620px, i.e. the
  overwhelming majority of real usage — this is a house-party app used on
  phones) it's already full-width; the cap only kicks in on tablets/desktop.
- This width is intentionally the **same on every page**, including
  content-heavy ones like the photo grid. That was a deliberate trade-off
  (fewer grid columns on wide screens) in favor of one consistent content
  width everywhere, not a technical default — don't "fix" the gallery back
  to full-bleed without re-checking that decision.
- Don't reuse the bare `.card` class for anything that isn't this
  page-level wrapper. See `.photo-card` below for why that collision is a
  trap.

### `.footer-nav`

Already covered by `_footer_nav.html` (existing). Unchanged by this pass —
included for completeness since it's the third leg of the shell.

## Fixed positioning, not flow

`.page-header` and `.footer-nav` are both `position:fixed`, anchored with
explicit pixel heights — not `height:100%` + flexbox flow. This is
deliberate: Android Chrome can compute `100%`/`100vh` taller than what's
actually visible once the on-screen nav bar is factored in, which pushes
flow-positioned bottom/top bars out past the real edge, under the system
UI. `position:fixed` elements anchor to the true visible viewport instead
and don't have that problem. This was a real, user-reported bug on the
whiteboard page before the fix — don't reintroduce flow positioning for
page chrome to "simplify" a layout.

Pages using this shell also need `padding-top`/`padding-bottom` reserved
for the fixed bars, via the `has-page-header` / `has-footer-nav` body
classes (both defined in `site.css`) — a page that's fully custom-positioned
itself (like Whiteboard) doesn't need these classes, since it computes its
own offsets from the same `56px` constants directly.

## Colors, spacing, typography

All defined as CSS custom properties on `:root` in `site.css` — never
hardcode a hex value that already has a token:

| Token | Use |
|---|---|
| `--ink` | primary text |
| `--soft` | secondary/muted text |
| `--card` / `--card-border` | frosted surface + its border, for any panel/sheet/header |
| `--btn-1` / `--btn-2` | primary action gradient (green) |
| `--danger-1` / `--danger-2` | destructive action gradient (red, `.btn.delete`) |
| `--accent` | informational accent (blue) |
| `--bg-1` / `--bg-2` | page background gradient |

Shadows on light surfaces (header, footer, cards, sheets) use a soft,
colored shadow derived from the surface's own tint (e.g.
`rgba(31,52,72,0.16–0.22)`), not a flat black one — a plain
`rgba(0,0,0,0.4)` shadow reads as a different, heavier design language.
The one deliberate exception is UI floating directly over the whiteboard's
dark canvas (zoom controls), where a darker shadow is needed for contrast
against black/photo content — that's a contextual necessity, not a
inconsistency to fix.

Font is set once on `html,body` (`"Trebuchet MS","Segoe UI",sans-serif`).
Don't set `font-family` again on a per-page basis.

## Buttons

Base rules apply to every `button` and `.btn` automatically: rounded
(`13px`), bold, `inline-flex` with centered icon+text and an `8px` gap —
an icon and a text label just work side by side with no extra markup.

Variants (add as a second class):
- `.btn.primary` / `button.primary` — main call to action, green gradient.
- `.btn.secondary` — outlined, transparent background.
- `.btn.neutral` — light gray, for a non-primary but not-outlined action.
- `.btn.delete` — destructive, red gradient. Use `.small` alongside it for
  inline per-item delete actions (photo/drawing rows) — `.btn.delete.small`.
- `.btn.small` / `.btn.large` — size modifiers, combine with any variant.

A button with multiple children meant to **stack vertically** (e.g. a
title + description inside a selectable card) needs an explicit
`flex-direction:column` override — the base rule above makes every button
`inline-flex` by default, which otherwise forces those children into a row.
This bit a dashboard card once; check for it whenever you put a `<button>`
around more than an icon+label pair.

## Icons

- Self-hosted Tabler icons (MIT), in `static/photos/icons/*.svg`. No CDN,
  no icon font, no emoji in the UI — the whole point is that these render
  identically regardless of the guest's browser/OS emoji set.
- Render via the `{% icon 'name' size=20 %}` template tag
  (`photos/templatetags/icons.py`). `{% load icons %}` at the top of any
  template that calls it directly; templates that only `{% include %}` a
  partial which itself loads `icons` don't need to load it again — Django
  resolves tag libraries per-template at render time.
- In plain JS (no template tags available, e.g. `tv.js`), inline the exact
  SVG markup as a string constant instead of reinventing the icon.
- **Keep text where it's genuinely doing work**, don't blindly convert
  everything to icon-only: destructive actions (Delete) stay labeled
  because a mis-tap is costly and unambiguous text prevents it; the
  Simple/Artiste mode switch stays labeled because it names a mode, not a
  direction, and an icon can't carry that meaning unambiguously. When in
  doubt, ask "would a first-time guest, at a party, slightly distracted,
  know what this icon does with zero label?" — if not, keep the word.

## Reusable components

- **`.segmented`** — two-way toggle between sibling views that share one
  footer-nav destination (All photos / My photos). Pill-shaped, active
  item gets a white background + soft shadow.
- **`.photo-card`** — the compact per-photo tile used in grids
  (`.grid`). Deliberately a **different class from `.card`** — the page
  wrapper and the grid tile need very different visual treatment (heavy
  padding/shadow/blur vs. a small flat tile), and giving them the same
  class name was an actual bug in this codebase before this pass (a photo
  tile briefly inherited the big page-card's padding and shadow). If you
  add a new kind of card-like tile, give it its own class rather than
  reaching for `.card`.
- **Bottom sheet** (Whiteboard's tools panel is the reference
  implementation) — for a tool/options surface that must be reachable
  one-handed and fully hide when closed: `position:fixed`, full width,
  `border-radius: 20px 20px 0 0`, anchored above the footer-nav.
  Closed state is `transform:translateY(100%); pointer-events:none` —
  fully off-screen and non-interactive, not just invisible via `opacity`
  (a `opacity:0` sheet with `pointer-events:auto` left behind is still
  clickable, which was a real bug class earlier in this project). Prefer
  this pattern over a small corner-anchored popover for anything with more
  than one or two controls — bigger touch targets, more standard mobile
  ergonomics.

## Adding a new guest page

1. Copy the [minimal template](#page-shell) above.
2. Pick (or add) an icon in `static/photos/icons/` for the header.
3. Wrap content in `.card`; reuse `.photo-card`/`.segmented`/`.btn.*` etc.
   before inventing new component CSS.
4. Add the page to `_footer_nav.html` only if it's a top-level destination
   guests navigate to directly — not every page needs a footer entry.
5. Verify on a real narrow viewport (or headless Chrome at ~390px width)
   that the fixed header/footer don't overlap content, and on Android
   specifically if you touch any fixed-positioning or viewport-height CSS —
   this app has hit real, hard-to-reproduce-in-devtools Android bugs here
   before.
