#!/usr/bin/env python3
"""Top bars over columns: one count-based user group per column per direction.

Pure geometry and bookkeeping; no Concept API here. Local axes follow the
engine: ``a`` runs across the bars, ``b`` along them. Lengths are feet.
"""

from __future__ import annotations

import itertools
import math
import statistics
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
    kind: str                     # "typical", "own", "beam end" or "cluster" (away from columns)
    a0: float
    a1: float
    b0: float
    b1: float
    elevation: float
    size: str
    widened: bool = False         # a column group that has already taken a stray beside its extent

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

    A bar beside the extent, within ``reach`` feet across and alongside the
    group, is taken once: the extent is widened over it and its bars added,
    and the group is marked ``widened`` (2636 building 1, 2026-10-28: the
    engineer widened 10#8 groups to 12#8 and 15#8 over the strays beside
    them). A widened group takes no second stray across: spreading column
    bars out again and again thins them where they are needed and the program
    asks for more every round (2636 building 2: 15#9 grew to 25#9). That
    second stray is the next strip's bar and is left.

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
            beside = None
            for g in out:
                across = max(g.a0 - d.a1, d.a0 - g.a1, 0.0)
                alongside = min(g.b1, d.b1) - max(g.b0, d.b0) >= 0.5 * d.length
                if (g.size == d.size and g.kind != "cluster" and not g.widened and alongside
                        and across <= reach and (beside is None or across < beside[0])):
                    beside = (across, g)
            if beside is None:
                left.append(d)
                continue
            g = beside[1]
            g.a0, g.a1 = min(g.a0, d.a0), max(g.a1, d.a1)
            g.count += d.count
            g.widened = True
            changed.add(g.column)
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


def _shared_schedule(rows: list, chosen: tuple) -> tuple[float, list]:
    """Tons and schedule of one direction under a shared count list: (tons, [(count, length, columns, kind)])."""
    weight = BAR_WEIGHT[rows[0][2]]
    longest, members, own = {}, {}, {}
    for n, length, _ in rows:
        t = next((c for c in chosen if n <= c), None)
        if t is None:
            own[(n, length)] = own.get((n, length), 0) + 1
        else:
            longest[t] = max(longest.get(t, 0), length)
            members[t] = members.get(t, 0) + 1
    schedule = [(t, longest[t], members[t], "typical") for t in sorted(longest)]
    schedule += [(n, length, k, "own") for (n, length), k in sorted(own.items())]
    pounds = sum(n * length * k for n, length, k, _ in schedule) * weight
    return pounds / 2000, schedule


def type_options_shared(by_layer: dict, most: int = 5) -> list[dict]:
    """Cheapest shared count lists: 1 to ``most`` typical counts that serve every direction at once.

    One list of counts goes on the drawings for both directions (2636
    building 1, 2026-10-28: 5, 7, 10, 15, 20 #8, picked from five priced
    rows). Each column takes the smallest listed count that covers it, and
    the largest count is always on the list, so every column is covered; a
    listed count's length is the longest demand among its columns in that
    direction, in even feet. (``typed`` with a shorter list leaves the heavy
    columns on their own count.) Rows: types, counts, tons (total), per
    direction tons and schedule.
    """
    data = {name: sorted((c.count, _feet(c.length), c.size) for c in bars) for name, bars in by_layer.items() if bars}
    counts = sorted({n for rows in data.values() for n, _, _ in rows})
    out = []
    for k in range(1, min(most, len(counts)) + 1):
        best = None
        for lower in itertools.combinations(counts[:-1], k - 1):     # the largest count is always listed: no column is left on its own
            chosen = lower + (counts[-1],)
            per = {name: _shared_schedule(rows, chosen) for name, rows in data.items()}
            total = sum(t for t, _ in per.values())
            if best is None or total < best[0] - 1e-9:
                best = (total, chosen, per)
        total, chosen, per = best
        out.append(dict(types=k, counts=list(chosen), tons=round(total, 1),
                        per={name: dict(tons=round(t, 1), schedule=sch) for name, (t, sch) in per.items()}))
    return out


def is_noise(d, lone: float = 10.0, pair: float = 7.0) -> bool:
    """A program leftover the engineer leaves alone (2636 building 1, 2026-10-28).

    A lone bar up to 10 ft, or a pair up to 7 ft: 17 such in longitude and
    14 in latitude were left standing in the finished model. A pair that is
    longer, or any three bars, gets a group; noise beside a real bar joins
    its group. Slivers at the slab edge are set aside in ``cluster_groups``.
    """
    return (d.count == 1 and d.length <= lone) or (d.count == 2 and d.length <= pair)


def _split_wide(c: dict, max_width: float) -> list[dict]:
    """A chain wider than a strip is cut at its widest gaps across until every piece fits (2636: an 8#8 and a
    20#8 group where one 32 ft chain crossed from a middle strip into the column strip)."""
    if c["a1"] - c["a0"] <= max_width or len(c["bars"]) < 2:
        return [c]
    bars = sorted(c["bars"], key=lambda d: d.a0)
    reach, cut, widest = bars[0].a1, None, 0.0
    for i in range(1, len(bars)):
        if bars[i].a0 - reach > widest:
            widest, cut = bars[i].a0 - reach, i
        reach = max(reach, bars[i].a1)
    if cut is None:
        return [c]
    pieces = []
    for part in (bars[:cut], bars[cut:]):
        pieces += _split_wide(dict(a0=min(d.a0 for d in part), a1=max(d.a1 for d in part), b0=min(d.b0 for d in part),
                                   b1=max(d.b1 for d in part), bars=part), max_width)
    return pieces


def _over_wall(c: dict, walls: list, evenness: float = 0.4) -> bool:
    """A run: a wall under the cluster running across the bars for at least half its width, with the program
    bars fairly even along it (the thinnest at least ``evenness`` of the densest). A chain that crosses a wall
    but thins out is two strips, not a run (2636: 1 and 2 bar leftovers in a middle strip chained into the
    9#8 over the column strip beside it; the engineer drew 8#8 and 20#8 there, not one run)."""
    width = c["a1"] - c["a0"]
    densities = [d.count / (d.a1 - d.a0) for d in c["bars"] if d.a1 > d.a0]
    if not densities or min(densities) < evenness * max(densities):
        return False
    for (a0, b0), (a1, b1) in walls:
        if abs(a1 - a0) < 2 * abs(b1 - b0):
            continue                                                 # runs along the bars, not across
        if not (c["b0"] - 1.0 <= (b0 + b1) / 2 <= c["b1"] + 1.0):
            continue
        if min(max(a0, a1), c["a1"]) - max(min(a0, a1), c["a0"]) >= 0.5 * width:
            return True
    return False


def standard_length(loose) -> int:
    """The one length a direction's clusters share: the commonest even-feet length of the real program bars."""
    lengths = [_feet(d.length) for d in loose if not is_noise(d)]
    return statistics.mode(sorted(lengths)) if lengths else 12


def cluster_groups(loose, typical: tuple[int, ...], standard: float, size: str, on_slab=lambda a, b: True,
                   walls: list = (), gap: float = 1.25, max_width: float = 18.0, sliver: float = 3.0) -> list[ColumnGroup]:
    """Count groups for the program top bars away from columns, the way the engineer finished 2636 building 1.

    Program bars that touch across (within ``gap`` ft) and overlap along are
    one cluster, and the group covers the cluster's footprint. A chain wider
    than a strip (``max_width``) is cut at its widest gaps, unless a wall
    runs across the bars under it: that is a run, kept whole. Count: the sum
    of the program bars when under the smallest typical count, else the
    smallest typical that covers the sum, else the sum itself; a run takes
    its densest program bar's spacing across its whole width instead (the
    engineer went heavier still on 2636: 46#8 and 31#8 over 23 ft runs,
    about 6 and 9 in, against 31 and 26 by this rule), so runs are flagged
    for him. Length: ``standard`` for the direction, centred on the cluster,
    kept on the slab like a column group. Left out: clusters made only of
    noise (``is_noise``), and slivers up to ``sliver`` ft wide with the slab
    edge beside them (2636: a 3#8 x 11' and a 2#8 x 12.5' in the 2.5 ft edge
    strip). Earlier clusters may be passed in as demands tagged "seed" (count
    and footprint): the new leftovers then grow them instead of stacking on
    top, and a seed is never dropped.
    """
    typical = tuple(sorted(typical))
    clusters = [dict(a0=d.a0, a1=d.a1, b0=d.b0, b1=d.b1, bars=[d]) for d in sorted(loose, key=lambda d: d.a0)]
    merged = True
    while merged:
        merged = False
        for i, c in enumerate(clusters):
            for j in range(i + 1, len(clusters)):
                h = clusters[j]
                if (c["a0"] <= h["a1"] + gap and h["a0"] <= c["a1"] + gap
                        and min(c["b1"], h["b1"]) - max(c["b0"], h["b0"]) > 0):
                    c.update(a0=min(c["a0"], h["a0"]), a1=max(c["a1"], h["a1"]),
                             b0=min(c["b0"], h["b0"]), b1=max(c["b1"], h["b1"]), bars=c["bars"] + h["bars"])
                    del clusters[j]
                    merged = True
                    break
            if merged:
                break
    out = []
    for c in [p for c in clusters for p in ([c] if _over_wall(c, walls) else _split_wide(c, max_width))]:
        bars = c["bars"]
        seeded = any(getattr(d, "tag", "") == "seed" for d in bars)
        if not seeded and all(is_noise(d) for d in bars):
            continue
        total = sum(d.count for d in bars)
        width = c["a1"] - c["a0"]
        mid_a, mid_b = (c["a0"] + c["a1"]) / 2, (c["b0"] + c["b1"]) / 2
        if (not seeded and width <= sliver
                and not (on_slab(c["a0"] - 0.5, mid_b) and on_slab(c["a1"] + 0.5, mid_b))):
            continue                                                 # an edge strip
        if _over_wall(c, walls):
            density = max(d.count / (d.a1 - d.a0) for d in bars if d.a1 > d.a0)
            count = math.ceil(density * width - 1e-9)
        elif typical and total >= typical[0]:
            count = next((t for t in typical if total <= t), total)
        else:
            count = total
        b0, b1 = mid_b - standard / 2, mid_b + standard / 2
        if not on_slab(mid_a, b0):
            b0, b1 = c["b0"], c["b0"] + standard
        if not on_slab(mid_a, b1):
            b1 = c["b1"]
            b0 = max(b1 - standard, b0) if on_slab(mid_a, b1 - standard) else c["b0"]
        elevation = statistics.mode(sorted(round(getattr(d, "elevation", 0.0), 3) for d in bars))
        out.append(ColumnGroup(-1, count, round(b1 - b0, 2), "cluster", c["a0"], c["a1"], b0, b1, elevation, size))
    return out


def typed(bars: list[ColumnBars], typical: tuple[int, ...], on_slab=lambda a, b: True,
          beam_ends: frozenset = frozenset(), own: frozenset = frozenset(),
          widened: frozenset = frozenset()) -> list[ColumnGroup]:
    """One group per column: the smallest typical count that covers it, else its own count.

    A typical callout's length is the longest demand among its columns, in
    even whole feet like every other length. Bars
    stay centred on the program bars; where that would run off the slab the
    bar keeps the program bar's end on that side. Columns in ``beam_ends``
    keep their own count and length (kind "beam end") and do not stretch the
    typical callouts; neither do columns in ``own`` (kind "own"). Columns in
    ``widened`` keep their widened flag (see ``capture``).
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
                                  c.a0, c.a1, b0, b1, c.elevation, c.size, c.column in widened))
    return groups


def schedule(groups: list[ColumnGroup]) -> list[tuple[str, int]]:
    """Callouts with how many use each: typical first, then own counts, beam ends, then the clusters away from columns."""
    order = {"typical": 0, "own": 1, "beam end": 2, "cluster": 3}
    seen: dict[tuple, int] = {}
    for g in groups:
        key = (order[g.kind], g.count, g.length, g.size)
        seen[key] = seen.get(key, 0) + 1
    return [(f"{n}{size} x {length:g}'" + {2: " (beam end)", 3: " (away from columns)"}.get(rank, ""), k)
            for (rank, n, length, size), k in sorted(seen.items())]
