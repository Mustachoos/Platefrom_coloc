# PI-2 dependency plan

## Dependency graph

| Story | Depends on | Reason |
|---|---|---|
| US-A1 | none | single template edit, no other story in this PI yet |

## Dev waves

**Wave 1:**
- US-A1 (upload → dashboard back link)

Small enough (one file, one conditional block) to implement directly rather than dispatching an
isolated worktree agent — no parallelism to gain, and the story is fully self-contained.
