---
name: clean-up-ram-concept-t-beams
description: Handle every place a concrete beam changes the slab rebar in a RAM Concept model - beam design strips, top bars where a beam runs through or ends at a column, the beam's own bottom bars, and bottom bars at beam ends - and record "no bar called out here" overrides with the reason. Use when a slab has concrete beams, when the user says t-beam cleanup, beam conditions, or asks to override a program bar because the beam carries it.
---

# T-Beam Cleanup (RAM Concept)

A concrete beam in a slab changes the rebar in five places. This skill owns
all five: the rule for each, the check, and the record of what the engineer
overrode. The top and bottom rebar skills call into it; they do not carry
beam rules of their own.

```text
status (saved, calculated model)
  1 strips -> 2 top, beam through -> 3 top, beam end
  -> 4 bottom, mid-span -> 5 bottom, beam end
  -> anything OPEN: fix or override -> status again -> nothing open
```

## The five conditions

| # | Where | Rule | Who decides |
|---|---|---|---|
| 1 | Design spans along a beam | T or L beam strip setup, before any rebar work | rule |
| 2 | Top bars, beam runs through the column, parallel to the bars | **No top bar called out.** The beam carries the moment | rule, recorded as an override |
| 3 | Top bars, beam ends at the column | The column keeps its own count and length; it does not stretch the typical callouts | rule |
| 4 | Bottom bars inside the beam, mid-span | The beam's own bars: by count, beam depth, program's end conditions. Never banded with slab bars | rule |
| 5 | Bottom bars inside the beam, reaching its end | Never added automatically. The engineer adds them or overrides | engineer |

Why, in one line each:

1. On slab settings Concept spreads a large count of bars across the slab
   strip (2636: 20 to 27 #9 over beam columns against 10 typical).
2. The beam's own top steel is continuous through the column.
3. The slab past the beam end takes the beam's end moment on a much smaller
   depth, so these columns are heavier and longer than slab columns.
4. A band at slab depth gets no credit in a beam; chasing these with bands
   never converges.
5. They balance the heavy top bars over the end column. On 2636 the engineer
   left them out: the top bars there are already conservative.

A bar inside a beam is "at the end" when it reaches within 1 ft of the beam
end, otherwise mid-span. Mid-span leftovers after the beam bars are drawn
are real: the bottom tool adds them to that beam's count on its next absorb.

## Run (from this skill's `scripts/`)

```powershell
python t_beam_cleanup.py status --model <job>\rebar-simplify\<work>\round-N.cpt
```

Read-only; no Concept session. Exit code 1 while anything is OPEN.

| OPEN line | Fix |
|---|---|
| 1, spans not set | `../set-ram-concept-beam-strips`, then Generate Strips and Calc All |
| 2, user bars drawn at a through column | rerun the top tool's `plan` and `run` |
| 3, program still adds at a beam-end column | rerun the top tool |
| 4, program still adds mid-span | bottom tool `absorb` then `run` for that layer |
| 5, needs your call | engineer adds the bars by hand, or records an override |

## Overrides: "no bar called out here"

An override says no bar is called out at a location, and why. The program
bar stays yellow in Concept (it shows what it would add with nothing drawn);
the tools stop chasing it and report it as overridden with the count the
program wanted.

```powershell
python t_beam_cleanup.py override --job <job>\rebar-simplify --layer top-long --at 269 111 --reason "beam carries this moment"
python t_beam_cleanup.py override --model <round-N.cpt> --beam-ends --reason "top bars over the column are already conservative"
```

- The record is `decisions.json` in the folder that holds the work folders.
  Each entry: layer, x, y, reach (6 ft), reason, source (rule or engineer),
  date. Edit or delete entries by hand to undo one.
- Condition 2 is recorded automatically by the top tool's `plan`, with
  source "rule". Everything else needs the engineer to say so first. Never
  record an override the engineer did not ask for.
- `--beam-ends` covers both bottom layers unless `--layer` is given.
- Put the overrides in the report every time, with the program's count.
  They are engineering decisions, not cleanup.

## Report

The five numbered blocks from `status`, then the open count. Callouts as
count then size: `15#7 x 26'`.

## Flag to the engineer

- More bars than fit one layer in the beam web (2636: 13 to 15 #7 in a
  20 in beam). Suggest a larger bar; do not change size without asking.
- A through column where the program would add many bars (2636: 8#9 at
  (269,111)). The beam design must show that top steel.

## Validation

`python -m unittest ram-concept/tests/test_t_beam_cleanup.py`. Live on 2636
only: 10 of 10 strips, 2 through columns, 14 beam-end columns, 9 beam bar
groups.

## Bundled scripts

- `scripts/t_beam_cleanup.py`: `status` and `override`; model reads for
  beam columns.
- `scripts/beam_rules.py`: the rules and the override record (pure, tested).
  Imported by the top and bottom tools.
