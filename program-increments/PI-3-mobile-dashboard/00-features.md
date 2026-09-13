# PI-3: Mobile-usable staff/admin dashboard

One feature, refined with the user before any changes (see the AskUserQuestion round in
conversation — not reproduced here, only the resulting decisions).

## Decisions locked

1. **Scope**: both `/dashboard/` (staff) and `/admin-account/` (admin) — not just one.
2. **Approach**: responsive fixes to the existing pages, not a redesign — same tabs, same
   content, same navigation pattern (no bottom-nav, no dropdown replacing the tab bar). Layout
   adapts to a phone width; nothing new is hidden or restructured.
3. **Priority order** (if not everything lands at once): Photos (moderate/hide, delete) and
   Guests first, then TV layout / Optional features / Whiteboard. Events tab was **not** flagged
   as a priority — still must not be broken, just not the focus of extra polish.

## Feature A — Responsive fixes to the staff dashboard and admin page

**Problem.** `/dashboard/` has **zero** mobile handling — no `@media` rules at all, relying
entirely on incidental flexbox wrapping. Concretely broken: the 6-tab `.tabbar` (Évènements /
Fonctionnalités optionnelles / Disposition TV / Whiteboard / Invités / Photos) has no wrap or
scroll — on a phone-width screen it overflows the viewport with the later tabs unreachable.
`/admin-account/` already has one breakpoint (`@media max-width:720px`, stacks its two-column
hub layout) but the Wi-Fi verify popup's new "?" help callout (`left:100%` of the dialog) was
built without a narrow-viewport case — on a phone, where the dialog is already ~90vw wide, that
callout renders almost entirely off-screen.

**Scope.**
- `.tabbar` becomes a horizontally-scrollable strip below a phone-width breakpoint (same tabs,
  same click behavior — just scrollable instead of silently overflowing).
- Guests table (`/dashboard/`, Invités tab) reflows into stacked cards (one per guest) below the
  breakpoint, replacing the current sideways-scroll-a-table fallback — real usability
  improvement for the prioritized "check who's joined, remove someone" action.
- Photos tab: verify/tighten the Hide/Unhide + Delete button row inside each photo-card doesn't
  force the card wider than its grid cell on narrow screens.
- TV-layout tab's side column (QR codes / leaderboard cards, currently `flex:0 0 30%;
  min-width:220px`) switches to `flex:1 1 100%` below the breakpoint, so it fills the row width
  once wrapped onto its own line instead of leaving dead space beside it. Same treatment applies
  wherever "Optional features"/"Whiteboard" tab content uses the same side-column pattern.
- Fix the Wi-Fi verify popup's help callout: beside the dialog (`left:100%`) above the
  breakpoint as already built, repositioned into normal flow below the popup's content on
  narrow viewports.

**Out of scope.** No navigation pattern change (no bottom-nav, no dropdown-instead-of-tabs — the
user explicitly wants responsive fixes, not a redesign). No universal `.btn--sm` tap-target size
increase — that class is shared with every guest-facing page (gallery likes, my-photos delete,
etc.), so a global change there would ripple well beyond this PI's scope; only the
dashboard-specific layout/overflow problems are addressed here.

**Actors.** Staff, Admin.
