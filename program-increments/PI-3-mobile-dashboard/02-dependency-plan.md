# PI-3 dependency plan

## Dependency graph

| Story | Depends on | Reason |
|---|---|---|
| US-A1 | none | single cohesive CSS/template change across two files, one story |

## Dev waves

**Wave 1:**
- US-A1 (responsive dashboard + admin fixes) — CSS-only, tightly coupled (same breakpoint value,
  same two templates); implement directly, no subagent dispatch.
