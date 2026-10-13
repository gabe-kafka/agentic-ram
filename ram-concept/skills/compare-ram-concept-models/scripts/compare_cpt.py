#!/usr/bin/env python3
"""Compare two saved RAM Concept models (.cpt, or the Concept member of an .rss): what the engineer or the agent
changed between them. Read-only.

  python compare_cpt.py <A.cpt|A.rss> <B.cpt|B.rss> [--ids zone-ids.json] [--member cpt1027E] [--json out.json]

Reports, for A and B: identity (sha, size, saved), structure and strip counts, calc options, program results, and
then the user reinforcement line by line: stirrup regions (slab zones and beam regions) and bending bar groups as
only-in-A, only-in-B, changed, same. --ids maps zone lines to the engineer's Z numbers (a JSON of
"x0,y0,x1,y1": "Zn" in ft; a zone on the same line with an overlapping span keeps its number).
Exit 0 when the user reinforcement is identical, 1 when it differs.
"""
import argparse, hashlib, json, re, sqlite3, tempfile, time, zipfile
from pathlib import Path

FT, IN = 3048.0, 254.0
SET = {1: "latitude", 2: "longitude"}
nums = lambda t: [float(v) for v in re.findall(r"-?[\d.]+", t or "")]


def load(path, member):
    """(sqlite connection, label, sha12, size, saved) for a .cpt or the Concept member of an .rss."""
    if path.suffix.lower() == ".rss":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if (n.endswith("." + member) if member else re.search(r"\.cpt\d+E$", n))]
            if len(names) != 1:
                raise SystemExit(f"{path.name}: need one Concept member, found {names}; pass --member")
            data = z.read(names[0])
        tmp = Path(tempfile.gettempdir()) / f"compare-{hashlib.sha256(data).hexdigest()[:12]}.cpt"
        tmp.write_bytes(data)
        label = f"{path.name} [{names[0]}]"
    else:
        data, tmp, label = path.read_bytes(), path, path.name
    db = sqlite3.connect(f"file:{tmp.as_posix()}?immutable=1", uri=True)
    return db, label, hashlib.sha256(data).hexdigest()[:12], len(data), time.strftime("%Y-%m-%d %H:%M", time.localtime(path.stat().st_mtime))


def count(db, table, where=""):
    try:
        return db.execute(f"select count(*) from [{table}] {where}").fetchone()[0]
    except sqlite3.Error:
        return None


def summary(db):
    s = {"spans": count(db, "SpanSegment"), "strips": dict(db.execute("select StripType, count(*) from SpanSegmentStrip group by 1")),
         "strip width calc": dict(db.execute("select ColumnStripWidthCalc, count(*) from SpanSegment group by 1")),
         "strip boundaries": count(db, "StripBoundary"), "columns": count(db, "Column"), "walls": count(db, "Wall"), "beams": count(db, "Beam"),
         "slab areas": count(db, "SlabArea"), "openings": count(db, "SlabOpening"), "punch checks": count(db, "PunchCheck"), "stud rail sets": count(db, "SsrSet"),
         "rebars": sorted(n for (n,) in db.execute("select Name from Rebar")),
         "user bar groups": count(db, "ConcentratedRebar", "where DesignedBy=1"), "user mats": count(db, "DistributedRebar", "where DesignedBy=1"),
         "user stirrup regions": count(db, "TransverseRebarRegion", "where DesignedBy=1"),
         "program bar groups": count(db, "ConcentratedRebar", "where DesignedBy=2"), "program stirrup regions": count(db, "TransverseRebarRegion", "where DesignedBy=2"),
         "detailed stirrups (calc present)": count(db, "IndividualTransverseBar")}
    cols = [c[1] for c in db.execute("pragma table_info(CalcOptions)")]
    if "CheckCapacityOnly" in cols:
        s["check capacity only"] = db.execute("select CheckCapacityOnly from CalcOptions").fetchone()[0]
    return s


def stirrups(db):
    bar = dict(db.execute("select UID, Name from Rebar"))
    out = {}
    for p0, p1, sd, bt, shape, legs, sp, fixed in db.execute(
            "select Point0, Point1, SpanDirection, BarType, StirrupShape, StirrupLegs, StirrupSpacing, FixedSpacing from TransverseRebarRegion where DesignedBy=1"):
        key = tuple(round(v / FT, 2) for v in nums(p0) + nums(p1)) + (SET.get(sd, sd),)
        out[key] = dict(bar=bar.get(bt, bt), shape="open" if shape == 0 else "closed", legs=legs, spacing=round(sp / IN, 2), fixed=fixed)
    return out


