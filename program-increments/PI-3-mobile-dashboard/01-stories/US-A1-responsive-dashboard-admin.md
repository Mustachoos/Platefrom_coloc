# US-A1 — Responsive fixes to the staff dashboard and admin page

**As** a staff member or admin, **I want** `/dashboard/` and `/admin-account/` to work on a
phone-width screen, **so that** I can moderate photos, check guests, and manage the event without
needing a laptop.

**Feature:** A. **Depends on:** none.

## Contract

Breakpoint: reuse the one breakpoint `admin_management.html` already established,
`@media (max-width: 720px)`, applied consistently to both templates rather than inventing a
second breakpoint value.

### 1. `.tabbar` overflow (`static/photos/components.css`, `dashboard.html`'s 6-tab bar)

`.tabbar` (`components.css` ~line 166) currently has no wrap/scroll handling at all —
`display:flex; gap:var(--space-md); border-bottom:1px solid var(--line);`. Below the breakpoint:
```css
@media (max-width: 720px) {
  .tabbar {
    overflow-x: auto;
    flex-wrap: nowrap;
    -webkit-overflow-scrolling: touch;
  }
  .tabbar__tab {
    flex: 0 0 auto;
    white-space: nowrap;
  }
}
```
Same tabs, same click handler, same active-tab logic — purely a scroll-instead-of-overflow fix.
No dots/arrows/scroll-shadow affordance — out of scope for a fix-not-redesign.

### 2. Guests table → stacked cards (`dashboard.html`, Invités tab, priority)

The current markup is a `<table class="table">` inside `<div style="overflow-x:auto;">`. Below
the breakpoint, reflow into one card per guest instead of a scrollable table (a sideways-scrolled
table is a worse experience on a touchscreen than stacked cards for a 4-column list this short).
Add a `.guest-cards` wrapper alongside the existing table (both rendered; CSS `hidden`s the wrong
one per breakpoint — avoids a JS reflow, matches how the rest of this app already hides
alternate markup with plain media queries rather than JS):
```html
<div class="table-wrap" style="overflow-x:auto;">
  <table class="table">...</table>
</div>
<div class="guest-cards">
  {% for identity in identities %}
  <div class="card card--solid card--tight guest-card">
    <div class="flex justify-between items-center">
      <span style="font-weight:700;">{{ identity.pseudo }}</span>
      <form method="post" action="{% url 'dashboard-delete-guest' identity.id %}">
        {% csrf_token %}
        <button type="submit" class="btn btn--danger btn--sm">Supprimer</button>
      </form>
    </div>
    <div class="text-sm text-muted">{{ identity.email|default:"—" }}</div>
    <div class="text-sm text-muted">Drive partagé : {{ identity.drive_shared|yesno:"Oui,Non" }} · Arrivée : {{ identity.created_at }}</div>
  </div>
  {% endfor %}
</div>
```
```css
.guest-cards { display: none; flex-direction: column; gap: var(--space-2xs); }
@media (max-width: 720px) {
  .table-wrap { display: none; }
  .guest-cards { display: flex; }
}
```
Same fields as the table (pseudo, email, drive-shared, arrival, delete button) — no data dropped.

### 3. Photos tab button row (`dashboard.html`, priority)

`.photo-card`'s Masquer/Réafficher + Supprimer buttons already sit in a `display:flex;gap` row
below the thumbnail, inside a CSS grid cell (`minmax(160px,1fr)`) — verify in-browser this
doesn't overflow the 160px minimum on a narrow phone; if it does, add:
```css
@media (max-width: 720px) {
  .photo-card > div[style*="display:flex"] { flex-wrap: wrap; }
}
```
(Targeting via a dedicated class is cleaner than an attribute selector — if this turns out to be
needed, add `.photo-card__actions` to that div's existing `style` attribute instead of leaving
the inline style, then target the class.)

### 4. TV-layout / Optional-features / Whiteboard side column (`dashboard.html`)

The `tv-layout` panel's right-hand column (`flex:0 0 30%;min-width:220px;` around line 179)
holds the QR-codes and bottom-right cards stacked vertically. Below the breakpoint:
```css
@media (max-width: 720px) {
  #panel-tv-layout .flex.gap-sm.flex-wrap[style*="align-items:stretch"] > * {
    flex: 1 1 100% !important;
  }
}
```
Simplest robust approach: give that specific flex container and its two children real classes
(`.tv-layout-row`, `.tv-layout-main`, `.tv-layout-side`) instead of matching on inline styles —
inline `style` attributes can't be overridden by a later `!important`-free media rule reliably
across browsers, and matching on `[style*=...]` is brittle if the inline style text ever
changes. Add the three classes in the template, keep existing inline styles for the base layout,
and add:
```css
@media (max-width: 720px) {
  .tv-layout-main, .tv-layout-side { flex: 1 1 100%; }
}
```
This removes the 30%-width dead space once the side column wraps onto its own row. The
Fonctionnalités-optionnelles and Whiteboard panels don't use this side-column pattern (they're
already single-column), so no change needed there beyond general breakpoint hygiene already
covered by items 1–3.

### 5. Wi-Fi verify popup help callout (`admin_management.html`, bug fix)

`#wifi-qr-help-text` is `position:absolute;top:0;left:100%` relative to the dialog (line ~332).
The dialog itself is `.wide` — check its max-width in CSS; if it approaches the viewport width on
a phone, `left:100%` places the callout entirely off-screen. Fix: keep the side-callout
positioning above the breakpoint, switch to static in-flow positioning below it:
```css
@media (max-width: 720px) {
  #wifi-qr-help-text {
    position: static;
    margin: var(--space-sm) 0 0;
    width: auto;
  }
}
```
Since `#wifi-qr-help-text` is currently the last child of `<dialog>` (a sibling after the button
row, not inside the `padding` wrapper div), switching to `position:static` places it below the
buttons in normal flow — acceptable, matches "helper text appears near what it explains."

### Out of scope (per feature doc)

Events tab: no dedicated responsive work beyond whatever items 1–4's breakpoint incidentally
helps (its cards already use `flex-wrap`). No navigation redesign. No global `.btn--sm` sizing
change.

## Acceptance criteria

- At a 375px-wide viewport: `.tabbar` scrolls horizontally instead of overflowing/clipping tabs;
  all 6 tabs remain reachable and clickable.
- At 375px: Invités tab shows one card per guest (not a horizontally-scrolled table); all 4
  fields (pseudo, email, drive-shared, arrival) and the Supprimer button are present and usable.
- At 375px: Photos tab's Masquer/Réafficher + Supprimer buttons don't overflow their grid cell.
- At 375px: TV-layout tab's side column (QR/leaderboard cards) fills the row width once wrapped,
  no dead space beside it.
- At 375px: opening the Wi-Fi verify popup and clicking "?" shows the help text fully on-screen,
  not clipped or off-canvas.
- At ≥720px width, all of the above render exactly as before this story (no regression to the
  desktop layout).
- Existing Django tests for these templates (`test_admin_dashboard_polish.py`, dashboard view
  tests) still pass — this is a CSS/markup-only change, no view/model behavior changes.

## Files touched

`static/photos/components.css`, `photos/templates/photos/dashboard.html`,
`photos/templates/photos/admin_management.html`. No Python, no migrations.
