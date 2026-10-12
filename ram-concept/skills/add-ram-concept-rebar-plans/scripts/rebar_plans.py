#!/usr/bin/env python3
"""Add the office's four rebar review plans to a saved RAM Concept model: Top Long, Top Lat, Bot Long, Bot Lat.

  python rebar_plans.py add  <model.cpt> <out.cpt> [--only "Bot Long" ...]
  python rebar_plans.py list <model.cpt>

The published API cannot create plans, so this writes the saved file (a SQLite database) and never
the open model: `out` must be a new file. Each plan is a copy of the model's own standard Top Bars
plan on the Reinforcement layer, with the visible objects set to the office convention
(RAM_CONCEPT_GUI_NOTES.md, "Rebar review plans"), as the plans were set up on 2636 building 2:

  Reinforcement: <direction> User + Program Concentrated Bars, <face> Concentrated Bars,
                 Concentrated Bar Descriptions, Concentrated Bar Extent
  Element:       walls above/below (outline only), columns above/below, slab elements and edges
  every other layer: nothing

A plan is: a PlanData row (child of PlansManager), one PlotSpecData child, one FilterKeyShowFilter
child per CAD layer (FilterString = what that layer shows; ForegroundFilter points at the plan's own
layer's filter), and a StdReportLeaf in the report tree under the layer's StdReportBranch. UIDs are
one space across every table; new ones follow the model's largest.
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

PLANS = {
    "Top Long": ("Longitude", "TopFace"),
    "Top Lat": ("Latitude", "TopFace"),
    "Bot Long": ("Longitude", "BottomFace"),
    "Bot Lat": ("Latitude", "BottomFace"),
}
ELEMENT_FILTER = ("[WallElementsAbove][WallElementsBelow][WallElementOutlineOnly][ColumnElementsAbove]"
                  "[ColumnElementsBelow][SlabElements][SlabElementEdges]")


def rebar_filter(direction: str, face: str) -> str:
    return (f"[{direction}UserConcentratedBars][{direction}ProgramConcentratedBars][{face}ConcentratedBars]"
            "[ConcentratedBarDescriptions][ConcentratedBarExtent]")


def tables(db) -> list[str]:
    return [r[0] for r in db.execute("select name from sqlite_master where type='table'")]


def columns(db, table: str) -> list[str]:
    return [r[1] for r in db.execute(f"pragma table_info([{table}])")]


def max_uid(db) -> int:
    top = 0
    for t in tables(db):
        if "UID" in columns(db, t):
            top = max(top, db.execute(f"select coalesce(max(UID), 0) from [{t}]").fetchone()[0])
    return top


def row_dict(db, table: str, uid: int) -> dict:
    cols = columns(db, table)
    row = db.execute(f"select * from [{table}] where UID=?", (uid,)).fetchone()
    if row is None:
        raise SystemExit(f"{table} has no row {uid}")
    return dict(zip(cols, row))


def insert(db, table: str, row: dict) -> None:
    keys = list(row)
    db.execute(f"insert into [{table}] ({', '.join('[' + k + ']' for k in keys)}) values ({', '.join('?' * len(keys))})",
               [row[k] for k in keys])


def layer_uids(db) -> tuple[int, int]:
    rebar = db.execute("select UID from RebarLayer").fetchone()
    element = db.execute("select UID from ElementLayer").fetchone()
    if not rebar or not element:
        raise SystemExit("no Reinforcement or Element layer in this model")
    return rebar[0], element[0]


def plan_face(db, plan_uid: int, rebar_layer: int) -> str:
    """What a plan on the Reinforcement layer shows, from its own layer's filter."""
    row = db.execute("select FilterString from FilterKeyShowFilter where ParentUID=? and CadLayer=?",
                     (plan_uid, rebar_layer)).fetchone()
    return row[0] if row else ""


def existing(db) -> dict[str, str]:
    rebar, _ = layer_uids(db)
    out = {}
    for uid, name in db.execute("select UID, Name from PlanData"):
        if name in PLANS:
            out[name] = plan_face(db, uid, rebar)
    return out


def template_plan(db, rebar_layer: int) -> int:
    """The model's standard Top Bars plan on the Reinforcement layer: the one every copy is made from."""
    for uid, name in db.execute("select UID, Name from PlanData order by ChildIndex"):
        fg = db.execute("select ForegroundFilter from PlanData where UID=?", (uid,)).fetchone()[0]
        layer = db.execute("select CadLayer from FilterKeyShowFilter where UID=?", (fg,)).fetchone()
        if layer and layer[0] == rebar_layer and name == "Top Bars":
            return uid
    raise SystemExit("no standard Top Bars plan on the Reinforcement layer to copy from")