def bars(db):
    bar = dict(db.execute("select UID, Name from Rebar"))
    out = {}
    for p0, p1, sd, face, bt, n, spacing in db.execute("select Point0, Point1, SpanDirection, BarFace, BarType, BarCount, BarUsesSpacing from ConcentratedRebar where DesignedBy=1"):
        key = tuple(round(v / FT, 2) for v in nums(p0) + nums(p1)) + (SET.get(sd, sd), face)
        out[key] = dict(bar=bar.get(bt, bt), count=n, by_spacing=spacing)
    return out


def zone_id(key, ids):
    x0, y0, x1, y1 = key[:4]
    along = "x" if abs(x1 - x0) >= abs(y1 - y0) else "y"
    across = (y0 + y1) / 2 if along == "x" else (x0 + x1) / 2
    lo, hi = (min(x0, x1), max(x0, x1)) if along == "x" else (min(y0, y1), max(y0, y1))
    hits = set()
    for k, v in ids.items():
        a0, b0, a1, b1 = (float(t) for t in k.split(","))
        al = "x" if abs(a1 - a0) >= abs(b1 - b0) else "y"
        ac = (b0 + b1) / 2 if al == "x" else (a0 + a1) / 2
        l2, h2 = (min(a0, a1), max(a0, a1)) if al == "x" else (min(b0, b1), max(b0, b1))
        if al == along and abs(ac - across) < 0.6 and l2 <= hi + 0.5 and h2 >= lo - 0.5:
            hits.add(v)
    return "/".join(sorted(hits, key=lambda v: int(re.sub(r"\D", "", v) or 0))) or "-"


def line(key):
    return f"({key[0]},{key[1]})-({key[2]},{key[3]}) {key[4]}" + (f" face {key[5]}" if len(key) > 5 else "")


def diff(name, a, b, fmt, ids=None):
    only_a = sorted(k for k in a if k not in b)
    only_b = sorted(k for k in b if k not in a)
    changed = sorted(k for k in a if k in b and a[k] != b[k])
    same = len(a) - len(only_a) - len(changed)
    print(f"\n{name}: A {len(a)}, B {len(b)}: {same} same, {len(changed)} changed, {len(only_a)} only in A, {len(only_b)} only in B")
    tag = (lambda k: f"{zone_id(k, ids):6s} ") if ids else (lambda k: "")
    for k in only_a:
        print(f"  A only  {tag(k)}{line(k)}  {fmt(a[k])}")
    for k in only_b:
        print(f"  B only  {tag(k)}{line(k)}  {fmt(b[k])}")
    for k in changed:
        print(f"  changed {tag(k)}{line(k)}  {fmt(a[k])}  ->  {fmt(b[k])}")
    return dict(same=same, changed=[(k, a[k], b[k]) for k in changed], only_a=[(k, a[k]) for k in only_a], only_b=[(k, b[k]) for k in only_b])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("a", type=Path)
    p.add_argument("b", type=Path)
    p.add_argument("--ids", type=Path)
    p.add_argument("--member")
    p.add_argument("--json", type=Path)
    args = p.parse_args(argv)
    ids = json.loads(args.ids.read_text(encoding="utf-8")) if args.ids else None
    (da, la, sa, za, ta), (dbb, lb, sb, zb, tb) = load(args.a, args.member), load(args.b, args.member)
    print(f"A: {la}  sha {sa}  {za} bytes  saved {ta}\nB: {lb}  sha {sb}  {zb} bytes  saved {tb}")
    if sa == sb:
        print("identical files")
        return 0
    A, B = summary(da), summary(dbb)
    print("\nsummary (A -> B where different):")
    for k in A:
        print(f"  {k:34s} {A[k]}" + ("" if A[k] == B[k] else f"  ->  {B[k]}"))
    sfmt = lambda v: f"{v['bar']} {v['shape']} {v['legs']}L @{v['spacing']:g} in" + ("" if v["fixed"] else " (free)")
    bfmt = lambda v: f"{v['count']} {v['bar']}" + (" by spacing" if v["by_spacing"] else "")
    out = {"A": dict(file=la, sha=sa), "B": dict(file=lb, sha=sb),
           "stirrups": diff("USER STIRRUP REGIONS", stirrups(da), stirrups(dbb), sfmt, ids),
           "bars": diff("USER BAR GROUPS", bars(da), bars(dbb), bfmt)}
    if args.json:
        args.json.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    differs = any(out[k][f] for k in ("stirrups", "bars") for f in ("changed", "only_a", "only_b"))
    print("\nuser reinforcement:", "DIFFERS" if differs else "identical")
    return 1 if differs else 0


if __name__ == "__main__":
    raise SystemExit(main())
