#!/usr/bin/env python3
"""The RAM Concept member of a RAM Structural System .rss archive: list, hash or extract it. Read-only.

  python rss_member.py <model.rss> --list
  python rss_member.py <model.rss> --hash [--member cpt1027E]
  python rss_member.py <model.rss> --extract <out.cpt> [--member cpt1027E]

An .rss is a zip. The elevated slab's Concept file is the member ending .cpt<story>E (the mat is ...M). Without
--member the single ...E member is used; with more than one, --member is required.
"""
import argparse, hashlib, re, zipfile
from pathlib import Path


def member_name(z, suffix):
    names = z.namelist()
    hits = [n for n in names if n.endswith("." + suffix)] if suffix else [n for n in names if re.search(r"\.cpt\d+E$", n)]
    if len(hits) != 1:
        raise SystemExit(f"need exactly one Concept member, found {hits or [n for n in names if '.cpt' in n]}; pass --member")
    return hits[0]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rss", type=Path)
    p.add_argument("--list", action="store_true")
    p.add_argument("--hash", action="store_true")
    p.add_argument("--extract", type=Path)
    p.add_argument("--member", help="member suffix, e.g. cpt1027E")
    a = p.parse_args(argv)
    with zipfile.ZipFile(a.rss) as z:
        if a.list:
            for i in z.infolist():
                if ".cpt" in i.filename:
                    print(f"{i.filename}  {i.file_size} bytes  {i.date_time}  sha {hashlib.sha256(z.read(i)).hexdigest()[:12]}")
            return 0
        name = member_name(z, a.member)
        data = z.read(name)
        if a.extract:
            if a.extract.exists():
                raise SystemExit(f"{a.extract} exists; not overwritten")
            a.extract.write_bytes(data)
            print(f"extracted {name} ({len(data)} bytes, sha {hashlib.sha256(data).hexdigest()[:12]}) -> {a.extract}")
        else:
            print(f"{name} {hashlib.sha256(data).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
