#!/usr/bin/env python3
"""Read-only access to a saved RAM Concept .cpt (SQLite) for rebar simplification.

Opens the file immutable; never writes. Internal lengths are 0.1 mm.
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from rebar_groups import Demand

FT = 3048.0          # internal units per foot
IN = 254.0           # internal units per inch
BAR_SIZES = {24: "#3", 25: "#4", 26: "#5", 27: "#6", 28: "#7", 29: "#8", 30: "#9", 31: "#10", 32: "#11"}
FACE = {"top": 1, "bottom": 2}
DIRECTION = {"lat": 1, "long": 2}
USER, PROGRAM = 1, 2


@dataclass(frozen=True)
class Layer:
    """One face + direction, e.g. Layer.parse('bot-long')."""
    face: str
    direction: str

    @staticmethod
    def parse(text: str) -> "Layer":
        face, direction = text.lower().split("-")
        face = {"bot": "bottom", "bottom": "bottom", "top": "top"}[face]
        if direction not in DIRECTION:
            raise ValueError(f"direction must be lat or long: {text}")
        return Layer(face, direction)

    @property
    def name(self) -> str:
        return f"{'bot' if self.face == 'bottom' else 'top'}-{self.direction}"

    @property
    def letter(self) -> str:
        return "T" if self.face == "top" else "B"

    def to_local(self, x: float, y: float) -> tuple[float, float]:
        """(across, along): longitude bars run in plan y, latitude bars in plan x."""
        return (x, y) if self.direction == "long" else (y, x)

    def to_plan(self, a: float, b: float) -> tuple[float, float]:
        return (a, b) if self.direction == "long" else (b, a)


def _points(text: str | None) -> list[tuple[float, float]]:
    v = [float(t) / FT for t in re.findall(r"-?[\d.]+", text or "")]
    return list(zip(v[0::2], v[1::2]))


def connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(path).as_posix()}?immutable=1", uri=True)


def bars(path: Path, layer: Layer, designed_by: int) -> list[Demand]:
    out = []
    rows = connect(path).execute(
        "select BarType, Point0, Point1, LeftPoint, RightPoint, BarCount, AbsoluteElevation, BarEnd0, BarEnd1, "
        "BarUsesSpacing from ConcentratedRebar where SpanDirection=? and BarFace=? and DesignedBy=?",
        (DIRECTION[layer.direction], FACE[layer.face], designed_by))
    for bar_type, p0, p1, lp, rp, count, elevation, end0, end1, uses_spacing in rows:
        (s0, s1), (l, r) = _points(p0 + p1), _points(lp + rp)
        a = sorted((layer.to_local(*l)[0], layer.to_local(*r)[0]))
        b = sorted((layer.to_local(*s0)[1], layer.to_local(*s1)[1]))
        d = Demand(a[0], a[1], b[0], b[1], count, BAR_SIZES[bar_type])
        d.elevation = elevation / IN
        d.by_count = not uses_spacing
        # end condition codes (1 straight, 2 hook 90, 3 hook 180, 4 anchored) at the low-b and high-b ends
        d.ends = (end0, end1) if layer.to_local(*s0)[1] <= layer.to_local(*s1)[1] else (end1, end0)
        out.append(d)
    return out


def stacks(bars: list, tol: float = 0.3) -> list[list]:
    """Groups of bars drawn on top of each other: same footprint (within tol ft), count, size and depth.

    Identical copies are never meant (2636 building 1, 2026-10-28: eight top groups four deep). Returns one
    list per stack, two or more bars each, in the order read.
    """
    out = []
    for d in bars:
        key = (d.count, d.size, round(getattr(d, "elevation", 0.0), 2), getattr(d, "by_count", True))
        for stack in out:
            s = stack[0]
            same = (s.count, s.size, round(getattr(s, "elevation", 0.0), 2), getattr(s, "by_count", True)) == key
            if same and all(abs(u - v) <= tol for u, v in zip((s.a0, s.a1, s.b0, s.b1), (d.a0, d.a1, d.b0, d.b1))):
                stack.append(d)
                break
        else:
            out.append([d])
    return [stack for stack in out if len(stack) > 1]


def walls(path: Path, layer: Layer) -> list:
    """Wall centrelines of a saved model in the layer's local feet: ((a0, b0), (a1, b1))."""
    out = []
    for p0, p1 in connect(path).execute("select Point0, Point1 from Wall"):
        (x0, y0), (x1, y1) = _points(p0)[0], _points(p1)[0]
        out.append((layer.to_local(x0, y0), layer.to_local(x1, y1)))
    return out


