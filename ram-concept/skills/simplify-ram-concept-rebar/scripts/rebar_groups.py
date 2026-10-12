#!/usr/bin/env python3
"""Turn RAM Concept program rebar demand into a few constructible user bar groups.

Pure geometry and bookkeeping; no Concept API here. Rectangles use local axes:
``a`` runs across the bars (extent zone), ``b`` runs along them (bar length).
All lengths are feet, spacings inches, areas square inches.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

BAR_AREA = {"#3": 0.11, "#4": 0.20, "#5": 0.31, "#6": 0.44, "#7": 0.60,
            "#8": 0.79, "#9": 1.00, "#10": 1.27, "#11": 1.56}
BAR_WEIGHT = {"#3": 0.376, "#4": 0.668, "#5": 1.043, "#6": 1.502, "#7": 2.044,
              "#8": 2.670, "#9": 3.400, "#10": 4.303, "#11": 5.313}   # lb/ft
SPACINGS = (18, 12, 9, 6, 4)            # inches, loosest first


@dataclass
class Settings:
    size: str = "#7"
    spacings: tuple = SPACINGS
    max_gap_across: float = 30.0          # ft between groups that may merge
    max_gap_along: float = 3.0            # ft between bar ends that may merge
    max_length: float = 40.0              # ft longest bar
    max_class_jump: int = 1               # spacing steps two merged groups may differ by
    peak_bars: int = 2                    # demand this small ...
    peak_length: float = 5.0              # ... and this short is "peaking"
    reach: float = 3.0                    # ft a group may grow to absorb a leftover
    peak_reach: float = 5.0               # ft a group may stretch to cover a peaking bar
    development: float = 2.0              # ft extra length past an absorbed leftover


@dataclass
class Demand:
    a0: float
    a1: float
    b0: float
    b1: float
    count: int
    size: str
    tag: str = ""

    @property
    def width(self) -> float:
        return self.a1 - self.a0

    @property
    def length(self) -> float:
        return self.b1 - self.b0

    def density(self) -> float:
        """in^2 per ft across the bars; very narrow zones count as 1 ft wide."""
        return self.count * BAR_AREA[self.size] / max(self.width, 1.0)


@dataclass
class Group:
    a0: float
    a1: float
    b0: float
    b1: float
    step: int                             # index into Settings.spacings
    members: int = 1
    notes: list = field(default_factory=list)

    def spacing(self, s: Settings) -> float:
        return s.spacings[self.step]

    def bars(self, s: Settings) -> int:
        return int((self.a1 - self.a0) * 12 // self.spacing(s)) + 1

    def pounds(self, s: Settings) -> float:
        return self.bars(s) * (self.b1 - self.b0) * BAR_WEIGHT[s.size]

    def callout(self, s: Settings, face_letter: str) -> str:
        return f"({self.bars(s)}){s.size}x{self.b1 - self.b0:g}@{self.spacing(s):g}{face_letter}"


def step_for(density: float, s: Settings) -> int:
    for i, spacing in enumerate(s.spacings):
        if BAR_AREA[s.size] * 12.0 / spacing >= density - 1e-9:
            return i
    return len(s.spacings) - 1


def is_peak(d: Demand, s: Settings) -> bool:
    """Demand too small to band: peak_bars or fewer, and no longer than peak_length (0: any length)."""
    return d.count <= s.peak_bars and (s.peak_length <= 0 or d.length <= s.peak_length)


def _union(g: Group, h: Group) -> Group:
    return Group(min(g.a0, h.a0), max(g.a1, h.a1), min(g.b0, h.b0), max(g.b1, h.b1),
                 max(g.step, h.step), g.members + h.members, g.notes + h.notes)


def _gaps(g, h) -> tuple[float, float]:
    return max(g.a0, h.a0) - min(g.a1, h.a1), max(g.b0, h.b0) - min(g.b1, h.b1)


def _mergeable(g: Group, h: Group, s: Settings) -> Group | None:
    ga, gb = _gaps(g, h)
    if ga > s.max_gap_across or gb > s.max_gap_along or abs(g.step - h.step) > s.max_class_jump:
        return None
    u = _union(g, h)
    return u if u.b1 - u.b0 <= s.max_length else None


def _tidy(g: Group) -> Group:
    """Whole-foot extents for clean callouts and drafting."""
    g.a0, g.a1 = math.floor(g.a0 + 1e-6), math.ceil(g.a1 - 1e-6)
    g.b0, g.b1 = math.floor(g.b0 + 1e-6), math.ceil(g.b1 - 1e-6)
    return g


def seed(demands: list[Demand], s: Settings) -> list[Group]:
    return [_tidy(Group(d.a0, d.a1, d.b0, d.b1, step_for(d.density(), s))) for d in demands]


def merge_until(groups: list[Group], s: Settings, budget_lb: float) -> list[Group]:
    """Greedily merge the pair adding the least steel while that cost stays under budget."""
    groups = list(groups)
    while True:
        best = None
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                u = _mergeable(groups[i], groups[j], s)
                if u is None:
                    continue
                cost = u.pounds(s) - groups[i].pounds(s) - groups[j].pounds(s)
                if best is None or cost < best[0]:
                    best = (cost, i, j, u)
        if best is None or best[0] > budget_lb:
            return groups
        _, i, j, u = best
        groups = [g for k, g in enumerate(groups) if k not in (i, j)] + [u]


def options(demands: list[Demand], s: Settings, budgets: tuple = (0, 100, 250, 500, 1000, 2000, 4000, 8000)) -> list[dict]:
    """Groups-vs-tonnage trade-off: one plan per merge budget (lb of extra steel per merge)."""
    plans, groups = [], seed(demands, s)
    for budget in budgets:
        groups = merge_until(groups, s, budget)
        plan = dict(budget_lb=budget, groups=len(groups),
                    tons=round(sum(g.pounds(s) for g in groups) / 2000.0, 1),
                    plan=[asdict(g) for g in groups])
        if plans and (plans[-1]["groups"], plans[-1]["tons"]) == (plan["groups"], plan["tons"]):
            continue                      # a budget that merged nothing more: not a row of its own
        plans.append(plan)
    return plans


def pick(plans: list[dict], target_groups: int, max_tons: float) -> dict:
    """Fewest groups within the tonnage cap, preferring the count closest to target."""
    within = [p for p in plans if p["tons"] <= max_tons] or plans[:1]
    return min(within, key=lambda p: (abs(p["groups"] - target_groups), p["tons"]))


def knee(plans: list[dict], max_tons_per_group: float = 0.5) -> dict:
    """Fewest groups reachable while each step costs at most this many tons per group removed."""
    best = plans[0]
    for prev, cur in zip(plans, plans[1:]):
        removed = prev["groups"] - cur["groups"]
        if removed <= 0:
            continue
        if (cur["tons"] - prev["tons"]) / removed > max_tons_per_group:
            break
        best = cur
    return best


def absorb(groups: list[Group], leftovers: list[Demand], s: Settings) -> tuple[list[Group], list[Demand]]:
    """Grow or tighten the cheapest nearby group for each leftover; return groups and unplaced leftovers."""
    unplaced = []
    for d in leftovers:
        best = None
        for g in groups:
            ga, gb = _gaps(g, d)
            if ga > s.reach or gb > s.reach:
                continue
            need = BAR_AREA[s.size] * 12.0 / g.spacing(s) + d.density()
            step = min(max(g.step + 1, step_for(need, s)), len(s.spacings) - 1)
            grown = _tidy(Group(min(g.a0, d.a0), max(g.a1, d.a1),
                                min(g.b0, d.b0 - s.development), max(g.b1, d.b1 + s.development),
                                step, g.members, g.notes))
            extra = grown.pounds(s) - g.pounds(s)
            if best is None or extra < best[0]:
                best = (extra, g, grown)
        if best is None:
            unplaced.append(d)
            continue
        _, g, grown = best
        groups[groups.index(g)] = grown
    return groups, unplaced


def _covers(g: Group, d: Demand, tol: float = 0.1) -> bool:
    return d.a0 >= g.a0 - tol and d.a1 <= g.a1 + tol and d.b0 >= g.b0 - tol and d.b1 <= g.b1 + tol


def absorb_peaks(groups: list[Group], peaks: list[Demand], s: Settings) -> tuple[list[Group], list[Demand]]:
    """Stretch the cheapest adjacent group over each peaking bar; never tighten or add a group for a peak."""
    left = []
    for d in peaks:
        if any(_covers(g, d) for g in groups):
            d.tag = f"{d.tag} inside a group".strip()
            left.append(d)
            continue
        best = None
        for g in groups:
            ga, gb = _gaps(g, d)
            if ga > s.peak_reach or gb > s.peak_reach:
                continue
            grown = _tidy(Group(min(g.a0, d.a0), max(g.a1, d.a1),
                                min(g.b0, d.b0 - s.development), max(g.b1, d.b1 + s.development),
                                max(g.step, step_for(d.density(), s)), g.members, g.notes))
            if grown.b1 - grown.b0 > s.max_length:
                continue
            extra = grown.pounds(s) - g.pounds(s)
            if best is None or extra < best[0]:
                best = (extra, g, grown)
        if best is None:
            d.tag = f"{d.tag} no group within {s.peak_reach:g} ft".strip()
            left.append(d)
            continue
        groups[groups.index(best[1])] = best[2]
    return groups, left


def from_dict(d: dict) -> Group:
    return Group(**d)
