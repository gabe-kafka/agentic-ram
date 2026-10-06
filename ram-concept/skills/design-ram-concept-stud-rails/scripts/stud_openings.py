#!/usr/bin/env python3
"""Assumed penetration at stud rail columns: one 6 in x 6 in opening at the long face, off centre.

  python stud_openings.py list  <saved.cpt>
  python stud_openings.py add   <saved.cpt> <out.cpt> --at X Y [--at X Y ...] [--face south|north] [--toward west|east]
  python stud_openings.py move  <saved.cpt> <out.cpt> --back FT --at X Y [--at X Y ...]
  python stud_openings.py show  <saved.cpt> <out.png> --at X Y
  python stud_openings.py calc  <any.cpt> <out.cpt> [--no-mesh]  mesh, calc all, save
  python stud_openings.py compare <before.cpt> <after.cpt> [--at X Y ...]

`move` takes the assumed opening at each named column straight back from the face by FT. The saved
file must be the model that is open in the session; it is read for the columns and their openings.
`calc --no-mesh` is for changes that leave the mesh alone, such as a search radius.

Face rule: the long face. At a column with a slab edge or opening close on one long side, the
inside face (the long face away from it). Otherwise the south (or west) face.

`add` reads the columns from the saved file, draws the openings in the live API session and saves to <out.cpt>.
"""
import argparse
import math
import re
import sqlite3
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "simplify-ram-concept-rebar" / "scripts"
sys.path.insert(0, str(ENGINE))
import cpt_reader as cr          # noqa: E402

FT, IN = 3048.0, 254.0
SIZE = 6.0            # in, square
OFF_CENTRE = 4.5      # in, opening centre from the middle of the face


def pts(text):
    v = [float(x) for x in re.findall(r"\[(-?[\d.eE+]+)\]", text or "")]
    return list(zip(v[0::2], v[1::2]))


def columns(path):
    """(x ft, y ft, b in, d in, angle) for every column; b is the plan x dimension at angle 0."""
    return [(pts(p)[0][0] / FT, pts(p)[0][1] / FT, b / IN, d / IN, a)
            for p, b, d, a in cr.connect(path).execute("select Point0, B, D, Angle from Column")]


def rail_sets(path):
    """Stud rail sets as dicts: column location (ft), rails [(start, end)] in ft, studs per rail, typical spacing (in)."""
    out = []
    for p0, p1, loc, count, first, typical, by in cr.connect(path).execute(
            "select Point0, Point1, LocationPoint, StudCount, StudSpacingFirst, StudSpacingTypical, DesignedBy from SsrSet"):
        starts, ends = pts(p0), pts(p1)
        x, y = pts(loc)[0]
        out.append(dict(x=x / FT, y=y / FT, rails=[((a / FT, b / FT), (c / FT, d / FT)) for (a, b), (c, d) in zip(starts, ends)],
                        studs=[int(n) for n in re.findall(r"\[(\d+)\]", count)], first=first / IN, typical=typical / IN, by=by))
    return out


def opening(col, face="south", toward="west"):
    """Corner points (ft) of the assumed opening: touching the long face, shifted off the middle of that face."""
    x, y, b, d, angle = col
    if abs(angle) > 1e-6:
        raise SystemExit(f"column at ({x:.1f},{y:.1f}) is rotated {angle}; not handled")
    s, o = SIZE / 12, OFF_CENTRE / 12
    sign_face = -1 if face in ("south", "west") else 1
    sign_shift = -1 if toward in ("west", "south") else 1
    if b >= d:                                   # long faces are the north and south faces
        cx, y0 = x + sign_shift * o, y + sign_face * d / 24
        y1 = y0 + sign_face * s
        return [(cx - s / 2, min(y0, y1)), (cx + s / 2, min(y0, y1)), (cx + s / 2, max(y0, y1)), (cx - s / 2, max(y0, y1))]
    cy, x0 = y + sign_shift * o, x + sign_face * b / 24   # long faces are the east and west faces
    x1 = x0 + sign_face * s
    return [(min(x0, x1), cy - s / 2), (max(x0, x1), cy - s / 2), (max(x0, x1), cy + s / 2), (min(x0, x1), cy + s / 2)]


def inside_face(col, mesh, reach=10.0, step=0.25):
    """The long face away from a nearby slab edge or opening; south (or west) when neither side is close."""
    x, y, b, d, _ = col
    along_x = b >= d                              # long faces are north and south
    def clear(sign):
        dist = step
        while dist <= reach:
            px, py = (x, y + sign * dist) if along_x else (x + sign * dist, y)
            if mesh.thickness(px, py) is None:
                return dist
            dist += step
        return None
    low, high = clear(-1), clear(1)               # south / north, or west / east
    names = ("south", "north") if along_x else ("west", "east")
    if low is not None and (high is None or high > low):
        return names[1], f"edge or opening {low:g} ft to the {names[0]}"
    if high is not None:
        return names[0], f"edge or opening {high:g} ft to the {names[1]}"
    return names[0], ""


