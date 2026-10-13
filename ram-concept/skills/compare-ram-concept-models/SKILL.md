---
name: compare-ram-concept-models
description: Compare two saved RAM Concept models (.cpt files or the Concept member inside an .rss) and report what changed - user stirrup regions and bar groups line by line, strips, calc options, program results - so the engineer's save and the agent's working copy are never confused. Use when a user asks what changed, which model is newer or current, to diff two Concept files, to check what the production model holds, or at the start of a session before any model work.
---

# Compare two RAM Concept models

Read-only. One command, two files, the differences by line:

```text
python scripts/compare_cpt.py <A.cpt|A.rss> <B.cpt|B.rss> [--ids zone-ids.json] [--member cpt1027E] [--json out.json]
```

Prints, for A and B: sha, size, when saved; a summary (spans, strips and
their width calc, boundaries, columns, walls, beams, openings, punching
checks, stud rail sets, rebar names, user and program reinforcement counts,
whether a calc is in the file, `Check capacity only`); then the user stirrup
regions and the user bar groups as same / changed / only in A / only in B,
each on its line in model feet. Exit 1 when the user reinforcement differs.

## When to run it

- **At the start of every session** and whenever the engineer says he
  saved: his model on the job drive against the agent's newest working
  file. On 2636 (2026-10-08) he had lengthened five zones by hand in the
  production model overnight while the agent's redesign sat unlocked in
  the job folder; the diff found it in a minute, and his file was taken as
  the design.
- **Before a sync** (`sync-ram-concept-into-rss`): show the diff, swap once.
- **Before a merge** of two people's work: it lists what each changed
  (2636, 2026-10-07: the reviewer's strips and bars against the engineer's
  stirrup zones, replayed onto the reviewer's file).
- **After a revert**: prove the file is back to the earlier one (identical
  sha, or only the intended lines differ).

## Reading the result

- `--ids` maps stirrup lines to the engineer's zone numbers (a JSON of
  `"x0,y0,x1,y1": "Zn"` in feet); a zone on the same line with an
  overlapping span keeps its number, so a lengthened zone reads as
  `changed`, not as a new one.
- Concept snaps a region's far end to a whole number of spacings; a 0.2 ft
  difference in one end is that, not an edit.
- Program results (bar groups, stirrup regions, detailed stirrups) differ
  after any recalc; they say whether a calc is present, not what changed.
- Strips are not in the API; a change in `spans` or `strip width calc`
  means someone edited them in the GUI (or a full-width copy was built).

## Bundled scripts

- `scripts/compare_cpt.py` (sqlite, read-only; an `.rss` member is
  extracted to the temp folder).
