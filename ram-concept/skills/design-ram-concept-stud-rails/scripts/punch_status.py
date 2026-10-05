#!/usr/bin/env python3
"""Classify every punching check from Concept's own results table.

  python punch_status.py <model.cpt> <Punching Check Analysis export.txt>

The saved model holds the checks and the generated stud rails, not pass or
fail. Export `Layers > Design Status > Tables > Punching Check Analysis`
(the Export... button; UTF-16 tab-separated text) from the same calculated
model, then run this. Read-only. Exit code 1 while anything is not OK.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "simplify-ram-concept-rebar" / "scripts"))
import cpt_reader as cr          # noqa: E402

FT = 3048.0


def read_table(path: Path) -> list[dict]:
    raw = Path(path).read_bytes()
    text = raw.decode("utf-16-le", "replace").lstrip("﻿") if b"\x00" in raw[:64] else raw.decode("utf-8", "replace")
    lines = [[c.strip() for c in line.split("\t")] for line in text.splitlines() if line.strip()]
    head = lines[0]
    return [dict(zip(head, line)) for line in lines[1:] if len(line) >= 6]


def checks(model: Path) -> dict[int, dict]:
    """Punching checks in the saved model, keyed by the ID the table uses (Number + 1)."""
    out = {}
    for number, point, radius, ssr in cr.connect(model).execute("select Number, Point0, MaxRadius, SsrDesignDesired from PunchCheck"):
        x, y = (float(v) / FT for v in re.findall(r"\[(-?[\d.]+)\]", point))
        out[number + 1] = dict(x=x, y=y, radius=radius / FT, ssr=bool(ssr))
    return out


def classify(model: Path, table: Path) -> dict[str, list[dict]]:
    """Checks by status: ok, ok with ssr, cutoff error, failed on stress, failed with design off."""
    by_id = defaultdict(list)
    for row in read_table(table):
        by_id[int(row["ID"])].append(row)
    out = defaultdict(list)
    for i, c in sorted(checks(model).items()):
        rows = by_id.get(i)
        if not rows:                                   # the program stopped before a result: cutoff sections
            out["cutoff error"].append(dict(c, id=i))
            continue
        column = next((r for r in rows if r["Type"] == "Column"), rows[0])
        info = dict(c, id=i, unreinforced=float(column["Max SR Unreinf. SR"]), reinforced=float(column["Max SR Reinforced SR"]))
        states = {r["Max SR Status"] for r in rows}
        if all(s.startswith("OK") for s in states):
            out["ok with ssr" if any("SSR" in s for s in states) else "ok"].append(info)
        else:
            out["failed on stress" if c["ssr"] else "failed, stud rail design off"].append(info)
    return out


NEXT = {"cutoff error": "raise the search radius: 10, then 12 ft",
        "failed on stress": "radius will not help: move the assumed opening back, or a beam",
        "failed, stud rail design off": "a column on a beam? delete the check"}


def main(argv=None) -> int:
    model, table = map(Path, (argv or sys.argv[1:])[:2])
    found = classify(model, table)
    total = sum(len(v) for v in found.values())
    print(f"{total} punching checks: " + ", ".join(f"{len(found[k])} {k}" for k in ("ok", "ok with ssr", "cutoff error", "failed on stress", "failed, stud rail design off") if found.get(k)))
    for key, action in NEXT.items():
        for c in found.get(key, []):
            ratio = f", unreinforced ratio {c['unreinforced']:g}" if "unreinforced" in c else ""
            print(f"  #{c['id']} ({c['x']:.0f},{c['y']:.0f}) radius {c['radius']:g} ft{ratio}: {key} -> {action}")
    return 1 if any(found.get(k) for k in NEXT) else 0


if __name__ == "__main__":
    raise SystemExit(main())
