#!/usr/bin/env python3
"""What an architect's DXF holds, read the way RAM Modeler's DXF import will read it.

  python dxf_inventory.py <floor.dxf> [--plan <out.png>]

Prints, for the engineer: the file's units and where it sits, each layer and the import role its
name says (COL -> Columns, EDGE -> Slab Edges, FLR_OPNG -> Slab Openings, GRID -> Grids; WALL is
not imported), the columns (inserts, their blocks and angles), the slab edge (open ends,
junctions, closed loops, columns it leaves outside), openings, walls and grids. --plan draws it.
Read-only. Needs ezdxf (and matplotlib for the plan).
"""
from __future__ import annotations

import argparse
import collections
import math
import re
import sys
from pathlib import Path

import ezdxf

UNITS = {0: "no units set", 1: "inches", 2: "feet", 4: "mm", 5: "cm", 6: "m"}
ROLES = [                                   # office layer names, first match wins
    (re.compile(r"FRAME.*HANG", re.I), "Frame Hanging Columns"),
    (re.compile(r"HANG", re.I), "Hanging Columns"),
    (re.compile(r"FRAME.*COL", re.I), "Frame Columns"),
    (re.compile(r"^COL(UMN)?S?$", re.I), "Columns"),
    (re.compile(r"EDGE|SLAB.?PERIM", re.I), "Slab Edges"),
    (re.compile(r"OPNG|OPEN", re.I), "Slab Openings"),
    (re.compile(r"GRID.*LABEL", re.I), "Grid Labels"),
    (re.compile(r"GRID", re.I), "Grids"),
    (re.compile(r"FRAME.*BEAM", re.I), "Frame Beams"),
    (re.compile(r"BEAM", re.I), "Beams"),
    (re.compile(r"JOIST", re.I), "Joists"),
    (re.compile(r"WALL", re.I), "walls (not imported)"),
]
TOL = 0.05                                  # inches: endpoints closer than this are one point
FAR = 2000.0                                # inches from 0,0 before the drawing counts as far off


def role_of(layer: str) -> str:
    return next((role for pattern, role in ROLES if pattern.search(layer)), "-")


def ft_in(inches: float) -> str:
    sign = "-" if inches < 0 else ""
    inches = abs(inches)
    feet, rest = divmod(round(inches * 16) / 16, 12)
    return f"{sign}{int(feet)}'-{rest:g}\"" if feet else f"{sign}{rest:g}\""


def key(point) -> tuple:
    return (round(point[0] / TOL), round(point[1] / TOL))


def segments(entities) -> list[tuple]:
    """Lines and exploded polylines as ((x, y), (x, y)) pairs; other entities are skipped."""
    out = []
    for e in entities:
        kind = e.dxftype()
        if kind == "LINE":
            out.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
        elif kind == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points()]
            pairs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if e.closed and len(pts) > 2 else [])
            out += pairs
        elif kind == "POLYLINE":
            pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
            out += list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if e.is_closed and len(pts) > 2 else [])
    return out


class Graph:
    """Endpoints and the segments meeting there."""

    def __init__(self, segs: list[tuple]):
        self.segs = [s for s in segs if math.dist(*s) > TOL]
        self.tiny = len(segs) - len(self.segs)
        self.at = collections.defaultdict(list)
        for i, (a, b) in enumerate(self.segs):
            self.at[key(a)].append(i)
            self.at[key(b)].append(i)

    def ends(self, degree) -> list[tuple]:
        return [k for k, v in self.at.items() if degree(len(v))]

    def point(self, k: tuple) -> tuple:
        return (k[0] * TOL, k[1] * TOL)

    def loops(self) -> list[list[tuple]]:
        """Connected sets of segments where every endpoint joins exactly two: closed loops."""
        seen, loops = set(), []
        for start in range(len(self.segs)):
            if start in seen:
                continue
            stack, part, ok = [start], [], True
            while stack:
                i = stack.pop()
                if i in seen:
                    continue
                seen.add(i)
                part.append(i)
                for end in self.segs[i]:
                    others = self.at[key(end)]
                    ok &= len(others) == 2
                    stack += [j for j in others if j not in seen]
            if ok and part:
                loops.append([self.segs[i] for i in part])
        return loops


