#!/usr/bin/env python3
"""Replace RAM Concept program rebar with a few user bar groups, one layer at a time.

Works on an API-enabled Concept session holding a separately named copy of the
model. Every save goes to the work folder; ``save_file`` re-targets the open
model there, so the original file is never written.

  baseline  clear the layer's user bars, calc, save base.cpt (full program demand)
  options   groups-vs-tonnage table from base.cpt; writes plan-1.json
  apply     write a plan's groups as user bars
  verify    calc, save round-N.cpt, report leftovers (real vs peaking)
  absorb    grow/tighten groups to cover real leftovers; writes the next plan
  run       apply -> verify -> absorb until no real leftovers (or max rounds)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, fields
from pathlib import Path

import cpt_reader as cr
import rebar_groups as rg

SKILLS = Path(__file__).resolve().parents[2]
VENDOR = SKILLS / "attach-ram-concept-api" / "scripts" / "api_vendor"
INSTALL = Path(r"C:\Program Files\Bentley\Engineering\RAM Concept")


# ---------------------------------------------------------------- live session

def api():
    sys.path.insert(0, str(VENDOR))
    newest = sorted(INSTALL.glob("RAM Concept */python"))[-1]
    sys.path.insert(1, str(newest))
    from ram_concept.concept import Concept
    from ram_concept.model import Model
    return Concept, Model


def discover_port() -> int:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-CimInstance Win32_Process -Filter \"Name='Concept.exe'\").CommandLine"],
        capture_output=True, text=True).stdout
    ports = sorted({int(p) for p in re.findall(r"-port\s+(\d+)", out)})
    if len(ports) != 1:
        raise SystemExit(f"Need exactly one API-enabled Concept (-apiServerWithGui); found ports {ports}. Pass --port.")
    return ports[0]


def live_model(port: int | None):
    Concept, Model = api()
    try:
        concept = Concept.attach_to_concept(port or discover_port())
    except TimeoutError:
        raise SystemExit("Concept did not answer. If its Scripting Server window shows Resume, "
                         "the server is paused: click Resume and rerun.")
    model = Model(concept)
    concept._model = model
    return model


def enums():
    from ram_concept.enums import BarEnd, DesignedBy, ElevationReference, SlabFace, SpanSet
    return BarEnd, DesignedBy, ElevationReference, SlabFace, SpanSet


def user_bars(model, layer: cr.Layer):
    _, DesignedBy, _, SlabFace, SpanSet = enums()
    span = SpanSet.LONGITUDE if layer.direction == "long" else SpanSet.LATITUDE
    face = SlabFace.TOP if layer.face == "top" else SlabFace.BOTTOM
    return [b for b in model.cad_manager.rebar_layer.concentrated_rebar(DesignedBy.USER, span) if b.slab_face == face]


def calc_and_save(model, path: Path) -> float:
    start = time.time()
    model.calc_all(timeout_seconds=3600)
    model.save_file(str(path))
    return time.time() - start


# ---------------------------------------------------------------- work folder

def settings_of(state: dict) -> rg.Settings:
    s = rg.Settings(**{f.name: state["settings"][f.name] for f in fields(rg.Settings) if f.name in state["settings"]})
    s.spacings = tuple(s.spacings)
    return s


def load_plan(work: Path, n: int) -> dict:
    return json.loads((work / f"plan-{n}.json").read_text())


def latest(work: Path, prefix: str) -> int:
    nums = [int(m.group(1)) for p in work.glob(f"{prefix}-*.*") if (m := re.match(rf"{prefix}-(\d+)\.", p.name))]
    return max(nums, default=0)


def split_peaks(demands, s: rg.Settings, mesh: cr.Mesh, layer: cr.Layer):
    real, peaks = [], []
    for d in demands:
        if rg.is_peak(d, s):
            x, y = layer.to_plan((d.a0 + d.a1) / 2, (d.b0 + d.b1) / 2)
            d.tag = "at opening/edge" if mesh.near_opening(x, y) else ""
            peaks.append(d)
        else:
            real.append(d)
    return real, peaks


def describe(d, layer: cr.Layer) -> str:
    x0, y0 = layer.to_plan(d.a0, d.b0)
    x1, y1 = layer.to_plan(d.a1, d.b1)
    return (f"({d.count}){d.size}x{d.length:.1f} at x={min(x0, x1):.1f}-{max(x0, x1):.1f} "
            f"y={min(y0, y1):.1f}-{max(y0, y1):.1f} {d.tag}").rstrip()


def tons_of(groups, s) -> float:
    return sum(g.pounds(s) for g in groups) / 2000.0


# ---------------------------------------------------------------- commands

def cmd_baseline(a):
    model, layer = live_model(a.port), cr.Layer.parse(a.layer)
    old = user_bars(model, layer)
    for b in old:
        b.delete()
    secs = calc_and_save(model, a.work / "base.cpt")
    prog = cr.bars(a.work / "base.cpt", layer, cr.PROGRAM)
    pounds = sum(d.count * d.length * rg.BAR_WEIGHT[d.size] for d in prog)
    print(f"cleared {len(old)} user groups; calc+save {secs:.0f}s")
    print(f"program demand: {len(prog)} groups, {sum(d.count for d in prog)} bars, {pounds / 2000:.1f} tons")


def cmd_options(a):
    layer = cr.Layer.parse(a.layer)
    base = a.work / "base.cpt"
    mesh = cr.Mesh(base)
    demands = cr.bars(base, layer, cr.PROGRAM)
    s = rg.Settings(size=cr.dominant_size(demands))
    real, peaks = split_peaks(demands, s, mesh, layer)
    plans = rg.options(real, s)
    program_tons = sum(d.count * d.length * rg.BAR_WEIGHT[d.size] for d in demands) / 2000
    print(f"{layer.face} {layer.direction}: {len(demands)} program groups ({program_tons:.1f} tons program-only); "
          f"{len(peaks)} peaking left out")
    print(f"{'option':>6} {'groups':>7} {'tons':>6}")
    for i, p in enumerate(plans, 1):
        print(f"{i:>6} {p['groups']:>7} {p['tons']:>6}")
    chosen = plans[a.option - 1] if a.option else rg.pick(plans, a.target_groups, a.max_tons)
    state = dict(layer=a.layer, settings=asdict(s), budget_lb=chosen["budget_lb"],
                 depth=cr.depth_rule(base, layer, mesh), groups=chosen["plan"])
    (a.work / "plan-1.json").write_text(json.dumps(state, indent=1))
    (a.work / "peaks.json").write_text(json.dumps([describe(d, layer) for d in peaks], indent=1))
    print(f"chose option {plans.index(chosen) + 1}: {chosen['groups']} groups, {chosen['tons']} tons -> plan-1.json")


def bar_elevation(state: dict, thinnest: float) -> float:
    depth = {float(k): v for k, v in state["depth"].items()}
    if thinnest in depth:
        return depth[thinnest]
    near = min(depth, key=lambda t: abs(t - thinnest))
    # bottom bars follow the soffit; top bars stay put under a flush top
    return depth[near] - (thinnest - near) if state["layer"].startswith("bot") else depth[near]


def cmd_apply(a):
    model, layer = live_model(a.port), cr.Layer.parse(a.layer)
    from ram_concept.line_segment_2D import LineSegment2D
    from ram_concept.point_2D import Point2D
    BarEnd, _, ElevationReference, SlabFace, SpanSet = enums()
    n = a.plan or latest(a.work, "plan")
    state = load_plan(a.work, n)
    s = settings_of(state)
    mesh = cr.Mesh(a.work / "base.cpt")
    bar = model.rebars.rebar(s.size)
    old = user_bars(model, layer)
    for b in old:
        b.delete()
    for g in map(rg.from_dict, state["groups"]):
        mid = (g.a0 + g.a1) / 2
        b = model.cad_manager.rebar_layer.add_concentrated_rebar(
            LineSegment2D(Point2D(*layer.to_plan(mid, g.b1)), Point2D(*layer.to_plan(mid, g.b0))))
        b.span_set = SpanSet.LONGITUDE if layer.direction == "long" else SpanSet.LATITUDE
        b.slab_face = SlabFace.TOP if layer.face == "top" else SlabFace.BOTTOM
        b.bar_type = bar
        b.elevation_reference = ElevationReference.ABSOLUTE
        b.elevation_from_reference = bar_elevation(state, mesh.thinnest(layer, g.a0, g.a1, g.b0, g.b1))
        b.ending_anchorage_1 = BarEnd.STRAIGHT
        b.ending_anchorage_2 = BarEnd.STRAIGHT
        b.extent_zone_width = g.a1 - g.a0
        b.set_extent_zone_width_fractions(0.5)
        b.spacing = g.spacing(s)
    print(f"plan-{n}: replaced {len(old)} user groups with {len(state['groups'])}")


def cmd_verify(a):
    model, layer = live_model(a.port), cr.Layer.parse(a.layer)
    n = latest(a.work, "plan")
    state, path = load_plan(a.work, n), a.work / f"round-{n}.cpt"
    s = settings_of(state)
    secs = calc_and_save(model, path)
    left = cr.bars(path, layer, cr.PROGRAM)
    real, peaks = split_peaks(left, s, cr.Mesh(path), layer)
    groups = [rg.from_dict(g) for g in state["groups"]]
    left_tons = sum(d.count * d.length * rg.BAR_WEIGHT[d.size] for d in left) / 2000
    print(f"round {n} (calc+save {secs:.0f}s): {len(groups)} user groups, {tons_of(groups, s):.1f} tons; "
          f"program left: {len(real)} real, {len(peaks)} peaking ({left_tons:.2f} tons)")
    for d in real:
        print("  real   ", describe(d, layer))
    for d in peaks:
        print("  peaking", describe(d, layer))
    return real


def cmd_absorb(a):
    layer = cr.Layer.parse(a.layer)
    n = latest(a.work, "plan")
    state = load_plan(a.work, n)
    s = settings_of(state)
    path = a.work / f"round-{n}.cpt"
    real, _ = split_peaks(cr.bars(path, layer, cr.PROGRAM), s, cr.Mesh(path), layer)
    groups = [rg.from_dict(g) for g in state["groups"]]
    groups, unplaced = rg.absorb(groups, real, s)
    groups += rg.seed(unplaced, s)
    groups = rg.merge_until(groups, s, state["budget_lb"])
    state["groups"] = [asdict(g) for g in groups]
    (a.work / f"plan-{n + 1}.json").write_text(json.dumps(state, indent=1))
    print(f"plan-{n + 1}: absorbed {len(real) - len(unplaced)}, new {len(unplaced)}; "
          f"{len(groups)} groups, {tons_of(groups, s):.1f} tons")


def cmd_run(a):
    for _ in range(a.rounds):
        cmd_apply(a)
        if not cmd_verify(a):
            print("no real leftovers; done")
            return
        cmd_absorb(a)
    print(f"stopped after {a.rounds} rounds with real leftovers; review the last round")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["baseline", "options", "apply", "verify", "absorb", "run"])
    p.add_argument("--layer", required=True, help="bot-long, bot-lat, top-long or top-lat")
    p.add_argument("--work", required=True, type=Path, help="per-layer work folder (job folder, not this repo)")
    p.add_argument("--port", type=int, help="API port (auto-detected when one session runs)")
    p.add_argument("--target-groups", type=int, default=50)
    p.add_argument("--max-tons", type=float, default=15.0)
    p.add_argument("--option", type=int, help="pick this row of the options table instead")
    p.add_argument("--plan", type=int, help="apply this plan number (default latest)")
    p.add_argument("--rounds", type=int, default=4)
    a = p.parse_args(argv)
    a.work = a.work.resolve()
    a.work.mkdir(parents=True, exist_ok=True)
    {"baseline": cmd_baseline, "options": cmd_options, "apply": cmd_apply,
     "verify": cmd_verify, "absorb": cmd_absorb, "run": cmd_run}[a.command](a)


if __name__ == "__main__":
    main()
