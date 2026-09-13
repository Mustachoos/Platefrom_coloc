# PI-2 dependency plan

## Dependency graph

| Story | Depends on | Reason |
|---|---|---|
| US-A1 | none | single template edit, no other story in this PI yet |

| US-B2 | US-B1 | needs `notify.js`/`.notify` CSS to exist |
| US-B3 | US-B1 | needs `notify.js`/`.notify` CSS to exist; independent of US-B2 but both touch `upload.html` — expect a merge conflict, resolve additively |

## Dev waves

**Wave 1:**
- US-A1 (upload → dashboard back link) — done, implemented directly.

**Wave 2:**
- US-B1 (notification component) — foundational, no parallelism to gain building it alone;
  implement directly rather than dispatching a worktree agent.

**Wave 3 — dispatch in parallel once US-B1 is merged:**
- US-B2 (wire Django messages)
- US-B3 (wire upload/whiteboard JS status feedback)

Both touch `upload.html` (B2 adds the message-span pattern + `notify.js` include; B3 reworks the
JS status logic there) — expect one merge conflict there, same as prior PI's overlapping-file
waves; resolve additively.
