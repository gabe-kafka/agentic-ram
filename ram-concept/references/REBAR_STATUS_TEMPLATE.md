# <job> Slab Rebar Simplification: Status

Updated <date, time>. Read with
`agentic-ram/ram-concept/references/SLAB_REBAR_OPTIMIZATION.md`.

Copy this file to
`eng-agent/projects/<job>/ram-concept/rebar-simplify/STATUS.md` and keep it
current at the end of every session. It is the only record of where the job
stands that travels between machines.

## Where the model is

| What | Where | State |
|---|---|---|
| Newest working model | `<work folder>/round-N.cpt` | which layers are in; calculated or not |
| Production RAM model | `<path to .rss>` | date and time of the last sync; what it is missing |
| Before each sync | `<Archive folder>` | list of archived files |

Concept member inside the `.rss`: `<name>.cpt<story>E`. Next sync due: <time>.

## Result in the newest round

| Layer | Count groups | Bands | User tons | Program left |
|---|---|---|---|---|
| Bottom longitude | | | | |
| Bottom latitude | | | | |
| Top longitude | | | | |
| Top latitude | | | | |

Total user steel and what the program still adds. State whether any real
demand is left. Bar sizes and mats.

## What the engineer picked

- Bottom: bar size and the options-table row for each direction.
- Top over columns: typical counts.
- Top general bands: bar size and row.
- Strip and beam-span decisions, with who asked for them.

## Overrides on record (`decisions.json`)

Each one: layer, location, what the program would add, the reason, and
whether it came from a rule or from the engineer.

## Open, in order

1. ...

Include the flags for the engineer: bars that do not fit, very tight
spacing, changed geometry, slab outside every strip.

## Folder notes

Which work folders are current and which are earlier attempts. Any plan or
round numbers that were discarded, and why.

## To continue

The exact commands for `status`, `report` and the layout images on the
newest model.
