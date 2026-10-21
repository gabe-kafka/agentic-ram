"""Parse a RAM Frame 'Member Forces' report (Reports > Member Forces > All, exported to PDF)
into per-wall, per-story JSON: wall number, story, end coordinates, length, thickness, frame
number and P / Mmajor / Mminor / Vmajor / Vminor for every load combination.

Usage: python frame_member_forces.py "Member Forces.pdf" out.json

The report prints one wall per story on two pages: CONCRETE WALL INFORMATION (with
`Column Line (x1,y1)-(x2,y2)`, the key to which wall number is where), then MEMBER FORCES.
Seen: 2612_08, RAM Frame 26, 20 walls x 10 stories = 400 pages, 2026-10-20.
"""
import json
import re
import sys

import pymupdf


def parse(path):
    recs, cur = [], None
    d = pymupdf.open(path)
    for i in range(d.page_count):
        t = d[i].get_text("text")
        m = re.search(r"Wall Number: (\d+)", t)
        if m:
            cl = re.search(r"Column Line \(([-\d.]+),([-\d.]+)\)-\(([-\d.]+),([-\d.]+)\)", t)
            cur = dict(wall=int(m.group(1)), page=i + 1,
                       top=re.search(r"Top: (.+)", t).group(1).strip(),
                       bot=re.search(r"Bot: (.+)", t).group(1).strip(),
                       x1=float(cl.group(1)), y1=float(cl.group(2)), x2=float(cl.group(3)), y2=float(cl.group(4)),
                       length=float(re.search(r"Length \(ft\) = ([\d.]+)", t).group(1)),
                       thick=float(re.search(r"Thickness \(in\) = ([\d.]+)", t).group(1)),
                       frame=int(re.search(r"Frame Number: (\d+)", t).group(1)))
            recs.append(cur)
        if "MEMBER FORCES:" in t and cur is not None:
            vals = [float(x) for x in re.findall(r"^\s*(-?[\d.]+)\s*$", t.split("MEMBER FORCES:")[1], re.M)]
            rows, k = {}, 0
            while k + 5 < len(vals) and vals[k] == len(rows) + 1:   # combinations run 1, 2, 3, ...
                rows[int(vals[k])] = dict(P=vals[k + 1], Mmaj=vals[k + 2], Mmin=vals[k + 3],
                                          Vmaj=vals[k + 4], Vmin=vals[k + 5])
                k += 6
            cur["forces"] = rows
    return recs


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    recs = parse(sys.argv[1])
    json.dump(recs, open(sys.argv[2], "w"), indent=1)
    print(len(recs), "wall-stories;", sum(1 for r in recs if r.get("forces")), "with forces")
