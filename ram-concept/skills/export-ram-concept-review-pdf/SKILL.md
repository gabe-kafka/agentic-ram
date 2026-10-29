---
name: export-ram-concept-review-pdf
description: Produce the PDF a senior engineer reviews for the slab additional reinforcement (moment) - the Concept plan windows exported to PDF in the office's set and order, top reinforcement then bottom, no markups. Use when the user says review PDF, boss review, export for review, additional reinforcement PDF, moment add'l reinf export, or hands over a marked-up review set to reproduce.
---

# Export the additional reinforcement review PDF (RAM Concept)

The reviewer marks up a PDF of Concept's own plan windows. This skill makes
that PDF again from the current model, clean: the same views, the same
order, no markups. Learnt from 2636 building 1 (2026-10-29): Ryan's marked
set `Review\Additional Reinf\2636_01_Additional rienf.pdf` and the clean
export it was made from, `concept.pdf` beside it (2026-10-14).

**The engineer does this by hand for now.** Do not take over the screen:
guide the steps. The automation below is noted, not proven.

## The set, in order

Top reinforcement first, then bottom. Each page is one plan window from the
Layers tree, exported as it is:

| Page | Tree path | What the reviewer reads |
|---|---|---|
| 1 | Reinforcement > Top Bars Plan | all top bars, user and program, with callouts |
| 2 | Strength Design > Top Reinforcement Plan | top span and design-section designs, with the Section Analysis Plot: Moment, Min Demand / Min Capacity |
| 3 | Reinforcement > Bottom Bars Plan | all bottom bars, user and program |
| 4 | Strength Design > Bottom Reinforcement Plan | bottom designs with the Section Analysis Plot: Moment, Max Capacity / Max Demand |

Optional, as in the 2026-10-14 set: Top Long, Top Lat, Bot Long, Bot Lat
(Reinforcement plans, one face and direction each) after their face.

The Strength Design plans are the "moment capacity and demand" pages: the
plot shows demand and capacity along each design section, so the reviewer
sees where the bars fall short. Their plot context must be set before export
(Min for top, Max for bottom); check it in the plan's visible objects.

## Steps (by hand)

1. Open the calculated model the review is for: the newest state (see
   `never pick up an outdated model`), not a stale working copy. Plans read
   saved results, so calc first if anything changed.
2. Page setup, once per model: `Report > Setup PDF Export...` > Size A1,
   Landscape (the marked set is 36 x 24 in; A1 is 33.1 x 23.4 in, the
   closest Concept offers). OK.
3. Scale, once per model: `View > Print Scale...` > 1:150 (1:250 was too
   small on 2636), tick `Set for all plans`. OK.
4. For each page in the table: double-click the plan in the Layers tree,
   then `Report > Export Window to PDF...`, name it `NN <plan>.pdf` in the
   job's `ram-concept\review\<date>\` folder, Save. Concept prints a white
   page with the plan title, the visible-objects legend, the scale and the
   page footer.
5. Combine in order (Bluebeam Stapler, or `pymupdf`): top bars, top
   strength design, bottom bars, bottom strength design. Name it
   `<job>_Additional reinf_<date>.pdf` beside the earlier review sets.

`Report > Export Report to PDF...` exports the whole report tree instead;
it is the alternative when the report sections are set to exactly these
plans.

## What the reviewer checked on 2636 building 1 (Ryan, 2026-10-28)

Useful to look at before sending the set:

- Duplicated additional bar regions (bars stacked at 3 in): run the
  stacked-copies check (`simplify-ram-concept-top-rebar` report, STACKED).
- Top bars two bar sizes larger than the mat.
- Bottom bars: start and stop at logical points; reduce extents; same
  design-strip issue as the other building.
- Program bars still generated where user bars were drawn: iterate, do not
  double-reinforce.

## Automation notes (not proven; for a later tool)

- Concept's menus answer UI Automation by name (`Report > Setup PDF Export...`,
  `Export Window to PDF...`); Pause the Scripting Server first. A menu item
  that opens a modal dialog blocks `Invoke()` until the dialog closes: invoke
  it from a background job.
- The Export PDF file dialog: setting the file name box (Edit 1001) by
  `WM_SETTEXT` and pressing Save once saved the typed path and twice saved
  the default name `export.pdf` in the last folder. Typing into the box
  (focus, select all, type the name, Enter) saved reliably, but that is real
  keystrokes: only with the engineer away from the PC.
- Opening a plan: double-click its tree item; a tree item may expose
  `SelectionItemPattern`, not yet tried.
- An existing file name raises Concept's "replace the existing file?" box,
  which blocks everything after it. Use a new folder per export.