def bbox(points) -> tuple | None:
    pts = list(points)
    if not pts:
        return None
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def area(loop: list[tuple]) -> float:
    """Shoelace over a loop's segments chained in order; fine for the simple loops openings are."""
    chain, used = [loop[0][0], loop[0][1]], {0}
    while len(used) < len(loop):
        nxt = next((i for i, s in enumerate(loop) if i not in used and key(s[0]) == key(chain[-1])), None)
        if nxt is None:
            nxt = next((i for i, s in enumerate(loop) if i not in used and key(s[1]) == key(chain[-1])), None)
            if nxt is None:
                return 0.0
            chain.append(loop[nxt][0])
        else:
            chain.append(loop[nxt][1])
        used.add(nxt)
    return abs(sum(chain[i][0] * chain[i + 1][1] - chain[i + 1][0] * chain[i][1] for i in range(len(chain) - 1))) / 2


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dxf", type=Path)
    p.add_argument("--plan", type=Path, help="write a PNG of the floor as the import will see it")
    a = p.parse_args()
    try:
        doc = ezdxf.readfile(a.dxf)
    except (OSError, ezdxf.DXFError) as problem:
        print(f"{a.dxf}: cannot read it as a DXF ({problem})")
        return 2
    msp = doc.modelspace()
    units = doc.header.get("$INSUNITS", 0)
    out = []
    say = out.append

    # the file
    say(f"{a.dxf.name}: {doc.dxfversion}, saved by {doc.header.get('$LASTSAVEDBY', '?')}")
    say(f"units: {UNITS.get(units, f'code {units}')}" + ("" if units == 1 else "  <- the import dialog must be told; sizes below assume inches"))
    ext = bbox([pt for s in segments(msp) for pt in s] + [(e.dxf.insert.x, e.dxf.insert.y) for e in msp.query("INSERT")])
    if ext:
        say(f"extent: x {ext[0]:.0f}..{ext[2]:.0f}, y {ext[1]:.0f}..{ext[3]:.0f} in  ({ft_in(ext[2] - ext[0])} by {ft_in(ext[3] - ext[1])})"
            + ("  <- far from 0,0 (shared coordinates); fine for RAM, but note it" if min(abs(ext[0]), abs(ext[2])) > FAR or min(abs(ext[1]), abs(ext[3])) > FAR else ""))

    # layers
    say("")
    say("layers (model space):")
    by_layer = collections.defaultdict(collections.Counter)
    for e in msp:
        by_layer[e.dxf.layer][e.dxftype()] += 1
    states = {l.dxf.name: ("off" if l.is_off() else "") + (" frozen" if l.is_frozen() else "") for l in doc.layers}
    roles = {}
    for layer in sorted(by_layer, key=lambda n: (role_of(n) == "-", n)):
        roles[layer] = role_of(layer)
        kinds = ", ".join(f"{n} {k}" for k, n in by_layer[layer].most_common())
        say(f"  {layer:24s} {roles[layer]:24s} {kinds}{('  ' + states[layer].strip()) if states.get(layer, '').strip() else ''}")
    for layer in doc.layers:
        if layer.dxf.name not in by_layer and role_of(layer.dxf.name) != "-":
            say(f"  {layer.dxf.name:24s} {role_of(layer.dxf.name):24s} empty")
    of = lambda role: [n for n, r in roles.items() if r == role]  # noqa: E731

    # columns
    say("")
    inserts = [e for n in of("Columns") for e in msp.query("INSERT") if e.dxf.layer == n]
    cols = [(e.dxf.insert.x, e.dxf.insert.y, e.dxf.rotation % 360) for e in inserts]
    if not inserts:
        say("columns: no layer named for columns, or nothing on it  <- the import needs block inserts on one layer")
    else:
        blocks = collections.Counter(e.dxf.name for e in inserts)
        say(f"columns ({', '.join(of('Columns'))}): {len(inserts)} inserts of " + "; ".join(f"{n} x {k}" for k, n in blocks.most_common()))
        scaled = sum(1 for e in inserts if abs(e.dxf.xscale - 1) > 1e-6 or abs(e.dxf.yscale - 1) > 1e-6)
        if scaled:
            say(f"  {scaled} scaled inserts (the import takes the insert point, not the drawn size)")
        angles = collections.Counter(round(c[2], 1) for c in cols)
        square = sum(n for ang, n in angles.items() if ang % 90 < 0.05 or ang % 90 > 89.95)
        odd = sorted((ang, n) for ang, n in angles.items() if not (ang % 90 < 0.05 or ang % 90 > 89.95))
        say(f"  angles: {angles.get(0.0, 0)} at 0, {sum(n for a_, n in angles.items() if a_ % 90 < 0.05 and a_ != 0)} at 90/180/270, "
            f"{len(cols) - square} at other angles" + (f" ({', '.join(f'{n} at {ang:g}' for ang, n in odd[:12])}{', ...' if len(odd) > 12 else ''})" if odd else ""))
        near = collections.defaultdict(list)
        for c in cols:
            near[key(c)].append(c[2])
        doubled = [k for k, v in near.items() if len(v) > 1]
        if doubled:
            alike = sum(1 for k in doubled if len({round(r, 1) for r in near[k]}) == 1)
            say(f"  on {len(near)} points: {len(doubled)} points carry two or more inserts ({alike} with the same angle)  "
                "<- the import makes a column for each; delete the doubles in CAD first")
        other = [e for e in msp if e.dxf.layer in of("Columns") and e.dxftype() != "INSERT"]
        if other:
            say(f"  also on the layer, ignored by the import: {', '.join(f'{n} {k}' for k, n in collections.Counter(e.dxftype() for e in other).items())}")
        cb = bbox((c[0], c[1]) for c in cols)
        say(f"  extent: x {cb[0]:.0f}..{cb[2]:.0f}, y {cb[1]:.0f}..{cb[3]:.0f} in")

    # slab edge
    say("")
    edge_layers = of("Slab Edges")
    edge = Graph(segments(e for e in msp if e.dxf.layer in edge_layers))
    if not edge.segs:
        say("slab edge: no layer named for it, or nothing on it  <- draw it in Modeler")
        eb = None
    else:
        opens = edge.ends(lambda d: d == 1)
        joins = edge.ends(lambda d: d >= 3)
        loops = edge.loops()
        say(f"slab edge ({', '.join(edge_layers)}): {len(edge.segs)} segments, {len(loops)} closed loop{'s' if len(loops) != 1 else ''}, "
            f"{len(opens)} open end{'s' if len(opens) != 1 else ''}, {len(joins)} junction{'s' if len(joins) != 1 else ''} where three or more meet"
            + (f", {edge.tiny} zero-length pieces" if edge.tiny else ""))
        if opens:
            say("  open ends at: " + "; ".join(f"({x:.0f}, {y:.0f})" for x, y in (edge.point(k) for k in opens[:16])) + (" ..." if len(opens) > 16 else ""))
        if joins:
            say("  junctions are where a balcony or bay outline sits on the main edge; the import follows lines, not faces")
        shortest = min(math.dist(*s) for s in edge.segs)
        if shortest < 1:
            say(f"  shortest segment {shortest:.2f} in")
        eb = bbox(pt for s in edge.segs for pt in s)
        say(f"  extent: x {eb[0]:.0f}..{eb[2]:.0f}, y {eb[1]:.0f}..{eb[3]:.0f} in")
        if cols:
            outside = [c for c in cols if not (eb[0] - 12 <= c[0] <= eb[2] + 12 and eb[1] - 12 <= c[1] <= eb[3] + 12)]
            if outside:
                ob = bbox((c[0], c[1]) for c in outside)
                say(f"  {len(outside)} columns lie outside the edge's extent (x {ob[0]:.0f}..{ob[2]:.0f}, y {ob[1]:.0f}..{ob[3]:.0f})  <- no slab edge there; draw it in Modeler")

    # openings
    say("")
    open_layers = of("Slab Openings")
    if open_layers:
        g = Graph(segments(e for e in msp if e.dxf.layer in open_layers))
        loops = g.loops()
        say(f"openings ({', '.join(open_layers)}): {len(g.segs)} segments, {len(loops)} closed loops"
            + (f", {len(g.ends(lambda d: d == 1))} open ends" if g.ends(lambda d: d == 1) else "")
            + (": " + ", ".join(f"{area(l) / 144:.0f} sf" for l in loops[:20]) if loops else ""))
    else:
        say("openings: none drawn")

    # walls
    say("")
    wall_layers = of("walls (not imported)")
    if wall_layers:
        g = Graph(segments(e for e in msp if e.dxf.layer in wall_layers))
        loops = g.loops()
        in_loops = {id(s) for l in loops for s in l}
        single = [s for s in g.segs if id(s) not in in_loops]
        say(f"walls ({', '.join(wall_layers)}): {len(g.segs)} segments; {len(loops)} closed outline{'s' if len(loops) != 1 else ''}"
            + (" (" + ", ".join(f"{ft_in(b[2] - b[0])} x {ft_in(b[3] - b[1])}" for b in (bbox(pt for s in l for pt in s) for l in loops[:8])) + ")" if loops else "")
            + f", {len(single)} other lines" + (" (" + ", ".join(ft_in(math.dist(*s)) for s in sorted(single, key=lambda s: -math.dist(*s))[:10]) + ")" if single else "")
            + (f"; {len(g.ends(lambda d: d >= 3))} points where outlines share a side" if g.ends(lambda d: d >= 3) else ""))
        say("  not imported: drawn by hand in Modeler on these lines")
    else:
        say("walls: none drawn")

    # grids and text
    say("")
    grid_layers = of("Grids") + of("Grid Labels")
    texts = list(msp.query("TEXT MTEXT"))
    if grid_layers:
        n = sum(1 for e in msp if e.dxf.layer in grid_layers and e.dxftype() in ("LINE", "LWPOLYLINE"))
        say(f"grids ({', '.join(grid_layers)}): {n} lines, {sum(1 for t in texts if t.dxf.layer in grid_layers)} labels")
    else:
        say("grids: none drawn")
    rest = [n for n, r in roles.items() if r == "-"]
    if rest:
        say(f"ignored by the import: {', '.join(rest)}")

    print("\n".join(out))

    if a.plan:
        draw(a.plan, cols, edge, wall_layers and Graph(segments(e for e in msp if e.dxf.layer in wall_layers)), eb)
        print(f"\nplan: {a.plan}")
    return 0


