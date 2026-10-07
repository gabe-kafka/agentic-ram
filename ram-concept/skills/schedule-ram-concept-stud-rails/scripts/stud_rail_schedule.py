#!/usr/bin/env python3
"""Stud rail schedule rows and proposed types, from a saved, calculated RAM Concept model.

  python stud_rail_schedule.py <calculated.cpt> <rows.json> [--step 1.25] [--tight 4.0] [--prefix SR-]
  python stud_rail_schedule.py <calculated.cpt> --options

One row per stud rail set as the program designed it: column (x, y), number of rails, studs per rail, first and
typical stud spacing, rail length, slab thickness, and a comment where some rails carry fewer studs. Then a
proposed type (Mk) for every row, and the controlling row of each type. Read-only on the model.

How types are proposed (senior reviewer, 2026-10-02: by rail length in steps of about 1 to 1.5 ft, then by stud
spacing, light about 5 to 6 in and heavy about 3 to 4 in; the same length at two spacings stays two types):
  1. rows are split by number of rails, then into heavy (typical spacing under --tight) and light;
  2. from the longest rail down, rows within --step ft of it form one type;
  3. a type's controlling row is a real row: the one with the tightest spacing, when it also has the longest
     rail. When it does not, the cheapest real row with the same number of rails that covers the whole group
     is brought in to control it; with no such row the uncovered rows are split off into their own type.
     So no column gets less than the program gave it, and every type is a rail set the program designed.
This is a proposal. --options prints types against studs for several steps, for the engineer to pick from (the
same trade as bar groups against tons); then --step and --tight, or edit Mk in the workbook.

Rail length = first spacing + (studs - 1) x typical spacing. The model must hold program-designed rail sets
(DesignedBy program); a user rail set stops the script. Pass or fail is NOT in the saved file: export the
Punching Check Analysis table for the same model state (design-ram-concept-stud-rails).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "simplify-ram-concept-rebar" / "scripts"))
import cpt_reader as cr          # noqa: E402

FT, IN = 3048.0, 254.0


def pts(text):
    v = [float(x) for x in re.findall(r"\[(-?[\d.eE+]+)\]", text or "")]
    return list(zip(v[0::2], v[1::2]))


def face(dx, dy):
    return ("east" if dx > 0 else "west") if abs(dx) > abs(dy) else ("north" if dy > 0 else "south")


def rail_length(first_in, typical_in, studs):
    return (first_in + (studs - 1) * typical_in) / 12


def rows(model: Path):
    """One dict per stud rail set, as designed."""
    db = cr.connect(model)
    mesh = cr.Mesh(model)
    out = []
    query = "select LocationPoint, Point0, Point1, StudCount, StudSpacingFirst, StudSpacingTypical, RailHeight, DesignedBy from SsrSet"
    for loc, p0, p1, count, first, typical, height, by in db.execute(query):
        x, y = (v / FT for v in pts(loc)[0])
        if by != 2:
            raise SystemExit(f"({x:.0f},{y:.0f}): a user rail set; this reads the program's design only")
        studs = [int(n) for n in re.findall(r"\[(\d+)\]", count)]
        most = max(studs)
        short = {}                                # rails with fewer studs than the rest: stud count -> faces
        for (a, b), (c, d), n in zip(pts(p0), pts(p1), studs):
            if n != most:
                short.setdefault(n, set()).add(face(c - a, d - b)[0].upper())
        comment = "; ".join(f"{'/'.join(sorted(f))} RAILS: {n} STUDS" for n, f in sorted(short.items())) or " "
        first, typical = first / IN, typical / IN
        slab = mesh.thickness(x, y)
        if slab is None:                          # column centre not in a mesh element: rail height plus cover
            slab = max(float(v) for v in re.findall(r"\[(-?[\d.]+)\]", height)) / IN + 2.125
        out.append(dict(x=round(x), y=round(y), rails=len(studs), studs=most, first=first, typical=typical,
                        slab=round(slab), comment=comment, ft=rail_length(first, typical, most)))
    return out


def covers(best, r):
    return (r["rails"] == best["rails"] and r["typical"] >= best["typical"] - 1e-6 and r["first"] >= best["first"] - 1e-6
            and r["ft"] <= best["ft"] + 0.005)


def propose(found, step_ft=1.25, tight_in=4.0, prefix="SR-"):
    """Set r['mk'] on every row and r['controlling'] = 'Y' on one row per type. Returns [(controlling row, rows)]."""
    types = []                                    # [controlling row, rows]
    for rails in sorted({r["rails"] for r in found}):
        same = [r for r in found if r["rails"] == rails]
        for heavy in (True, False):               # heavy first, so a light group can borrow a heavier row
            left = [r for r in same if (r["typical"] < tight_in) == heavy]
            while left:
                top = max(r["ft"] for r in left)
                group = [r for r in left if r["ft"] >= top - step_ft - 1e-6]
                best = min(group, key=lambda r: (r["typical"], r["first"], -r["ft"]))
                if all(covers(best, r) for r in group):
                    types.append([best, group])
                else:
                    cands = [r for r in same if all(covers(r, g) for g in group)]
                    if cands:
                        c = min(cands, key=lambda r: (r["studs"], r["ft"]))
                        home = next((t for t in types if any(c is r for r in t[1])), None)
                        if home and home[0] is c:                  # it already controls a type: the group joins it
                            home[1] += [r for r in group if all(r is not h for h in home[1])]
                        else:
                            if home:
                                home[1][:] = [r for r in home[1] if r is not c]
                            types.append([c, group + ([] if any(c is r for r in group) else [c])])
                        left = [r for r in left if r is not c]
                    else:
                        while True:                                # split off what the tightest row does not cover
                            best = min(group, key=lambda r: (r["typical"], r["first"], -r["ft"]))
                            out = [r for r in group if not covers(best, r)]
                            if not out:
                                break
                            group = out
                        types.append([best, group])
                left = [r for r in left if all(r is not g for g in group)]
    types.sort(key=lambda t: (t[0]["rails"], t[0]["ft"], -t[0]["typical"]))
    for i, (best, group) in enumerate(types, 1):
        for r in group:
            r["mk"] = f"{prefix}{i}"
            r.pop("controlling", None)
    for best, _ in types:
        best["controlling"] = "Y"
    found.sort(key=lambda r: (int(r["mk"][len(prefix):]), r["ft"], r["typical"], r["y"], r["x"]))
    return [(b, g) for b, g in types]


def studs_typed(types):
    return sum(len(g) * c["rails"] * c["studs"] for c, g in types)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("model", type=Path)
    p.add_argument("rows", type=Path, nargs="?")
    p.add_argument("--options", action="store_true", help="print types against studs for several steps and stop")
    p.add_argument("--step", type=float, default=1.25, help="rail lengths within this many ft form one type (default 1.25)")
    p.add_argument("--tight", type=float, default=4.0, help="typical spacing under this, in, is a heavy type (default 4.0)")
    p.add_argument("--prefix", default="SR-")
    a = p.parse_args(argv)
    found = rows(a.model)
    designed = sum(r["rails"] * r["studs"] for r in found)
    if a.options:
        print(f"{len(found)} stud rail columns, {designed} studs as designed (heavy = typical spacing under {a.tight:g} in)")
        print("  step ft  types  studs as typed")
        for step in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
            types = propose([dict(r) for r in found], step, a.tight, a.prefix)
            typed = studs_typed(types)
            print(f"  {step:7.2f}  {len(types):5d}  {typed:6d} ({(typed / designed - 1) * 100:+.0f}%)")
        return 0
    if not a.rows:
        p.error("give <rows.json>, or --options")
    types = propose(found, a.step, a.tight, a.prefix)
    a.rows.write_text(json.dumps(found, indent=1), encoding="utf-8")
    typed = studs_typed(types)
    print(f"{len(found)} stud rail columns, {len(types)} proposed types; studs as designed {designed}, as typed {typed} ({(typed / designed - 1) * 100:+.0f}%)")
    for c, g in types:
        print(f"  {c['mk']}: {len(g):2d} columns, {c['rails']} rails, {c['studs']} studs @ {c['typical']:g} in (first {c['first']:g}), {c['ft']:.2f} ft; "
              f"as designed {min(r['ft'] for r in g):.2f} to {max(r['ft'] for r in g):.2f} ft, "
              f"{min(r['typical'] for r in g):g} to {max(r['typical'] for r in g):g} in; slab {sorted({r['slab'] for r in g})} in")
    print("rows:", a.rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
