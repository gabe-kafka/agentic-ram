#!/usr/bin/env python3
"""Top bars over columns: one count-based user group per column per direction.

Pure geometry and bookkeeping; no Concept API here. Local axes follow the
engine: ``a`` runs across the bars, ``b`` along them. Lengths are feet.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, replace

BAR_WEIGHT = {"#3": 0.376, "#4": 0.668, "#5": 1.043, "#6": 1.502, "#7": 2.044,
              "#8": 2.670, "#9": 3.400, "#10": 4.303, "#11": 5.313}   # lb/ft


@dataclass
class ColumnBars:
    """Program top demand gathered over one column, in one direction."""
    column: int
    a: float                      # column position, local axes
    b: float
    count: int
    a0: float
    a1: float
    b0: float
    b1: float
    elevation: float
    size: str

    @property
    def length(self) -> float:
        return self.b1 - self.b0


@dataclass
class ColumnGroup:
    """The user group to draw over one column."""
    column: int
    count: int
    length: float
    kind: str                     # "typical", "own" or "beam end"
    a0: float
    a1: float
    b0: float
    b1: float
    elevation: float
    size: str

    def callout(self) -> str:
        return f"{self.count}{self.size} x {self.length:g}'"

    def pounds(self) -> float:
        return self.count * self.length * BAR_WEIGHT[self.size]


def assign(demands, columns, reach: float = 2.0):
    """Give each demand to the column under it. Returns (per-column bars, demands over no column).

    The largest group at a column sets where the bars go. A second group adds
    to it only when at least half its length lies alongside; a stray bar
    further along the span stays loose. Stretching the heavy column bars out
    to reach it puts far more top steel along the span than the program asked
    for (on 2636 the program then demanded 32#7 in the bottom of a beam).
    """
    found: dict[int, ColumnBars] = {}
    loose = []
    for d in sorted(demands, key=lambda d: -d.count):
        under = [i for i, (a, b) in enumerate(columns)
                 if d.a0 - reach <= a <= d.a1 + reach and d.b0 - reach <= b <= d.b1 + reach]
        if not under:
            loose.append(d)
            continue
        ca, cb = (d.a0 + d.a1) / 2, (d.b0 + d.b1) / 2
        i = min(under, key=lambda i: math.hypot(columns[i][0] - ca, columns[i][1] - cb))
        if i in found:
            f = found[i]
            if min(f.b1, d.b1) - max(f.b0, d.b0) < 0.5 * d.length:
                loose.append(d)
                continue
            f.count += d.count
            f.a0, f.a1, f.b0, f.b1 = min(f.a0, d.a0), max(f.a1, d.a1), min(f.b0, d.b0), max(f.b1, d.b1)
        else:
            found[i] = ColumnBars(i, columns[i][0], columns[i][1], d.count, d.a0, d.a1, d.b0, d.b1,
                                  getattr(d, "elevation", 0.0), d.size)
    return sorted(found.values(), key=lambda c: c.column), loose


def capture(groups: list[ColumnGroup], strays, reach: float = 5.0):
    """Fold the program bars left beside a column group into that group.

    A stray belongs to a group only when it sits in that group's own strip:
    at least half its width inside the group's extent. Alongside the group
    (half its length or more) its bars add to the count; past the end of the
    group, within ``reach`` feet, the group is lengthened to reach it.

    The extent is never widened. A bar beside the extent is the next strip's
    bar; spreading the column bars out to it thins them where they are needed
    and the program asks for more every round (2636: 15#9 grew to 25#9).

    Returns the groups, the columns that changed, the columns that were
    lengthened, and the strays no group could take. Pass the changed groups
    back through ``typed`` so a typical group that now needs more moves up to
    the next typical count.
    """
    out = [replace(g) for g in groups]
    changed, longer, left = set(), set(), []
    for d in strays:
        best = None
        for g in out:
            inside = min(g.a1, d.a1) - max(g.a0, d.a0)
            along = max(g.b0 - d.b1, d.b0 - g.b1, 0.0)
            if (g.size == d.size and inside >= 0.5 * (d.a1 - d.a0) and along <= reach
                    and (best is None or along < best[0])):
                best = (along, g)
        if best is None:
            left.append(d)
            continue
        g = best[1]
        if min(g.b1, d.b1) - max(g.b0, d.b0) >= 0.5 * d.length:
            g.count += d.count
        else:
            g.b0, g.b1 = min(g.b0, d.b0), max(g.b1, d.b1)
            longer.add(g.column)
        g.length = round(g.b1 - g.b0, 2)
        changed.add(g.column)
    return out, changed, longer, left


def _feet(length: float) -> int:
    """The callout length: even whole feet, rounding up (office rule). An inch or so over does not earn more."""
    whole = math.ceil(length - 0.1)
    return whole + whole % 2


def tons(groups) -> float:
    return sum(g.pounds() for g in groups) / 2000.0


def type_options(bars: list[ColumnBars], most: int = 4) -> list[dict]:
    """Cheapest schedule using 1..most callouts that covers every column (count and length)."""
    data = sorted((c.count, _feet(c.length)) for c in bars)
    weight = BAR_WEIGHT[bars[0].size]
    out = []
    for k in range(1, min(most, len(data)) + 1):
        best = None
        for cuts in itertools.combinations(range(1, len(data)), k - 1):
            edges = (0,) + cuts + (len(data),)
            parts = [data[i:j] for i, j in zip(edges, edges[1:])]
            cost = sum(max(n for n, _ in p) * max(l for _, l in p) * len(p) for p in parts) * weight / 2000
            if best is None or cost < best[0]:
                best = (cost, parts)
        out.append(dict(types=k, tons=round(best[0], 1),
                        schedule=[(max(n for n, _ in p), max(l for _, l in p), len(p)) for p in best[1]]))
    return out


def typed(bars: list[ColumnBars], typical: tuple[int, ...], on_slab=lambda a, b: True,
          beam_ends: frozenset = frozenset(), own: frozenset = frozenset()) -> list[ColumnGroup]:
    """One group per column: the smallest typical count that covers it, else its own count.

    A typical callout's length is the longest demand among its columns, in
    even whole feet like every other length. Bars
    stay centred on the program bars; where that would run off the slab the
    bar keeps the program bar's end on that side. Columns in ``beam_ends``
    keep their own count and length (kind "beam end") and do not stretch the
    typical callouts; neither do columns in ``own`` (kind "own").
    """
    typical = tuple(sorted(typical))
    apart = beam_ends | own
    kind_of = lambda c: None if c.column in apart else next((t for t in typical if c.count <= t), None)
    longest = {t: max((_feet(c.length) for c in bars if kind_of(c) == t), default=0) for t in typical}
    groups = []
    for c in bars:
        t = kind_of(c)
        count, length = (t, longest[t]) if t else (c.count, _feet(c.length))
        mid_a, mid_b = (c.a0 + c.a1) / 2, (c.b0 + c.b1) / 2
        b0, b1 = mid_b - length / 2, mid_b + length / 2
        if not on_slab(mid_a, b0):
            b0, b1 = c.b0, c.b0 + length
        if not on_slab(mid_a, b1):
            b1 = c.b1
            b0 = max(b1 - length, b0) if on_slab(mid_a, b1 - length) else c.b0
        kind = "typical" if t else ("beam end" if c.column in beam_ends else "own")
        groups.append(ColumnGroup(c.column, count, round(b1 - b0, 2), kind,
                                  c.a0, c.a1, b0, b1, c.elevation, c.size))
    return groups


def schedule(groups: list[ColumnGroup]) -> list[tuple[str, int]]:
    """Callouts with how many columns use each: typical first, then own counts, then beam ends."""
    order = {"typical": 0, "own": 1, "beam end": 2}
    seen: dict[tuple, int] = {}
    for g in groups:
        key = (order[g.kind], g.count, g.length, g.size)
        seen[key] = seen.get(key, 0) + 1
    return [(f"{n}{size} x {length:g}'" + (" (beam end)" if rank == 2 else ""), k)
            for (rank, n, length, size), k in sorted(seen.items())]
