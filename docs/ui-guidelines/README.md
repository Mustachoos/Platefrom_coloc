# UI guidelines — guest-facing pages

Design system for the pages guests reach from the bottom nav (Upload, Gallery/My photos, Whiteboard)
and any future page in that same family. **Not** for the TV screen, which is a separate context with
its own local styles (`tv.html`/`tv.js`) — it's a passive display, not something a guest interacts with.
The admin dashboard and admin account page *do* now use this same system (they didn't when this doc was
first written), so most of what's below applies there too; where something is guest-specific, it says so.

All shared rules live in three files, loaded in this order on every page:
`static/photos/tokens.css` (CSS custom properties — colors, spacing, radii, shadows, type scale) →
`static/photos/base.css` (reset, element defaults, layout primitives, small utility classes) →
`static/photos/components.css` (one class per UI concept, BEM-style modifiers for variants). Page-specific
CSS should be the exception, not the norm — if you're writing more than a few one-off rules in a page's
local `<style>` block, check whether it belongs in `components.css` as a named, reusable class instead.

This file replaces an earlier version that documented a previous CSS system (`site.css`, classes like
`.btn.primary`, tokens like `--ink`/`--card`) — that system no longer exists anywhere in the codebase.
If you find a stale reference to it somewhere, it's a bug in that file, not a hint that the old system
survives.

## Page shell

Every guest page follows the same shell — note that only the **bottom nav** is fixed-position; the
header now flows normally at the top of the content:

```
┌─────────────────────────────┐
│ .view-header (in normal      │  icon + title, flows with content
│  flow, not fixed)             │
├─────────────────────────────┤
│                              │
│   .card (content, ≤ shell    │  page content goes here
│   max-width, centered)       │
│                              │
│                              │
│      .bottom-nav (fixed,     │  pill, centered, floats above content
│      pill, bottom-center)    │
└─────────────────────────────┘
```

Minimal template for a new guest page (copied from the real structure of `upload.html`):

```django
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Page title</title>
  {% load static %}
  {% load icons %}
  <link rel="stylesheet" href="{% static 'photos/tokens.css' %}">
  <link rel="stylesheet" href="{% static 'photos/base.css' %}">
  <link rel="stylesheet" href="{% static 'photos/components.css' %}">
</head>
<body>
  <div class="page shell">
    {% include "photos/_account_button.html" %}
    {% include "photos/_page_header.html" with page_icon="icon-name" page_title="Page title" %}
    <main class="card">
      <!-- page content -->
    </main>
  </div>
  {% include "photos/_footer_nav.html" %}
</body>
</html>
```

Load all three CSS files on every page, in that order — `components.css` assumes `tokens.css`'s custom
properties and `base.css`'s reset already ran.

### `.view-header` (was `.page-header`)