def draw(png: Path, cols, edge: Graph, walls: Graph | None, eb) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(22, 11))
    for s in edge.segs:
        ax.plot([s[0][0], s[1][0]], [s[0][1], s[1][1]], "k-", lw=0.9)
    if walls:
        for s in walls.segs:
            ax.plot([s[0][0], s[1][0]], [s[0][1], s[1][1]], "r-", lw=1.6)
    for x, y, ang in cols:
        out = eb is not None and not (eb[0] - 12 <= x <= eb[2] + 12 and eb[1] - 12 <= y <= eb[3] + 12)
        ax.plot(x, y, "o", ms=5, mfc="none" if out else "tab:blue", mec="tab:blue")
        if ang % 90 > 0.05 and ang % 90 < 89.95:
            ax.plot([x, x + 30 * math.cos(math.radians(ang))], [y, y + 30 * math.sin(math.radians(ang))], "-", color="tab:blue", lw=1)
    for k in edge.ends(lambda d: d == 1):
        ax.plot(*edge.point(k), "o", ms=9, mfc="none", mec="m", mew=1.5)
    for k in edge.ends(lambda d: d >= 3):
        ax.plot(*edge.point(k), "^", ms=7, color="g")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.set_title("edge black, walls red, columns blue (hollow: outside the edge's extent; tick: angle), open ends magenta, junctions green; inches")
    fig.savefig(png, dpi=110, bbox_inches="tight")


if __name__ == "__main__":
    sys.exit(main())