def nearest(cols, x, y):
    return min(cols, key=lambda c: math.hypot(c[0] - x, c[1] - y))


def show(path, out, at, reach=6.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x, y = at
    fig, ax = plt.subplots(figsize=(9, 9), dpi=130)
    for cx, cy, b, d, _ in columns(path):
        ax.add_patch(plt.Rectangle((cx - b / 24, cy - d / 24), b / 12, d / 12, facecolor="#444444", zorder=3))
    for s in rail_sets(path):
        for (a, b), (c, d) in s["rails"]:
            ax.plot([a, c], [b, d], color="#087f5b", lw=2.2, zorder=2)
        if math.hypot(s["x"] - x, s["y"] - y) < 1:
            ax.set_title(f"Column ({s['x']:.0f},{s['y']:.0f}): {len(s['rails'])} rails, {s['studs'][0]} studs per rail "
                         f"@ {s['typical']:g} in  ({'user' if s['by'] == 1 else 'program'})", fontsize=11)
    for (mp,) in cr.connect(path).execute("select MultiPoint from SlabOpening"):
        poly = [(a / FT, b / FT) for a, b in pts(mp)]
        ax.add_patch(plt.Polygon(poly, facecolor="#ffd43b", edgecolor="#d00000", lw=1.5, zorder=4))
    ax.set_xlim(x - reach, x + reach)
    ax.set_ylim(y - reach, y + reach)
    ax.set_aspect("equal")
    ax.grid(color="#bbbbbb", lw=0.4)
    ax.set_xlabel("x (ft)")
    ax.set_ylabel("y (ft)")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    print(out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["list", "add", "move", "show", "calc", "compare"])
    p.add_argument("model", type=Path)
    p.add_argument("out", nargs="?", type=Path)
    p.add_argument("--at", type=float, nargs=2, action="append", metavar=("X", "Y"))
    p.add_argument("--face", choices=["auto", "south", "north", "west", "east"], default="auto")
    p.add_argument("--toward", choices=["west", "east", "south", "north"], default="west")
    p.add_argument("--all", action="store_true", help="add: every column with stud rails in <saved.cpt>")
    p.add_argument("--existing", type=Path, help="add --all: skip columns that already have an opening in this saved file")
    p.add_argument("--back", type=float, help="move: distance (ft) to take the opening back from the column face")
    p.add_argument("--no-mesh", action="store_true", help="calc: keep the mesh; calc all and save")
    p.add_argument("--port", type=int)
    a = p.parse_args()
    cols = columns(a.model)
    if a.command == "list":
        sets = rail_sets(a.model)
        print(f"{len(cols)} columns, {len(sets)} with stud rails")
        for s in sorted(sets, key=lambda s: (round(s["y"]), s["x"])):
            length = (s["first"] + (max(s["studs"]) - 1) * s["typical"]) / 12
            print(f"  ({s['x']:6.1f},{s['y']:6.1f})  {len(s['rails']):2d} rails  {max(s['studs']):2d} studs @ {s['typical']:5.2f} in  rail {length:4.1f} ft")
        return
    if a.command == "show":
        show(a.model, a.out, a.at[0])
        return
    if a.command == "compare":
        before, after = rail_sets(a.model), rail_sets(a.out)
        key = lambda s: (round(s["x"]), round(s["y"]))
        describe = lambda s: (f"{len(s['rails'])} rails, {max(s['studs'])} studs @ {s['typical']:g} in, "
                              f"{(s['first'] + (max(s['studs']) - 1) * s['typical']) / 12:.1f} ft") if s else "no rails"
        old, new = {key(s): s for s in before}, {key(s): s for s in after}
        wanted = [key(dict(x=x, y=y)) for x, y in a.at] if a.at else sorted(set(old) | set(new), key=lambda k: (k[1], k[0]))
        changed = 0
        for k in wanted:
            k = min(set(old) | set(new), key=lambda q: math.hypot(q[0] - k[0], q[1] - k[1]))
            b, n = describe(old.get(k)), describe(new.get(k))
            changed += b != n
            if a.at or b != n:
                print(f"  ({k[0]},{k[1]})  {b}  ->  {n}")
        print(f"{len(before)} -> {len(after)} rail sets; {changed} changed")
        lost = [k for k in old if k not in new]
        print("lost rails:", ", ".join(f"({x},{y})" for x, y in sorted(lost, key=lambda k: (k[1], k[0]))) or "none")
        reach = lambda s: max(math.hypot(e[0] - s["x"], e[1] - s["y"]) for _, e in s["rails"])
        sets = list(new.values())
        pairs = [(s, u) for i, s in enumerate(sets) for u in sets[i + 1:]
                 if math.hypot(s["x"] - u["x"], s["y"] - u["y"]) < reach(s) + reach(u)]
        print("rails that reach into a neighbour's rails:", "; ".join(
            f"({s['x']:.0f},{s['y']:.0f}) and ({u['x']:.0f},{u['y']:.0f}): {math.hypot(s['x'] - u['x'], s['y'] - u['y']):.0f} ft apart, "
            f"reach {reach(s):.1f} + {reach(u):.1f} ft" for s, u in pairs) or "none")
        return
    if a.command == "calc":
        import time
        import simplify_rebar as sr
        model = sr.live_model(a.port)
        start = time.time()
        if not a.no_mesh:
            model._command("[GENERATE_MESH]", 1800)
        meshed = time.time() - start
        model.calc_all(timeout_seconds=3600)
        model.save_file(str(a.out))
        print(f"mesh {meshed:.0f}s, calc {time.time() - start - meshed:.0f}s; saved {a.out}")
        return
    import simplify_rebar as sr
    model = sr.live_model(a.port)                # also puts the Concept API on the path
    from ram_concept.point_2D import Point2D
    from ram_concept.polygon_2D import Polygon2D
    layer = model.cad_manager.structure_layer
    before = len(layer.slab_openings)
    if a.command == "move":
        saved = [[(x / FT, y / FT) for x, y in pts(mp)] for (mp,) in cr.connect(a.model).execute("select MultiPoint from SlabOpening")]
        saved = [q for q in saved if len(q) == 4 and max(v[0] for v in q) - min(v[0] for v in q) < 1.1 * SIZE / 12]
        mid = lambda q: (sum(v[0] for v in q) / len(q), sum(v[1] for v in q) / len(q))
        live = [(o, o.location.points) for o in layer.slab_openings]     # read every location before anything is deleted
        live = [(o, mid([(v.x, v.y) for v in q])) for o, q in live if len(q) == 4]
        moves = []
        for x, y in a.at:
            cx, cy, b, d, _ = col = nearest(cols, x, y)
            ox, oy = mid(min(saved, key=lambda q: math.hypot(mid(q)[0] - cx, mid(q)[1] - cy)))
            hit = [o for o, (lx, ly) in live if math.hypot(lx - ox, ly - oy) < 0.05]
            if math.hypot(ox - cx, oy - cy) > 3 or len(hit) != 1:
                raise SystemExit(f"column ({cx:.1f},{cy:.1f}): need one assumed opening, saved and live; nothing changed")
            dx, dy = (0.0, math.copysign(a.back, oy - cy)) if b >= d else (math.copysign(a.back, ox - cx), 0.0)
            s = SIZE / 24
            moves.append((hit[0], [(ox + dx + i * s, oy + dy + j * s) for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))]))
            print(f"column ({cx:.2f},{cy:.2f}): opening centre ({ox:.3f},{oy:.3f}) -> ({ox + dx:.3f},{oy + dy:.3f})")
        for old, poly in moves:
            old.delete()
            layer.add_slab_opening(Polygon2D([Point2D(px, py) for px, py in poly]))
        model.save_file(str(a.out))
        print(f"openings {before} -> {len(layer.slab_openings)}; saved {a.out}")
        return
    mesh = cr.Mesh(a.model)
    if a.all:
        done = []
        if a.existing:
            for (mp,) in cr.connect(a.existing).execute("select MultiPoint from SlabOpening"):
                poly = pts(mp)
                if len(poly) == 4 and max(q[0] for q in poly) - min(q[0] for q in poly) < 1.1 * SIZE * IN:
                    done.append((sum(q[0] for q in poly) / 4 / FT, sum(q[1] for q in poly) / 4 / FT))
        a.at = [(s["x"], s["y"]) for s in sorted(rail_sets(a.model), key=lambda s: (round(s["y"]), s["x"]))
                if not any(math.hypot(s["x"] - dx, s["y"] - dy) < 2.0 for dx, dy in done)]
        print(f"{len(a.at)} columns to do, {len(done)} already have an assumed opening")
    for x, y in a.at:
        col = nearest(cols, x, y)
        face, why = (a.face, "") if a.face != "auto" else inside_face(col, mesh)
        poly = opening(col, face, a.toward)
        layer.add_slab_opening(Polygon2D([Point2D(px, py) for px, py in poly]))
        print(f"column ({col[0]:.2f},{col[1]:.2f}) {col[2]:g} x {col[3]:g} in: opening on the {face} face{' (' + why + ')' if why else ''}, shifted {a.toward}: "
              + " ".join(f"({px:.3f},{py:.3f})" for px, py in poly))
    model.save_file(str(a.out))
    print(f"openings {before} -> {len(layer.slab_openings)}; saved {a.out}")


if __name__ == "__main__":
    main()
