---
name: sync-ram-concept-into-rss
description: Put a saved RAM Concept file into a RAM Structural System model (.rss) safely - refuse if RAM Manager has it open or if someone saved it since, archive the file it replaces, prove the member hash - or extract and hash the Concept member of any .rss. Use when a user asks to sync, swap, push or merge a Concept model into the production RAM model, to lock a design into S:, to archive the RAM model first, or to check which Concept state an .rss holds.
---

# Sync a RAM Concept file into an RSS model

The one tool for the step every slab workflow ends with: the newest
calculated Concept file goes into the RAM model on the job drive. Proven on
2636 (2026-10-01 to 10-08, about twenty swaps across three `.rss` files).

```text
python scripts/rss_member.py <model.rss> --hash            what the .rss holds now (sha256)
python scripts/rss_member.py <model.rss> --extract x.cpt   the Concept member, for inspection or as a base
scripts/sync-concept-into-rss.ps1 -Rss <model.rss> -Cpt <calculated.cpt> -ExpectMember <sha12> [-DryRun]
```

## Rules it enforces

- **Never while RAM Manager has the model open.** RAM Manager writes
  `<model>.usr` beside the model; the script refuses (or waits with
  `-WaitMinutes`). A Concept opened from RAM Manager saves into the `.rss`
  on close, so a swap under it would be lost or would lose his save.
- **Never over a state it was not built on.** `-ExpectMember` is the hash
  of the member the change was based on; if the engineer saved since, the
  script refuses and says so. Get the base hash with `rss_member.py --hash`
  before starting the work, not after.
- **Archive first, prove after.** The replaced file goes to
  `<folder>\Archive\<model>_<yyyyMMdd-HHmm>.rss` (or `-ArchiveDir`); the
  new file is built in the repo's `models\sync-*` work folder and the member
  hash is checked there and again on the job drive.
- **One swap per decision, on the engineer's word.** Show him the diff
  (`compare-ram-concept-models`) and swap once; three swaps in an hour left
  him opening a model that was not the one he expected (2636, 2026-10-07).
- The source `.rss` is never edited in place (`swap-concept-into-rss.py`
  writes a new archive); `-DryRun` builds and verifies without touching it.

## Members

An `.rss` is a zip. The elevated slab's Concept file is `...cpt<story>E`,
the mat `...cpt<story>M`. With one `E` member the script finds it; with more
pass `-Member cpt1027E`. The member keeps the archive's own file name
(`2636_02_gravity_slab.cpt1027E` inside `..._merged_10-7-26.rss`).

## After a sync

Say where the newest state lives (the `.rss`, the archive it replaced, the
job-folder file and its hash) in the job's STATUS. The engineer must never
pick up an outdated model; if a sync cannot be done, say so first.

## Bundled scripts

- `scripts/sync-concept-into-rss.ps1`: the sync (PowerShell, calls
  `ram-structural-system/scripts/swap-concept-into-rss.py`).
- `scripts/rss_member.py`: list, hash, extract the Concept member (read-only).