def add_plan(db, name: str, template: int, rebar_layer: int, element_layer: int, next_uid: int) -> int:
    """Append one plan after the last one. Returns the next free UID."""
    direction, face = PLANS[name]
    plan = row_dict(db, "PlanData", template)
    last = db.execute("select UID, ChildIndex from PlanData order by ChildIndex desc limit 1").fetchone()
    plan_uid = next_uid
    next_uid += 1
    plan.update(UID=plan_uid, Name=name, ChildIndex=last[1] + 1, Number=last[1] + 1,
                PreviousSibUID=last[0], NextSibUID=0, RssUid=0)

    # the plan's children, in the template's order: the plot spec and one filter per CAD layer
    kids = []
    for table in ("PlotSpecData", "FilterKeyShowFilter"):
        for (uid,) in db.execute(f"select UID from [{table}] where ParentUID=? order by ChildIndex", (template,)):
            kids.append((table, row_dict(db, table, uid)))
    kids.sort(key=lambda k: k[1]["ChildIndex"])
    foreground = None
    new_kids = []
    for table, row in kids:
        row = dict(row, UID=next_uid, ParentUID=plan_uid, RssUid=0)
        next_uid += 1
        if table == "FilterKeyShowFilter":
            if row["CadLayer"] == rebar_layer:
                row["FilterString"] = rebar_filter(direction, face)
                foreground = row["UID"]
            elif row["CadLayer"] == element_layer:
                row["FilterString"] = ELEMENT_FILTER
            else:
                row["FilterString"] = ""
        new_kids.append((table, row))
    if foreground is None:
        raise SystemExit("the template plan has no filter for the Reinforcement layer")
    for i, (table, row) in enumerate(new_kids):
        row["PreviousSibUID"] = new_kids[i - 1][1]["UID"] if i else 0
        row["NextSibUID"] = new_kids[i + 1][1]["UID"] if i + 1 < len(new_kids) else 0
    plan["ForegroundFilter"] = foreground

    # the report tree: a leaf beside the template's, last under the layer's branch
    leaf = db.execute("select UID from StdReportLeaf where ReportData=?", (template,)).fetchone()
    if leaf is None:
        raise SystemExit("the template plan has no report tree leaf")
    leaf = row_dict(db, "StdReportLeaf", leaf[0])
    last_leaf = db.execute("select UID, ChildIndex from StdReportLeaf where ParentUID=? order by ChildIndex desc limit 1",
                           (leaf["ParentUID"],)).fetchone()
    leaf.update(UID=next_uid, ReportData=plan_uid, ChildIndex=last_leaf[1] + 1, Number=last_leaf[1] + 1,
                PreviousSibUID=last_leaf[0], NextSibUID=0, RssUid=0)
    next_uid += 1

    insert(db, "PlanData", plan)
    db.execute("update PlanData set NextSibUID=? where UID=?", (plan_uid, last[0]))
    for table, row in new_kids:
        insert(db, table, row)
    insert(db, "StdReportLeaf", leaf)
    db.execute("update StdReportLeaf set NextSibUID=? where UID=?", (leaf["UID"], last_leaf[0]))
    return next_uid


def cmd_list(a):
    db = sqlite3.connect(a.model)
    rebar, _ = layer_uids(db)
    have = existing(db)
    for name, (direction, face) in PLANS.items():
        if name not in have:
            print(f"{name}: missing")
        elif have[name] == rebar_filter(direction, face):
            print(f"{name}: present, office set-up")
        else:
            print(f"{name}: present but shows {have[name] or 'nothing'}")
    return 0


def cmd_add(a):
    src, out = Path(a.model), Path(a.out)
    if src.resolve() == out.resolve():
        raise SystemExit("out must be a new file, never the model itself")
    if out.exists() and not a.overwrite:
        raise SystemExit(f"{out} exists; pick a new name or pass --overwrite")
    shutil.copyfile(src, out)
    db = sqlite3.connect(out)
    try:
        rebar, element = layer_uids(db)
        have = existing(db)
        wanted = a.only or list(PLANS)
        template = template_plan(db, rebar)
        next_uid = max_uid(db) + 1
        added, kept = [], []
        for name in wanted:
            if name not in PLANS:
                raise SystemExit(f"{name}: not one of {', '.join(PLANS)}")
            if name in have:
                kept.append(name)
                continue
            next_uid = add_plan(db, name, template, rebar, element, next_uid)
            added.append(name)
        db.commit()
    finally:
        db.close()
    print(f"{out}: added {', '.join(added) or 'nothing'}" + (f"; already there: {', '.join(kept)}" if kept else ""))
    if kept:
        wrong = [n for n in kept if have[n] != rebar_filter(*PLANS[n])]
        if wrong:
            print(f"check the visible objects of {', '.join(wrong)}: not the office set-up (rename or delete them in Concept first)")
    print("Open the file in Concept to see them under Layers > Reinforcement.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    ls = sub.add_parser("list", help="which of the four plans the model has")
    ls.add_argument("model")
    add = sub.add_parser("add", help="write a copy of the model with the plans added")
    add.add_argument("model")
    add.add_argument("out")
    add.add_argument("--only", nargs="+", metavar="NAME", help="only these plans (default all four)")
    add.add_argument("--overwrite", action="store_true")
    a = p.parse_args(argv)
    return {"list": cmd_list, "add": cmd_add}[a.command](a)


if __name__ == "__main__":
    sys.exit(main())