class Mesh:
    """Slab thickness (in) from saved mesh elements: what Concept designs with."""
    CELL = 5.0

    def __init__(self, path: Path):
        c = connect(path)
        self.elements = []
        for table, n in (("QuadSlabElement", 4), ("TriSlabElement", 3)):
            cols = ", ".join(f"CornerNode{i}" for i in range(n))
            for row in c.execute(f"select SlabThickness, {cols} from {table}"):
                self.elements.append((round(row[0] / IN, 1), [_points(p)[0] for p in row[1:]]))
        self.grid = defaultdict(list)
        for i, (_, poly) in enumerate(self.elements):
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            for gx in range(int(min(xs) // self.CELL), int(max(xs) // self.CELL) + 1):
                for gy in range(int(min(ys) // self.CELL), int(max(ys) // self.CELL) + 1):
                    self.grid[(gx, gy)].append(i)
        self.openings = [_points(mp) for (mp,) in c.execute("select MultiPoint from SlabOpening")]

    def thickness(self, x: float, y: float) -> float | None:
        for i in self.grid.get((int(x // self.CELL), int(y // self.CELL)), ()):
            th, poly = self.elements[i]
            if inside(x, y, poly):
                return th
        return None

    def thinnest(self, layer: Layer, a0: float, a1: float, b0: float, b1: float, n: int = 16) -> float | None:
        found = {self.thickness(*layer.to_plan(a0 + (a1 - a0) * i / n, b0 + (b1 - b0) * j / n))
                 for i in range(n + 1) for j in range(n + 1)} - {None}
        return min(found) if found else None

    def near_opening(self, x: float, y: float, reach: float = 3.0) -> bool:
        for poly in self.openings:
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            if min(xs) - reach <= x <= max(xs) + reach and min(ys) - reach <= y <= max(ys) + reach:
                return True
        return self.thickness(x, y) is None


def beam_rects(path: Path, layer: Layer) -> list[tuple[float, float, float, float]]:
    """Concrete beams that run along this layer's bars, as (a0, a1, b0, b1) in the layer's local axes."""
    out = []
    for p0, p1, width in connect(path).execute("select Point0, Point1, Width from Beam"):
        (x0, y0), (x1, y1) = _points(p0 + p1)
        (a0, b0), (a1, b1) = layer.to_local(x0, y0), layer.to_local(x1, y1)
        if abs(b1 - b0) > abs(a1 - a0):
            mid, half = (a0 + a1) / 2, width / FT / 2
            out.append((mid - half, mid + half, min(b0, b1), max(b0, b1)))
    return out


def inside(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    ok, j = False, len(poly) - 1
    for i in range(len(poly)):
        (xi, yi), (xj, yj) = poly[i], poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            ok = not ok
        j = i
    return ok


def depth_rule(path: Path, layer: Layer, mesh: Mesh) -> dict[float, float]:
    """Bar elevation (in) Concept uses for each 'thinnest slab under the group' thickness.

    Learned from the program bars, so it follows the model's cover and bar size.
    """
    votes = defaultdict(Counter)
    for d in bars(path, layer, PROGRAM):
        th = mesh.thinnest(layer, d.a0, d.a1, d.b0, d.b1, n=8)
        if th is not None:
            votes[th][round(d.elevation, 3)] += 1
    return {th: c.most_common(1)[0][0] for th, c in votes.items()}


def dominant_size(demands: list[Demand]) -> str:
    return Counter(d.size for d in demands).most_common(1)[0][0]
