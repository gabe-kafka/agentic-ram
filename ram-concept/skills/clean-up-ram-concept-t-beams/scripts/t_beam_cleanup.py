#!/usr/bin/env python3
"""T-beam cleanup: every place a concrete beam changes the slab rebar, checked from one saved model.

  status    --model <calculated .cpt>
            the five beam conditions, and what is still open (exit 1 while anything is)
  override  --layer top-long --at X Y --reason "beam carries this moment"
            no bar is called out there; what the program would add is reported, not chased
  override  --model <calculated .cpt> --beam-ends --reason "..."
            the same for every program bottom bar left at a beam end

Decisions go to decisions.json in the job folder (--job; default: two levels
above --model, the folder that holds the work folders). Read-only on the
model; no Concept session needed.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
for other in ("simplify-ram-concept-rebar", "set-ram-concept-beam-strips"):
    sys.path.insert(0, str(SKILLS / other / "scripts"))

import beam_rules as br      # noqa: E402
import beam_spans            # noqa: E402
import cpt_reader as cr      # noqa: E402

TOP, BOTTOM = ("top-long", "top-lat"), ("bot-long", "bot-lat")
THROUGH = "beam carries this moment"


# ---------------------------------------------------------------- model reads

def columns(path: Path) -> list[tuple[float, float]]:
    return [beam_spans.point(p) for (p,) in cr.connect(path).execute("select Point0 from Column")]


def beams(path: Path) -> list[tuple]:
    return [(beam_spans.point(a), beam_spans.point(b), w / cr.FT)
            for a, b, w in cr.connect(path).execute("select Point0, Point1, Width from Beam")]


def beam_columns(path: Path, layer: cr.Layer) -> dict[int, int]:
    """Columns on a beam parallel to this layer's bars: 2 = beam runs through, 1 = beam ends there."""
    return br.beam_columns(columns(path), beams(path), layer.direction)


def through_columns(path: Path, layer: cr.Layer) -> set[int]:
    return {i for i, n in beam_columns(path, layer).items() if n == 2}


def end_columns(path: Path, layer: cr.Layer) -> frozenset:
    return frozenset(i for i, n in beam_columns(path, layer).items() if n == 1)


def beam_bars(path: Path, layer: cr.Layer, designed_by: int) -> tuple[list, list]:
    """Bars inside a beam along this layer, as (mid-span, at a beam end)."""
    rects = cr.beam_rects(path, layer)
    inside = [d for d in cr.bars(path, layer, designed_by) if br.in_beam(d, rects)]
    ends = [d for d in inside if br.at_beam_end(d, rects)]
    return [d for d in inside if d not in ends], ends


# ---------------------------------------------------------------- report

def callout(d) -> str:
    return f"{d.count}{d.size} x {round(d.length, 1):g}'"


def total(bars) -> str:
    sizes = Counter()
    for d in bars:
        sizes[d.size] += d.count
    return " + ".join(f"{n}{size}" for size, n in sizes.items()) or "nothing"


def centre(d, layer: cr.Layer) -> tuple[float, float]:
    return layer.to_plan((d.a0 + d.a1) / 2, (d.b0 + d.b1) / 2)


def over(d, a: float, b: float, reach: float = 2.0) -> bool:
    return d.a0 - reach <= a <= d.a1 + reach and d.b0 - reach <= b <= d.b1 + reach


