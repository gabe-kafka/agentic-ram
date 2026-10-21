"""Compare RAM Frame 'Drift' reports (drift at control points, Load Combinations mode).

Usage: python frame_drift_compare.py BASE.pdf RUN.pdf [RUN2.pdf ...] [--story-height 126]

Expects the 2612_08 drift combinations: combos 1-4 = 1.0E (limit 0.020/Cd, 0.0050 for Cd 4),
5-16 = 0.6W (office limit h/600). Story drift / story height gives the ratio to more places
than RAM prints. Torsion is max/avg story drift of the two extreme control points per direction:
the points are found as the extremes in Y (for X loading) and in X (for Y loading).
Seen: 2612_08 wall removal study, 2026-10-21 (baseline reproduces RAM's own torsion table).
"""
import re
import sys

import pymupdf

NUM = re.compile(r"^-?\d+\.\d+$")


def parse(path, h_in):
    """Rows (point, level, combo, |drift X| in, |drift Y| in, ratio X, ratio Y)."""
    rows, point, level = [], None, None
    for page in pymupdf.open(path):
        lines = {}
        for w in page.get_text("words"):
            lines.setdefault(round(w[3]), []).append(w)
        for k in sorted(lines):
            t = [w[4] for w in sorted(lines[k], key=lambda w: w[0])]
            m = re.search(r"Location \(ft\): \(([\d.]+), ([\d.]+)\)", " ".join(t))
            if m:
                point = (float(m.group(1)), float(m.group(2)))
                continue
            if t[:1] == ["Level"] and len(t) >= 2 and t[1].isdigit():
                level, t = int(t[1]), t[2:]
            if point and level and len(t) == 7 and t[0].isdigit() and all(NUM.match(x) for x in t[1:]):
                dx, dy = abs(float(t[3])), abs(float(t[4]))
                rows.append((point, level, int(t[0]), dx, dy, dx / h_in, dy / h_in))
    return rows


def worst(rows, combos, i):
    r = max((r for r in rows if r[2] in combos), key=lambda r: r[i])
    return r[i], r[0], r[1]


def torsion(rows, combos, i, pts):
    out = []
    for lv in sorted({r[1] for r in rows}):
        best = 0
        for c in combos:
            v = [next(r[i] for r in rows if r[1] == lv and r[2] == c and r[0] == p) for p in pts]
            best = max(best, max(v) / (sum(v) / 2))
        out.append(best)
    return out


def main(argv):
    h = 126.0
    if "--story-height" in argv:
        k = argv.index("--story-height")
        h = float(argv[k + 1])
        argv = argv[:k] + argv[k + 2:]
    E, W = range(1, 5), range(5, 17)
    for path in argv:
        rows = parse(path, h)
        pts = sorted({r[0] for r in rows})
        ys, xs = sorted(pts, key=lambda p: p[1]), sorted(pts, key=lambda p: p[0])
        cells = []
        for combos, lim in ((E, 0.005), (W, 1 / 600)):
            for i in (5, 6):
                v, p, lv = worst(rows, combos, i)
                tag = f"h/{1 / v:.0f}" if combos == W else f"{v:.5f}"
                cells.append(f"{tag} {v / lim:4.0%} {p} L{lv}")
        tx = torsion(rows, (1, 2), 3, [ys[0], ys[-1]])
        ty = torsion(rows, (3, 4), 4, [xs[0], xs[-1]])
        print(path.replace("\\", "/").split("/")[-1])
        print("  1.0E X | 1.0E Y | 0.6W X | 0.6W Y:  " + " | ".join(cells))
        print("  torsion X: " + " ".join(f"{v:.2f}" for v in tx) + "   Y: " + " ".join(f"{v:.2f}" for v in ty))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