- Partial: `photos/templates/photos/_page_header.html`. Takes two params: `page_icon` (a name from
  `static/photos/icons/`) and `page_title` (plain text, shown as the page's `<h1>`).
- Icon + title **only** — no subtitle, no back button, same rule as before. It answers "what page am
  I on", nothing else. Root guest pages (Upload/Gallery/Whiteboard) are peers reachable from the
  bottom nav, so there's never a "back" to show. The one page in the whole app that genuinely needs a
  back action (`/account/`, reachable from *every* page via a floating button, not just this guest
  family) solves it differently — an inline back-arrow icon next to its own `<h1>`, not by growing this
  partial's responsibility. Follow that precedent rather than adding a `back_url` param here.
- **No longer `position:fixed`.** This is the one real structural change since this doc's original
  version: `.view-header` (`base.css`) is a normal flow element (`display:flex`, `margin-bottom:
  var(--space-md)`) at the top of `.page.shell`'s content. There's no hardcoded height, no
  `has-page-header` body class to remember, nothing to keep in sync — it just takes the vertical space
  its content needs. Only `.bottom-nav` is still fixed (see "Fixed positioning" below); don't reapply
  `position:fixed` to the header on the assumption it still needs it.
- Contextual info that isn't the page identity (e.g. "Uploading as {pseudo}") does **not** go in the
  header. Put it at the top of the content card instead (see `upload.html`).

### `.card` (content wrapper)

- `background: var(--surface)` (a translucent frosted white over the app's gradient background),
  `border-radius: var(--radius-xl)`, `box-shadow: var(--shadow-md)`, `padding: var(--space-md)`.
  `.card--solid` swaps to an opaque white background (`var(--surface-solid)`) for contexts that need a
  fully solid surface (the admin dashboard's panels, for instance) rather than the translucent guest
  look. `.card--tight` reduces padding for a denser panel.
- Width is controlled by the `.shell` wrapper around it (`max-width: 1180px`, centered), not by `.card`
  itself — `.card` has no width rule of its own, so it fills whatever container it's in. On a guest
  page, that container is typically also constrained narrower via inline styles per-page (see
  `account.html`'s `max-width:420px` for a single-purpose page) rather than a shared card-width rule;
  there is no single "every card is the same width" constant anymore.
- Don't reuse the bare `.card` class for anything that isn't a page-level or panel-level content
  wrapper. See `.photo-card` below for why that collision is a trap — it bit this codebase for real,
  once, before the redesign, and the lesson still applies to the new class names.

### `.bottom-nav` (was `.footer-nav`)

Partial: `photos/templates/photos/_footer_nav.html` (the file name is the one place the old "footer"
name survives — the CSS class inside it is `.bottom-nav`). `position:fixed`, centered pill at the
bottom of the viewport, `.bottom-nav__item` children with an `.is-active` modifier for the current page
(compared against `request.resolver_match.url_name`). The Whiteboard entry only renders when
`whiteboard_enabled` is true for the active event — check that context var is actually available on any
new page that includes this partial.

## Fixed positioning, not flow

`.bottom-nav` is `position:fixed`, not flow-positioned. This is deliberate: Android Chrome can compute
`100%`/`100vh` taller than what's actually visible once the on-screen nav bar is factored in, which
pushes a flow-positioned bottom bar out past the real edge, under the system UI. A `position:fixed`
element anchors to the true visible viewport instead and doesn't have that problem. This was a real,
user-reported bug on the whiteboard page before the fix that first documented this rule — don't
reintroduce flow positioning for the bottom nav to "simplify" a layout.

The header no longer needs this treatment (see `.view-header` above) since it flows above the content
instead of overlaying it — there's nothing for Android's viewport math to get wrong when there's no
fixed height being reserved for it. `.page`'s own `padding-bottom: calc(var(--space-xl) + 64px)`
(`base.css`) is what reserves clearance for the fixed bottom nav; a page that's fully custom-positioned
itself (Whiteboard) computes its own clearance instead, at runtime, from the header's and bottom nav's
*actual* rendered geometry (`document.documentElement.style.setProperty('--wb-stage-top', ...)` in
`whiteboard_draw.html`) rather than a hardcoded pixel constant — because neither is a fixed-height
fixture anymore, unlike in the old shell this doc originally described.

## Colors, spacing, typography

All defined as CSS custom properties on `:root` in `tokens.css` — never hardcode a hex value, spacing
number, or radius that already has a token. The full set, grouped by concern:

| Group | Tokens |
|---|---|
| Ink (text) | `--ink-900` (primary/headings), `--ink-600` (secondary/muted), `--ink-400` (placeholder/disabled), `--ink-on-dark` |
| Surfaces | `--surface` (translucent card), `--surface-solid` (opaque white), `--surface-sunken` (inputs, table stripes), `--surface-dark` (solid dark fill, e.g. `.btn--dark`) |
| Borders | `--line`, `--line-strong` |
| Status | `--success-bg`/`--success-ink`, `--warning-bg`/`--warning-ink`, `--danger`/`--danger-ink` |
| Accent | `--accent` — the **one** deliberate color, spent only on the liked-heart state and focus rings; don't add a second use of it |
| Type | `--font-sans`, `--font-mono`, `--text-xs` through `--text-2xl` |
| Space | `--space-3xs` through `--space-xl` |
| Radius | `--radius-sm`/`md`/`lg`/`xl`/`pill` |
| Shadow | `--shadow-sm`/`md`/`lg` |
| Motion | `--ease`, `--fast`, `--base` |

Shadows on light surfaces use the tokenized `--shadow-*` values (a soft, dark-tinted shadow derived
from the surface's own ink color, not a flat black one) — a plain `rgba(0,0,0,0.4)` shadow reads as a
different, heavier design language than the rest of the app.

Font is set once on `body` (`var(--font-sans)`, itself `"Manrope", system-ui, -apple-system, "Segoe UI",
sans-serif`) in `base.css`. Don't set `font-family` again on a per-page basis except for the deliberate
`.mono`/`--font-mono` exception (redirect URIs, technical values).

## Buttons

Base `.btn` rule applies automatically: `inline-flex`, centered content, `var(--space-2xs)` gap between
icon and text, pill radius (`var(--radius-pill)`), `:active` gives a small scale-down, `:disabled`/
`[aria-disabled="true"]` dims to 45% opacity. An icon and a text label just work side by side with no
extra markup.

Variants (add as a second class — note the **double-dash** BEM modifier syntax, not a dot-joined class):
- `.btn--dark` — solid dark fill (`var(--surface-dark)`), the primary call-to-action equivalent of the
  old `.btn.primary`.
- `.btn--light` — solid white fill with a border, for a secondary-but-not-outlined action.
- `.btn--outline` — transparent background, bordered — the old `.btn.secondary`.
- `.btn--danger` — solid red fill, for destructive actions — the old `.btn.delete`.
- `.btn--placeholder` — dashed border, muted text, for a disabled-looking affordance that isn't a real
  `:disabled` button (e.g. the greyed-out "Forgot password?" on staff login when no recovery email is
  configured — a `<span>`, not a `<button>`, styled with this class plus explicit `color`/
  `text-decoration-color` overrides, since it must never be clickable at all).
- `.btn--block` — full width, larger padding/font, for a page's one primary action.
- `.btn--sm` — smaller padding/font, for inline per-item actions (table row buttons, dialog footers).

A button (or any flex container) with children meant to **stack vertically** needs an explicit
`flex-direction:column` override — `.btn`'s base rule makes it `inline-flex` (row) by default, which
otherwise forces those children into a row. This bit a dashboard card once, under the old system; the
underlying CSS mechanism is identical today, so the same check applies to any new multi-line button.

## Icons

- Self-hosted Tabler icons (MIT), one SVG file per icon in `static/photos/icons/*.svg`. No CDN, no icon
  font, no emoji in the UI — the whole point is that these render identically regardless of the guest's
  browser/OS emoji set.
- Render via the `{% icon 'name' size=20 %}` template tag (`photos/templatetags/icons.py`). `{% load
  icons %}` at the top of any template that calls it directly; a template that only `{% include %}`s a
  partial which itself loads `icons` doesn't need to load it again.
- **Exact failure mode to know about**: `{% icon 'name' %}` raises `TemplateSyntaxError: Unknown icon
  'name'` if the SVG file is missing — and this has actually broken a packaged production release
  before, because `finders.find()` (which the tag uses) only searches the raw `static/` source, not the
  collected `STATIC_ROOT`. `packaging/launcher.spec` now bundles both trees specifically to defend
  against this; if you ever touch that spec file, keep both.
- Before adding a new icon, grep for one that already covers the need — `heart.svg` sat completely
  unused in the icon set for a while (a near-duplicate, `heart-filled.svg`, already covered the actual
  need) before being removed; don't recreate that.
- In plain JS with no template tags available (`tv.js`), inline the exact SVG markup as a string
  constant instead of reinventing the icon.
- **Keep text where it's genuinely doing work**, don't blindly convert everything to icon-only:
  destructive actions ("Delete", "Disconnect") stay labeled because a mis-tap is costly and unambiguous
  text prevents it. When in doubt, ask "would a first-time guest, at a party, slightly distracted, know
  what this icon does with zero label?" — if not, keep the word.

## Reusable components

Everything below lives in `components.css`, one rule block per component, in roughly this order in the
file:

- **`.status-pill`/`.status-dot`/`.status-dot--live`** — the "live" indicator pill (TV display).
- **`.segmented`/`.segmented__option`** — two-way toggle between sibling views that share one nav
  destination. Reference usage: `_photos_segmented.html` (All photos / My photos), included from both
  `gallery.html` and `my_photos.html`. Pill-shaped track (`var(--surface-sunken)`), active option gets
  `var(--surface-dark)` background via `.is-active`.
- **`.tabbar`/`.tabbar__tab`** — underline tabs, used by the staff dashboard's own tab navigation
  (Events / Optional features / TV layout / Whiteboard / Guests / Photos), a different pattern from
  `.segmented` since it's a full navigation row, not a two-way toggle.
- **`.badge`** + `.badge--success`/`.badge--neutral`/`.badge--warning`/`.badge--danger` — small status
  labels (invite status, event ACTIVE marker).
- **`.alert`/`.alert--boxed`/`.alert--success`** — the default (no modifier) alert reads as a warning
  color; `.alert--success` swaps the semantic color for a success message. `.alert--boxed` adds the
  filled-background, centered-text treatment used for most in-page messages.
- **`.field`/`.input`** — form field wrapper + text input. `.input:focus-visible` gets a solid
  `--ink-900` border; no separate focus-ring component, `:focus-visible` on `.input` itself handles it.
- **`.toggle`/`.toggle__track`** — a checkbox styled as an iOS-style switch, pure CSS (`:checked +
  .toggle__track` sibling selector), no JS needed for the visual state.
- **`.slider`/`.slider--spectrum`** — range inputs; the spectrum modifier is for the whiteboard's hue
  picker specifically (a rainbow gradient track).
- **`.swatch`/`.swatch-row`/`.is-selected`** — the whiteboard's preset color swatches.
- **`.table`** — plain data tables (dashboard's guest list, invite list).
- **`.media-list`/`.media-item`/`.media-item__name`, `.thumb`/`.thumb--sm`/`.thumb--md`** — a
  photo/drawing row with a thumbnail (top-liked panel, whiteboard drawing log).
- **`.like`/`.like--active`** — the heart icon + count, `--active` swaps to `var(--accent)`.
- **`.photo-card`/`.photo-card__meta`** — the compact per-photo tile used in grids. Deliberately a
  **different class from `.card`** — the page wrapper and the grid tile need very different visual
  treatment, and giving them the same class name was a real bug in this codebase once (a photo tile
  briefly inherited the big page-card's padding and shadow). If you add a new kind of card-like tile,
  give it its own class rather than reaching for `.card`.
- **`.qr-card`/`.qr-card__caption`** — QR code display (TV screen, dashboard Wi-Fi preview).
- **`.fab`/`.fab--light`/`.fab--dark`/`.fab-stack`** — small floating round icon buttons. Used for the
  whiteboard's zoom/confirm controls (the component's original reason for existing) and, more recently,
  the account/profile page's floating entry button (`_account_button.html`) present on every guest and
  staff page — same visual language, different placement per call site (each sets its own
  `position:fixed` coordinates inline rather than the component prescribing a position).
- **Bottom sheet** (whiteboard's tools panel, `.tool-panel`/`.tool-row`/`.tool-row__label`, is the
  reference implementation) — for a tool/options surface that must be reachable one-handed and fully
  hide when closed: `position:fixed`, full width, rounded top corners only
  (`border-radius: var(--radius-lg) var(--radius-lg) 0 0`), anchored above the bottom nav via padding
  (not `bottom: var(--wb-stage-bottom)`, since `translateY(100%)` only clears the sheet's *own* height —
  folding the nav clearance into `padding-bottom` instead keeps the slide-in math simple). Closed state
  is `transform:translateY(100%); pointer-events:none` — fully off-screen and non-interactive, not just
  invisible via `opacity`. An `opacity:0` sheet with `pointer-events:auto` left behind is still
  clickable, which was a real bug class earlier in this project; the fix (an explicit `.open` modifier
  toggling both `transform` and `pointer-events` together) is still exactly how `#options-panel` in
  `whiteboard_draw.html` works today. Prefer this pattern over a small corner-anchored popover for
  anything with more than one or two controls.
- **`.bottom-nav`/`.bottom-nav__item`** — see "Page shell" above.

## Adding a new guest page

1. Copy the [minimal template](#page-shell) above.
2. Pick (or add) an icon in `static/photos/icons/` for the header.
3. Wrap content in `.card`; reuse `.photo-card`/`.segmented`/`.btn--*`/etc. before inventing new
   component CSS.
4. Add the page to `_footer_nav.html` only if it's a top-level destination guests navigate to directly
   — not every page needs a bottom-nav entry (`/account/`, reached via the floating button instead, is
   the example to follow for a page that shouldn't be in the nav).
5. Verify on a real narrow viewport (or headless Chrome at ~390px width) that content doesn't get
   hidden under the fixed bottom nav (`.page`'s `padding-bottom` should already handle this — check it
   actually does on your new page rather than assuming), and on Android specifically if you touch any
   fixed-positioning or viewport-height CSS — this app has hit real, hard-to-reproduce-in-devtools
   Android bugs here before.
