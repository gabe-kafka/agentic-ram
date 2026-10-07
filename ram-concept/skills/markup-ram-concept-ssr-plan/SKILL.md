---
name: markup-ram-concept-ssr-plan
description: Tag the column location plan (sheet S101D) with the stud rail mark SR-n at every stud rail column, as Bluebeam text-box markups the drafter can move or retype, from the office SSR workbook and the engineer's PDF plot of the sheet. Use when a user asks for the SSR plan markup, the stud rail plan, the SSR labels or Bluebeam labels for the documentation team, or to tag or label the columns with their stud rail marks. Comes after schedule-ram-concept-stud-rails; it does not change the model or the workbook.
---

# SSR Plan Markup (RAM Concept, Bluebeam)

The documentation team gets two things for the stud rails, the form set by the
2636_03 handoff (`2636_03_SSR.xlsx` and `2636_03_(26-06-18)_Coord Review -
SSR Markups.pdf`, a drafter's hand markup): the workbook's `FOR CAD` tab (the
schedule table, from `schedule-ram-concept-stud-rails`) and the column
location plan with a blue `SR-n` text box beside each stud rail column's
bubble. This skill makes the second.

```text
SSR workbook accepted (Mk per column, Column at (x, y) ft)
  + the engineer's fresh plot of S101D in the export folder
  -> the workbook rows proved against the rail sets in the model he is in
  -> markup_ssr_plan.py <SSR.xlsx> <plot.pdf> <out.pdf> --report <placements.json>
  -> the problem list is empty, the render is checked
  -> the PDF opened in Bluebeam Revu for him
```

## What is automated

| Step | Tool | How it is proved |
|---|---|---|
| Tags | `scripts/markup_ssr_plan.py` | 2636_02: 51 of 51 columns tagged at their bubble, worst match 0.53 ft, 6 tags dropped below the bubble to clear a 15 ft neighbour, 0 flagged |
| Placement record | `--report placements.json` | every tag with its column, bubble number, residual and page position; kept in the job repo |

Read-only on the model and the workbook. The source PDF is not touched; the
output is a new one-page file.

## How it works

- **Columns.** `SSR Input` gives each stud rail column's Mk and Concept `(x, y)`.
  The plan prints `X:ff'-ii"` and `Y:` from its work point beside every column.
  The Concept origin is not the work point (2636_02: 11.8 ft in x, 30.2 ft in
  y), so the shift is taken from the data, the most common whole-foot
  difference over every column pairing, and each workbook column is matched to
  the label within 1 ft. The workbook rounds to whole feet, so residuals up to
  about 0.6 ft are normal.
- **Bubbles.** The column number is a block attribute at a fixed offset from
  the column, so it is found through a page fit: fit the page from the labels,
  take the dominant offset of integers from the fitted columns, refit on those
  bubbles, then the nearest unused integer within 30 pt, and a second pass at
  60 pt for bubbles the drafter nudged aside. Nearest-text alone picks the
  neighbour's bubble at 15 to 20 ft column spacing. The bubble is for the
  report (`col 43 SR-1`); the tag is placed on the column symbol.
- **Column symbol.** The column is a small stroked rectangle in the page's
  vector drawings (24 x 16 in is 9 x 6 pt at 1/16 in = 1 ft). It is taken as
  the stroked single-item rect of 3 to 14 pt nearest the block's fitted bubble
  spot, within 35 pt, with the actual bubble as the second try. The fitted spot
  matters: where the drafter moved a bubble (2636_02 column 67 at the stair),
  the symbol is still at the block's offset.
- **Where the tag goes.** Engineer's rule, 2026-10-07, after the first pass
  put tags beside the bubbles and he said it was unclear which label applied
  to which column: the box **touches the right side of the column symbol**,
  bottom edge level with the symbol's bottom, so it sits up out of the `X:`/`Y:`
  text of the next column. The block puts the bubble up-right of the symbol,
  where that box would clip it, so the box slides down only as far as the
  bubble's 9 pt circle requires, never below top-aligned with the symbol
  (2636_02: every one of the 51 stayed on the right side). `settle()` falls
  back to touching the left side, then hanging under the symbol, only against
  other columns' bubbles, other symbols and earlier tags.
  A column with no symbol found gets the bubble placement (right, below, above)
  and a PROBLEMS line.
- **Tags.** `add_freetext_annot(rect, text, fontsize=10, fontname="helv",
  text_color=blue, fill_color=None, border_width=1)`: blue Helvetica 10 pt in a
  1 pt blue box drawn in the text colour, no fill, 30 x 14 pt, subject
  `Text Box`, author `--author` (default `GKG`). `DS` and `RC` carry the same
  style so Bluebeam keeps blue 10 pt when a tag is retyped. In pymupdf,
  `richtext=True` loses the colour and size and `border_color` is refused
  outside rich text; this way needs neither.
- **Misses.** A column with no label within 1 ft, or no bubble and no symbol,
  is listed under PROBLEMS and still tagged at its label with a `?`. Nothing is
  dropped.
- **Non-typical columns** (the engineer's equal-length rule, in
  `schedule-ram-concept-stud-rails`): a row whose Mk is `NON-TYPICAL` is
  tagged in red with the fix written in its COMMENTS cell, for example
  `DROP CAP 5'x5'x18 1/4" DP (RSD 10/7)`, so the drafter sees a condition
  still being resolved, not a stud rail mark. The box widens to the text.
- **Rerun on a previous output.** The engineer tidied the export folder and
  the plot went with it; the tagged PDF still holds the page. Given as the
  plan, this author's earlier tags are removed and other markups (the
  signature stamp, the drafter's notes) stay; the output may be the same
  file. Keep the plot anyway when you can: it is the clean record.

## Rules

- **Tag from the engineer's plot.** He plots the current S101D from AutoCAD
  into `Calculations\03_RAM Structural\2-Way Reinf Export\` himself, named
  `<job>_(yy-mm-dd)_Coord Review - SSR Markups.pdf`. It is newer than the
  permit set and carries his signature stamp. Never write over it; the tagged
  file gets its own name (`<job>_(yy-mm-dd)_SSR Markups.pdf`).
- **Prove the workbook against the model first.** Read `SsrSet` from the
  saved model he is working in (the `.cpt1027E` inside his `.rss`) and compare
  rails, studs and spacings row by row with `SSR Input`. If he has regrouped
  the marks or set rails to `User`, the workbook is what the tags follow, so it
  must be current.
- **Check the problem list and the render before handing on.** A `?` tag is a
  column the drafter would have to place by hand.
- **Open the result in Revu for him** (`Start-Process <pdf>`); the Markups List
  is his check.
- Any change to the marks means a rerun; the tags are not edited one by one.

## Not built

- Exterior columns with rails on three or two sides (configurations B, C):
  the tag is the same, the schedule row is not.
- Pasting the `FOR CAD` table onto the sheet; the drafter does that.
- Plans without printed `X:`/`Y:` labels: the fit has nothing to read.

## Drawing column numbers back into the workbook

The workbook's column A is only a running row number from the builder. The
engineer wants the drawing's column number on each row (2636_02, 2026-10-07:
"add the column labeling from the pdf and our drawing set"). The markup's
`--report` holds that mapping (Concept `(x, y)` to bubble), so after the
markup:

```powershell
powershell.exe -NoProfile -File scripts\write-plan-columns.ps1 -Workbook <SSR.xlsx> -Report <placements.json>
```

It inserts `Plan Col. (S101D)` right after `Column at (x, y) ft` (the type
table shifts one column right and its formulas follow) and fills it by
matching `(x, y)`. Run it under Windows PowerShell 5.1 (`powershell.exe`),
not 7: when the engineer has the workbook open, 5.1 can attach to his
running Excel and write there, which is what he sees; PowerShell 7 cannot
reach a running Excel. 2636_02: 51 of 51 rows filled, type table still OK.

## Bundled scripts

- `scripts/markup_ssr_plan.py`
- `scripts/write-plan-columns.ps1`
