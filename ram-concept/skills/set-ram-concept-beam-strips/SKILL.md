---
name: set-ram-concept-beam-strips
description: Set the RAM Concept design spans that run along concrete beams to the office T or L beam strip setup (Code T-beam width, T or L section, beam torsion and design system, middle strip on typical slab properties), then prove it from the saved file. Use when a slab has concrete beams, when top or bottom bars pile up at beam columns, or when a user asks for the T-beam, L-beam or beam strip setup.
---

# Set Beam Design Strips (RAM Concept)

A design span along a concrete beam left on slab settings makes Concept
spread a large number of bars across the slab strip (2636: 20 to 27 #9 over
beam columns against 10 typical). Set up as a T or L beam, the bars
concentrate over the beam and the count drops. Do this before any rebar
simplification.

Design strips are not in the Concept API, so the edit is driven through the
GUI and **proved from the saved file**, never from the script's own output.

```text
beam_spans.py (saved copy) -> TODO list + exact commands
  -> open the Design Spans plan for that direction
  -> apply-beam-strips.ps1 (one dialog per span)
  -> save a copy -> beam_spans.py again -> 10 of 10, exit 0
  -> Process > Generate Strips -> Calc All
```

## The setup (R. Darling, 2026-09-23 call)

Per span that runs along a beam, in `Edit > Selection Properties`:

| Tab | Setting | Value |
|---|---|---|
| Strip Generation | Column Strip Width Calc | Code T-beam (Code L-beam at a slab edge) |
| Column Strip | CS Cross Section Trimming | T or L |
| Column Strip | CS Torsion Design | Beam |
| Column Strip | CS Design System | Beam |
| Middle Strip | Middle Strip uses Column Strip Properties | unticked |
| Middle Strip | trimming, bars, covers, torsion, design system, detailer | the typical slab strip's values **for that direction** |

Strip generation is otherwise unchanged. Column strip covers were already
2 in on the beam spans reviewed; confirm with the engineer before changing
them. Hold shear bars until the engineer reviews.

The two directions sit in different bar layers, so the typical slab covers
differ: on 2636 longitude strips use 2 in and latitude strips 1 in.
`beam_spans.py` reads the typical values per direction and prints them.

## Run

1. Save a copy of the model and list the work:
   `python scripts/beam_spans.py <copy.cpt>`
   It prints each beam span as TODO or DONE, T or L, its midpoint, and the
   command for each direction.
2. In Concept, open **Design Strip > Longitude Design Spans Plan**. If it is
   an API session, Pause the Scripting Server. Hands off mouse and keyboard.
3. Run the longitude command it printed, for example:
   `scripts/apply-beam-strips.ps1 -Points "263.47,292.96;268.97,97.38" -TopBar "#9" -BottomBar "#7" -TopCover 2 -BottomCover 2`
4. Open the **Latitude Design Spans Plan** and run the latitude command.
5. Save a copy and rerun `beam_spans.py`. Done means every span DONE and
   exit code 0. Also check that no other span changed: the count of spans
   with non-slab column strip settings must equal the number of beam spans.
6. `Process > Generate Strips`, then Calc All. The beam's column strip
   narrows to the code flange width (2636: 12.8 ft to 8.8 ft).

## How the script selects and edits

- A span is selected by typing a 0.4 ft selection box at its midpoint into
  the command line. The box selects whatever it crosses, in the active plan
  only, so the right plan must be active.
- It reads the command prompt before and after each corner. A stray pending
  corner otherwise shifts every later box by one and edits the wrong span.
- It requires the dialog title `Edit 1 Selected Items`; anything else is
  skipped.
- Dropdowns are set by typing the first letters of the item, which is
  idempotent. The middle-strip checkbox is a toggle, so its state is read
  first and it is only clicked when ticked.
- Screen offsets are calibrated for Concept 2025, maximized, 100% scaling.
  On another setup, check one span by hand before a batch.

## Not proven yet

- **L beams.** `-Kind L` types "Code L" into the width dropdown; no edge
  beam existed on 2636 to try it, and `beam_spans.py` does not yet know the
  saved value for Code L-beam.
- **Several spans in one dialog.** Shift and Ctrl clicks did not add to the
  selection under automation, so the script edits one span per dialog
  (about 25 seconds each).
- Middle strip trimming, torsion and detailer are typed as Slab Rectangle,
  Wood-Armer and None. If `beam_spans.py` reports a different typical slab
  strip, edit those three lines.

## Validation

`python -m unittest ram-concept/tests/test_beam_spans.py`. Live-proven on
2636: 10 of 10 beam spans set and verified from the saved file, no other
span changed.

## Bundled scripts

- `scripts/beam_spans.py`: read-only finder and checker for a saved `.cpt`.
- `scripts/apply-beam-strips.ps1`: GUI driver for the active Design Spans
  plan.
