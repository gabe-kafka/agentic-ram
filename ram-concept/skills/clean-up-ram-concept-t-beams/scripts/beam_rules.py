#!/usr/bin/env python3
"""What a concrete beam changes for slab rebar, and the job's record of overrides.

  top bars, beam runs through the column    no top bar called out; the beam carries the moment
  top bars, beam ends at the column         the column keeps its own count and length
  bottom bars inside the beam, mid-span     the beam's own bars: by count, never banded
  bottom bars inside the beam, at its end   the engineer's call; never added automatically

Pure geometry and bookkeeping; no Concept API and no model reads here. Lengths
are feet. ``a`` runs across the bars, ``b`` along them.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path


# ---------------------------------------------------------------- top bars at beam columns

def beam_sides(column, axis, beams, reach: float = 3.0, tol: float = 1.0) -> int:
    """How many sides of the column (0, 1 or 2) have a beam parallel to the bars.

    ``column`` and ``beams`` (start, end, width) are plan coordinates; ``axis``
    is the bar direction as a unit vector.

    2: the beam runs through. No additional slab top bars in that direction;
       the beam's own top steel carries it.
    1: the beam ends at the column. The slab on the far side takes the
       beam's end moment on a much smaller depth, so the bars are needed and
       are heavier and longer than at a slab column.
    """
    x, y = column
    ux, uy = axis

    def on_beam(px, py):
        for (a, b), (c, d), width in beams:
            run = math.hypot(c - a, d - b)
            if not run or abs(ux * (c - a) + uy * (d - b)) / run < 0.95:
                continue
            s = ((px - a) * (c - a) + (py - b) * (d - b)) / run ** 2
            off = math.hypot(px - a - s * (c - a), py - b - s * (d - b))
            if 0.0 <= s <= 1.0 and off <= width / 2 + tol:
                return True
        return False

    return int(on_beam(x + ux * reach, y + uy * reach)) + int(on_beam(x - ux * reach, y - uy * reach))


def beam_runs_through(column, axis, beams, reach: float = 3.0, tol: float = 1.0) -> bool:
    """True when a beam parallel to the bars continues past the column on both sides."""
    return beam_sides(column, axis, beams, reach, tol) == 2


def beam_columns(columns, beams, direction: str) -> dict[int, int]:
    """Columns on a beam parallel to the bars: 2 = beam runs through, 1 = beam ends there."""
    axis = (0.0, 1.0) if direction == "long" else (1.0, 0.0)
    sides = {i: beam_sides(c, axis, beams) for i, c in enumerate(columns)}
    return {i: n for i, n in sides.items() if n}


# ---------------------------------------------------------------- bottom bars inside a beam

def in_beam(d, beams: list, tol: float = 0.75) -> bool:
    """True when a bar group sits inside a beam's width and runs along it.

    ``beams`` are (a0, a1, b0, b1) rectangles in the same local axes. These are
    the beam's own bars: few, by count, at the beam's depth. They are never
    banded with slab bars.
    """
    for a0, a1, b0, b1 in beams:
        along = min(d.b1, b1) - max(d.b0, b0)
        if d.a0 >= a0 - tol and d.a1 <= a1 + tol and along >= 0.5 * d.length:
            return True
    return False


def beam_group(d) -> dict:
    """A beam bar group to draw: the program's count and depth, whole-foot length about the same centre."""
    length = math.ceil(d.length - 0.1)
    mid = (d.b0 + d.b1) / 2
    return dict(a0=d.a0, a1=d.a1, b0=mid - length / 2, b1=mid + length / 2, count=d.count, size=d.size,
                elevation=getattr(d, "elevation", 0.0), ends=list(getattr(d, "ends", (1, 1))))


def at_beam_end(d, beams: list, tol: float = 1.0) -> bool:
    """True when a bar inside a beam reaches the end of that beam.

    Bottom bars there are not span steel. They balance the heavy top bars
    over the end column, so they are the engineer's call. A bar that stops
    short of both ends is mid-span steel and belongs to the beam's own bars.
    """
    return any(in_beam(d, [r]) and (d.b0 <= r[2] + tol or d.b1 >= r[3] - tol) for r in beams)


def grow_beam_groups(groups: list[dict], short: list, beams: list) -> list[dict]:
    """Add what the program still asks for at mid-span to the beam's own bars.

    A leftover is extra to the bars already drawn, so its count adds to the
    group in the same beam and the group stretches to cover it. A beam with
    no group yet, or bars of another size, gets a new group.
    """
    out = [dict(g) for g in groups]
    for d in short:
        rect = next((r for r in beams if in_beam(d, [r])), None)
        home = next((g for g in out if rect and g["size"] == d.size and rect[0] - 0.75 <= (g["a0"] + g["a1"]) / 2 <= rect[1] + 0.75
                     and min(g["b1"], rect[3]) > max(g["b0"], rect[2])), None)
        if home is None:
            out.append(beam_group(d))
            continue
        b0, b1 = min(home["b0"], d.b0), max(home["b1"], d.b1)
        length, mid = math.ceil(b1 - b0 - 0.1), (b0 + b1) / 2
        home.update(count=home["count"] + d.count, b0=mid - length / 2, b1=mid + length / 2,
                    a0=min(home["a0"], d.a0), a1=max(home["a1"], d.a1))
    return out


# ---------------------------------------------------------------- overrides: "no bar called out here"

def decisions_file(job: Path) -> Path:
    """The job's record of decisions: one file in the folder that holds the work folders."""
    return Path(job) / "decisions.json"


def overrides(job: Path, layer: str) -> list[dict]:
    path = decisions_file(job)
    if not path.exists():
        return []
    return [o for o in json.loads(path.read_text()).get("overrides", []) if o["layer"] == layer]


def add_override(job: Path, layer: str, x: float, y: float, reason: str, source: str, reach: float = 6.0) -> bool:
    """Record "no bar called out here" at a plan location. Returns False when it is already recorded."""
    path = decisions_file(job)
    data = json.loads(path.read_text()) if path.exists() else {"overrides": []}
    if any(o["layer"] == layer and math.hypot(o["x"] - x, o["y"] - y) < 1.0 for o in data["overrides"]):
        return False
    data["overrides"].append(dict(layer=layer, x=round(x, 1), y=round(y, 1), reach=reach, callout="none",
                                  reason=reason, source=source, date=time.strftime("%Y-%m-%d")))
    path.write_text(json.dumps(data, indent=1))
    return True


def override_at(found: list[dict], x: float, y: float) -> dict | None:
    """The override that covers a plan point, if any."""
    return next((o for o in found if math.hypot(o["x"] - x, o["y"] - y) <= o["reach"]), None)
