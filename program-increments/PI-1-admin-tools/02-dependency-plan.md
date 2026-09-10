# PI-1 dependency plan

## Dependency graph

| Story | Depends on | Reason |
|---|---|---|
| US-A1 | none | standalone delete-event endpoint |
| US-B1 | none | standalone dashboard entry point, no new backend logic |
| US-C1 | none | standalone export endpoint |
| US-D1 | none | standalone model field + toggle view |
| US-B2 | US-B1 | needs a way to acquire a dual session to verify the profile page renders both panels |
| US-D2 | US-D1 | needs the `hidden` field to exist before any view can filter on it |

No other story-to-story dependencies — A1, B1, C1, D1 touch disjoint code (events tab / dashboard
entry point / export endpoint / photo model+toggle), so nothing here blocks anything else.

## Dev waves

**Wave 1 — dispatch in parallel:**
- US-A1 (delete event)
- US-B1 (start guest session entry point)
- US-C1 (export event photos)
- US-D1 (hide/unhide toggle)

**Wave 2 — dispatch in parallel, after wave 1 closes:**
- US-B2 (dual-session profile page)
- US-D2 (hidden-photo filtering)

Both waves run each story as dev + test in parallel against the story's fixed contract (per
`program-increments/README.md` stage 5) — wave 2 doesn't start until wave 1's stories are marked
done in `03-dev-log.md`, since B2 and D2 both build on wave-1 output.