def status(model: Path, job: Path) -> int:
    """Print the five beam conditions. Returns how many items still need action."""
    open_items = 0
    print(f"T-beam cleanup: {model.name}")

    spans, _ = beam_spans.read(model)
    todo = [o for o in spans if o["diffs"]]
    open_items += len(todo)
    print(f"1. Beam strips: {len(spans) - len(todo)} of {len(spans)} spans along beams set as beams"
          + ("  <- OPEN: set these first, then recalc" if todo else ""))

    cols = columns(model)
    top = {name: (cr.Layer.parse(name), cr.bars(model, cr.Layer.parse(name), cr.PROGRAM),
                  [d for d in cr.bars(model, cr.Layer.parse(name), cr.USER) if d.by_count]) for name in TOP}

    print("2. Top bars, beam runs through the column: no top bar called out")
    for name, (layer, program, user) in top.items():
        marks = [(cols[i], THROUGH) for i in sorted(through_columns(model, layer))]
        marks += [((o["x"], o["y"]), o["reason"]) for o in br.overrides(job, name)
                  if not any(math.hypot(o["x"] - x, o["y"] - y) < 1.0 for (x, y), _ in marks)]
        for (x, y), reason in marks:
            a, b = layer.to_local(x, y)
            drawn = [d for d in user if over(d, a, b)]
            open_items += bool(drawn)
            print(f"   {name} ({x:.0f},{y:.0f}) {reason} [program would add {total(d for d in program if over(d, a, b))}]"
                  + (f"  <- OPEN: {total(drawn)} drawn here, remove" if drawn else ""))

    print("3. Top bars, beam ends at the column: the column keeps its own count and length")
    for name, (layer, program, user) in top.items():
        for i in sorted(end_columns(model, layer)):
            x, y = cols[i]
            a, b = layer.to_local(x, y)
            drawn = [d for d in user if over(d, a, b)]
            more = [d for d in program if over(d, a, b) and (d.count > 2 or d.length > 5.0)]
            open_items += bool(more)
            print(f"   {name} ({x:.0f},{y:.0f}) " + (", ".join(callout(d) for d in drawn) or "no top demand, no bars")
                  + (f"  <- OPEN: program still adds {', '.join(callout(d) for d in more)}" if more else ""))

    bottom = {name: cr.Layer.parse(name) for name in BOTTOM}
    print("4. Bottom bars in the beam, mid-span: the beam's own bars, by count")
    for name, layer in bottom.items():
        drawn = [d for part in beam_bars(model, layer, cr.USER) for d in part if d.by_count]
        short, _ = beam_bars(model, layer, cr.PROGRAM)
        open_items += len(short)
        for d in drawn:
            x, y = centre(d, layer)
            print(f"   {name} ({x:.0f},{y:.0f}) {callout(d)}")
        for d in short:
            x, y = centre(d, layer)
            print(f"   {name} ({x:.0f},{y:.0f})  <- OPEN: program still adds {callout(d)}; add to the beam's bars")

    print("5. Bottom bars at a beam end: the engineer's call, never added automatically")
    for name, layer in bottom.items():
        found = br.overrides(job, name)
        for d in beam_bars(model, layer, cr.PROGRAM)[1]:
            x, y = centre(d, layer)
            o = br.override_at(found, x, y)
            open_items += o is None
            print(f"   {name} ({x:.0f},{y:.0f}) " + (f"no bottom bar called out: {o['reason']}" if o else "<- OPEN: needs your call")
                  + f" [program would add {callout(d)}]")

    print(f"{open_items} open" if open_items else "nothing open")
    return open_items


# ---------------------------------------------------------------- commands

def cmd_override(a) -> int:
    if a.beam_ends:
        for name in ([a.layer] if a.layer else BOTTOM):
            layer = cr.Layer.parse(name)
            for d in beam_bars(a.model, layer, cr.PROGRAM)[1]:
                x, y = centre(d, layer)
                added = br.add_override(a.job, name, x, y, reason=a.reason, source="engineer", reach=a.reach)
                print(f"{'recorded' if added else 'already recorded'}: {name} ({x:.0f},{y:.0f}) no bar called out [{callout(d)}]")
    else:
        x, y = a.at
        added = br.add_override(a.job, a.layer, x, y, reason=a.reason, source="engineer", reach=a.reach)
        print(f"{'recorded' if added else 'already recorded'}: {a.layer} ({x:g},{y:g}) no bar called out: {a.reason}")
    print(f"-> {br.decisions_file(a.job)}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["status", "override"])
    p.add_argument("--model", type=Path, help="a saved, calculated .cpt (status, override --beam-ends)")
    p.add_argument("--job", type=Path, help="folder holding decisions.json (default: two levels above --model)")
    p.add_argument("--layer", choices=TOP + BOTTOM, help="override: which face and direction")
    p.add_argument("--at", type=float, nargs=2, metavar=("X", "Y"), help="override: plan location in feet")
    p.add_argument("--beam-ends", action="store_true", help="override: every program bottom bar left at a beam end")
    p.add_argument("--reason", help="override: why no bar is called out there")
    p.add_argument("--reach", type=float, default=6.0, help="override: radius in feet")
    a = p.parse_args(argv)
    if a.model:
        a.model = a.model.resolve()
    if a.job is None:
        if a.model is None:
            p.error("give --job or --model")
        a.job = a.model.parent.parent
    a.job = a.job.resolve()
    if a.command == "status":
        if a.model is None:
            p.error("status needs --model")
        return 1 if status(a.model, a.job) else 0
    if not a.reason or not (a.beam_ends and a.model or a.layer and a.at):
        p.error("override needs --reason and either --layer with --at X Y, or --beam-ends with --model")
    return cmd_override(a)


if __name__ == "__main__":
    raise SystemExit(main())
