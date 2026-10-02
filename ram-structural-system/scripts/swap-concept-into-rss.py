#!/usr/bin/env python3
"""Build a separately named RSS copy whose embedded RAM Concept model is replaced by a given .cpt.

  python swap-concept-into-rss.py <source.rss> <new.cpt> <output.rss> [member suffix, e.g. cpt1027E]

The .rss is a zip; the elevated slab's Concept file is the member ending
.cpt<story>E (the mat is ...M). Never writes the source RSS, refuses to
overwrite an existing output, and checks the .cpt opens as SQLite and has no
journal beside it. Same rewrite pattern as merge-ram-line-load-properties.

Opened cleanly in RAM Manager on one job (2636) four times. RAM Manager must
be closed on the production model before the output replaces it; archive the
old file first.
"""
import hashlib, sqlite3, sys, zipfile
from pathlib import Path

src, cpt, out = map(Path, sys.argv[1:4])
suffix = sys.argv[4] if len(sys.argv) > 4 else None
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
if out.resolve() == src.resolve() or out.exists():
    raise SystemExit("output must be a new file")
if any(Path(str(cpt) + ext).exists() for ext in ("-journal", "-wal")):
    raise SystemExit("cpt has a journal/wal beside it; save and close it first")
db = sqlite3.connect(f"file:{cpt}?mode=ro", uri=True)
if db.execute("pragma integrity_check").fetchone()[0] != "ok":
    raise SystemExit("cpt failed sqlite integrity_check")
db.close()
before = sha(src)
with zipfile.ZipFile(src) as a:
    infos = a.infolist()
    members = [i for i in infos if (i.filename.endswith("." + suffix) if suffix else ".cpt" in i.filename and i.filename[-1] in "EM")]
    if len(members) != 1:
        raise SystemExit(f"need exactly one Concept member, found {[i.filename for i in members]}; pass the suffix")
    target = members[0]
    if a.read(target)[:15] != b"SQLite format 3":
        raise SystemExit("target member is not a Concept SQLite file")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = cpt.read_bytes()
    with zipfile.ZipFile(out, "w") as o:
        o.comment = a.comment
        for i in infos:
            attr = i.external_attr
            o.writestr(i, payload if i is target else a.read(i))
            i.external_attr = attr
    names, comment = [i.filename for i in infos], a.comment
if sha(src) != before:
    raise SystemExit("source RSS changed during the operation")
with zipfile.ZipFile(out) as o:
    assert o.testzip() is None and o.namelist() == names and o.comment == comment
    assert hashlib.sha256(o.read(target.filename)).hexdigest() == sha(cpt)
print(f"replaced {target.filename} ({target.file_size} -> {len(payload)} bytes)")
print(f"source untouched: {src}\noutput: {out}")
