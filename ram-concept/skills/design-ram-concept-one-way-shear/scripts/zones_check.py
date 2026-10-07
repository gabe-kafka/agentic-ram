#!/usr/bin/env python3
"""After the calc: for each user stirrup zone, what the program still draws on its line.

  python zones_check.py <calculated.cpt>

A user zone is good when the program draws nothing more on its line. A program region counts as "on" a user zone
when it runs the same way, lies within 1 ft across of the zone's line, and overlaps the zone's length (or sits
within 0.75 ft of an end). Regions on a beam between its ends are ignored: those are the beam's own stirrups.
Read-only. Exit code 1 when any zone still has program stirrups on it.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import shear_regions as sr      # noqa: E402


def check(path: Path):
    """(user zones, [(user zone, program regions still on it)])."""
    db = sr.cr.connect(path)
    beams = sr.segments(db, "Beam")
    user = sr.regions(db, designed_by=1)
    prog = [p for p in sr.regions(db, designed_by=2) if not sr.on_beam(beams, p["mx"], p["my"])]
    dirty = []
    for u in sorted(user, key=lambda r: (round(r["my"]), r["mx"])):
        on = [p for p in prog if p["along"] == u["along"] and abs(p["across"] - u["across"]) <= 1.0
              and p["lo"] <= u["hi"] + 0.75 and p["hi"] >= u["lo"] - 0.75]
        if on:
            dirty.append((u, on))
    return user, dirty


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    user, dirty = check(Path(argv[0]))
    print(f"{len(user)} user zones: {len(user) - len(dirty)} clean, {len(dirty)} with program stirrups still on the line")
    for u, on in dirty:
        left = "; ".join(f"{p['legs']}L @ {p['spacing']:.2f} in over {p['lo']:.1f}-{p['hi']:.1f}" for p in on)
        print(f"  ({u['mx']:5.1f},{u['my']:5.1f}) along {u['along']} {u['lo']:.1f}-{u['hi']:.1f}  user {u['legs']}L @ {u['spacing']:.0f} in: {left}")
    return 1 if dirty else 0


if __name__ == "__main__":
    raise SystemExit(main())
