#!/usr/bin/env python3
"""Replace RAM Concept program rebar with a few user bar groups, one layer at a time.

Works on an API-enabled Concept session holding a separately named copy of the
model. Every save goes to the work folder; ``save_file`` re-targets the open
model there, so the original file is never written.

  baseline  clear the layer's user bars, calc, save base.cpt (full program demand)
            --reuse-calc saves without calculating when the layer has no user
            bars and the open model was just calculated
  options   groups-vs-tonnage table from base.cpt; writes plan-1.json
  apply     write a plan's groups as user bars
  verify    calc, save round-N.cpt, report leftovers (real vs peaking)
  absorb    grow/tighten groups to cover real leftovers; writes the next plan
            (beam bars grow by count over mid-span leftovers inside a beam)
  run       apply -> verify -> absorb until no real leftovers (or max rounds)

  --absorb-peaks also stretches the nearest group over peaking bars (absorb, run).
  --peak-bars / --peak-length (options) say what counts as peaking; --peak-length 0
            leaves every 1 or 2 bar zone as program bars whatever its length.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, fields
from pathlib import Path

import cpt_reader as cr
import rebar_groups as rg

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / "clean-up-ram-concept-t-beams" / "scripts"))

import beam_rules as br          # noqa: E402

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


def note(work: Path, text: str) -> None:
    """Append one line to the work folder's event log (shown by dashboard.py)."""
    with (work / "events.jsonl").open("a") as log:
        log.write(json.dumps(dict(t=time.time(), text=text)) + "\n")


def tons_of(groups, s) -> float:
    return sum(g.pounds(s) for g in groups) / 2000.0


def split_beam(demands, beams: list):
    """Set aside bars that sit inside a beam: (slab bars, beam bars)."""
    beam = [d for d in demands if br.in_beam(d, beams)]
    return [d for d in demands if d not in beam], beam


def beam_callouts(groups: list[dict], layer: cr.Layer) -> str:
    out = []
    for g in groups:
        x0, y0 = layer.to_plan(g["a0"], g["b0"])
        x1, y1 = layer.to_plan(g["a1"], g["b1"])
        out.append(f"{g['count']}{g['size']} x {g['b1'] - g['b0']:g}' in the beam at ({(x0 + x1) / 2:.0f},{(y0 + y1) / 2:.0f})")
    return "; ".join(out)


def load_transitions(path, layer: cr.Layer) -> dict:
    """Mat-boundary crossings for this layer from transition_check.py, as local (a, b) points by verdict."""
    marks = {"notch only": [], "real": []}
    if not path:
        return marks
    direction = "longitude" if layer.direction == "long" else "latitude"
    for f in json.loads(Path(path).read_text()):
        if f["face"] == layer.face and f["direction"] == direction and f["verdict"] in marks and f["demand"] >= 5:
            marks[f["verdict"]].append(layer.to_local(f["x"], f["y"]))
    return marks


def over(d, marks: list, across: float = 1.0, along: float = 0.5) -> bool:
    return any(d.a0 - across <= a <= d.a1 + across and d.b0 - along <= b <= d.b1 + along for a, b in marks)


def split_waived(demands, marks: dict):
    """Set aside program bars that exist only because the mat capacity notches at a mat boundary.

    A bar is waived when it sits on a "notch only" crossing and on no "real"
    one: the mat either side carries the demand, so the bar is not required.
    """
    waived = [d for d in demands if over(d, marks["notch only"]) and not over(d, marks["real"])]
    return [d for d in demands if d not in waived], waived


# ---------------------------------------------------------------- commands

def cmd_baseline(a):
    model, layer = live_model(a.port), cr.Layer.parse(a.layer)
    old = user_bars(model, layer)
    if a.reuse_calc:
        if old:
            raise SystemExit(f"{a.layer} has {len(old)} user groups; run baseline without --reuse-calc")
        model.save_file(str(a.work / "base.cpt"))
        note(a.work, "baseline: reused the current calc")
        secs = 0.0
    else:
        for b in old:
            b.delete()
        note(a.work, f"baseline: cleared {len(old)} user groups, calc started")
        secs = calc_and_save(model, a.work / "base.cpt")
        note(a.work, f"baseline calc done in {secs:.0f}s")
    prog = cr.bars(a.work / "base.cpt", layer, cr.PROGRAM)
    pounds = sum(d.count * d.length * rg.BAR_WEIGHT[d.size] for d in prog)
    print(f"cleared {len(old)} user groups; calc+save {secs:.0f}s")
    print(f"program demand: {len(prog)} groups, {sum(d.count for d in prog)} bars, {pounds / 2000:.1f} tons")


def cmd_options(a):
    layer = cr.Layer.parse(a.layer)
    base = a.work / "base.cpt"
    mesh = cr.Mesh(base)
    demands = cr.bars(base, layer, cr.PROGRAM)
    s = rg.Settings(size=cr.dominant_size(demands), peak_bars=a.peak_bars, peak_length=a.peak_length)
    marks = load_transitions(a.verdicts, layer)
    slab_demands, beam_bars = split_beam(demands, cr.beam_rects(base, layer))
    beam_groups = [br.beam_group(d) for d in beam_bars]
    real, peaks = split_peaks(slab_demands, s, mesh, layer)
    real, waived = split_waived(real, marks)
    peaks, waived_peaks = split_waived(peaks, marks)
    plans = rg.options(real, s)
    program_tons = sum(d.count * d.length * rg.BAR_WEIGHT[d.size] for d in demands) / 2000
    print(f"{layer.face} {layer.direction}: {len(demands)} program groups ({program_tons:.1f} tons program-only); "
          f"{len(peaks)} peaking left out"
          + (f"; {len(waived) + len(waived_peaks)} waived at mat-boundary notches" if a.verdicts else ""))
    if beam_groups:
        print(f"beam bars, kept out of the bands: {beam_callouts(beam_groups, layer)}")
    print(f"{'option':>6} {'groups':>7} {'tons':>6}")
    knee = rg.knee(plans, a.knee_tons_per_group)
    for i, p in enumerate(plans, 1):
        print(f"{i:>6} {p['groups']:>7} {p['tons']:>6}{'   <- knee' if p is knee else ''}")
    if a.option:
        chosen = plans[a.option - 1]
    else:
        chosen = knee if a.pick == "knee" else rg.pick(plans, a.target_groups, a.max_tons)
    state = dict(layer=a.layer, settings=asdict(s), budget_lb=chosen["budget_lb"],
                 depth=cr.depth_rule(base, layer, mesh), groups=chosen["plan"],
                 verdicts=str(a.verdicts.resolve()) if a.verdicts else None, beam_groups=beam_groups)
    (a.work / "plan-1.json").write_text(json.dumps(state, indent=1))
    (a.work / "peaks.json").write_text(json.dumps([describe(d, layer) for d in peaks], indent=1))
    print(f"chose option {plans.index(chosen) + 1}: {chosen['groups']} groups, {chosen['tons']} tons -> plan-1.json")
    note(a.work, f"option {plans.index(chosen) + 1} chosen: {chosen['groups']} groups, {chosen['tons']} tons")


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
    marks = load_transitions(state.get("verdicts"), layer)
    if any("ends" not in g for g in state.get("beam_groups", [])):      # plans written before ends were kept
        base = a.work / "base.cpt"
        _, beam_bars = split_beam(cr.bars(base, layer, cr.PROGRAM), cr.beam_rects(base, layer))
        state["beam_groups"] = [br.beam_group(d) for d in beam_bars]
        (a.work / f"plan-{n}.json").write_text(json.dumps(state, indent=1))
    stepped = 0
    for g in map(rg.from_dict, state["groups"]):
        mid = (g.a0 + g.a1) / 2
        # Where the band crosses a mat boundary that really needs bars, draw it as two bar sets
        # meeting at the boundary, each anchored there and each at its own slab's depth.
        cuts = []
        for b_at in sorted(b for a_at, b in marks["real"] if g.a0 - 1 <= a_at <= g.a1 + 1 and g.b0 + 1.5 < b < g.b1 - 1.5):
            if not cuts or b_at - cuts[-1] > 3.0:
                cuts.append(round(b_at, 2))
        stepped += bool(cuts)
        ends = [g.b0] + cuts + [g.b1]
        for lo, hi in zip(ends, ends[1:]):
            b = model.cad_manager.rebar_layer.add_concentrated_rebar(
                LineSegment2D(Point2D(*layer.to_plan(mid, hi)), Point2D(*layer.to_plan(mid, lo))))
            b.span_set = SpanSet.LONGITUDE if layer.direction == "long" else SpanSet.LATITUDE
            b.slab_face = SlabFace.TOP if layer.face == "top" else SlabFace.BOTTOM
            b.bar_type = bar
            b.elevation_reference = ElevationReference.ABSOLUTE
            b.elevation_from_reference = bar_elevation(state, mesh.thinnest(layer, g.a0, g.a1, lo, hi))
            b.ending_anchorage_1 = BarEnd.ANCHORED if hi in cuts else BarEnd.STRAIGHT
            b.ending_anchorage_2 = BarEnd.ANCHORED if lo in cuts else BarEnd.STRAIGHT
            b.extent_zone_width = g.a1 - g.a0
            b.set_extent_zone_width_fractions(0.5)
            b.spacing = g.spacing(s)
    for g in state.get("beam_groups", []):
        # the beam's own bars: by count, inside the beam width, at the beam's depth
        mid = (g["a0"] + g["a1"]) / 2
        b = model.cad_manager.rebar_layer.add_concentrated_rebar(
            LineSegment2D(Point2D(*layer.to_plan(mid, g["b1"])), Point2D(*layer.to_plan(mid, g["b0"]))))
        b.span_set = SpanSet.LONGITUDE if layer.direction == "long" else SpanSet.LATITUDE
        b.slab_face = SlabFace.TOP if layer.face == "top" else SlabFace.BOTTOM
        b.bar_type = model.rebars.rebar(g["size"])
        b.elevation_reference = ElevationReference.ABSOLUTE
        b.elevation_from_reference = g["elevation"]
        # keep the program's end conditions; the bar is drawn from its high-b end to its low-b end
        end = {2: BarEnd.HOOK_90, 3: BarEnd.HOOK_180, 4: BarEnd.ANCHORED}
        low, high = g.get("ends", (1, 1))
        b.ending_anchorage_1 = end.get(high, BarEnd.STRAIGHT)
        b.ending_anchorage_2 = end.get(low, BarEnd.STRAIGHT)
        b.extent_zone_width = g["a1"] - g["a0"]
        b.set_extent_zone_width_fractions(0.5)
        b.count = g["count"]
    print(f"plan-{n}: replaced {len(old)} user groups with {len(state['groups'])}"
          + (f"; {stepped} drawn as stepped pairs anchored at a mat boundary" if stepped else "")
          + (f"; {len(state['beam_groups'])} beam bar groups" if state.get("beam_groups") else ""))
    note(a.work, f"plan {n} applied: {len(state['groups'])} user groups")


def cmd_verify(a):
    model, layer = live_model(a.port), cr.Layer.parse(a.layer)
    n = latest(a.work, "plan")
    state, path = load_plan(a.work, n), a.work / f"round-{n}.cpt"
    s = settings_of(state)
    note(a.work, f"round {n}: calc started")
    secs = calc_and_save(model, path)
    left = cr.bars(path, layer, cr.PROGRAM)
    marks = load_transitions(state.get("verdicts"), layer)
    rects = cr.beam_rects(path, layer)
    slab_left, beam_left = split_beam(left, rects)
    beam_ends = [d for d in beam_left if br.at_beam_end(d, rects)]
    beam_short = [d for d in beam_left if d not in beam_ends]
    real, peaks = split_peaks(slab_left, s, cr.Mesh(path), layer)
    real, waived = split_waived(real, marks)
    peaks, waived_peaks = split_waived(peaks, marks)
    waived += waived_peaks
    groups = [rg.from_dict(g) for g in state["groups"]]
    left_tons = sum(d.count * d.length * rg.BAR_WEIGHT[d.size] for d in left) / 2000
    print(f"round {n} (calc+save {secs:.0f}s): {len(groups)} user groups, {tons_of(groups, s):.1f} tons; "
          f"program left: {len(real)} real, {len(peaks)} peaking, {len(waived)} waived at notches ({left_tons:.2f} tons)")
    note(a.work, f"round {n} calc done in {secs:.0f}s: {len(real)} real, {len(peaks)} peaking, {len(waived)} waived")
    if state.get("beam_groups"):
        print(f"  beam bars in: {beam_callouts(state['beam_groups'], layer)}")
    # Inside a beam the program can still ask for two things. Short at mid-span: added to the
    # beam's own bars by the next absorb. At a beam end, under heavy column top bars: the
    # engineer's call, never added automatically; an override records "no bar called out".
    overrides = br.overrides(a.work.parent, layer.name)
    for d in beam_short:
        print("  beam bars short", describe(d, layer))
    for d in beam_ends:
        o = br.override_at(overrides, *layer.to_plan((d.a0 + d.a1) / 2, (d.b0 + d.b1) / 2))
        print(f"  no bar called out (override: {o['reason']})" if o else "  beam end, engineer's call", describe(d, layer))
    (a.work / "beam-ends.json").write_text(json.dumps([describe(d, layer) for d in beam_ends], indent=1))
    for d in real:
        print("  real   ", describe(d, layer))
    for d in peaks:
        print("  peaking", describe(d, layer))
    for d in waived:
        print("  waived ", describe(d, layer))
    (a.work / "peaks.json").write_text(json.dumps([describe(d, layer) for d in peaks], indent=1))
    (a.work / "waived.json").write_text(json.dumps([describe(d, layer) for d in waived], indent=1))
    return real + beam_short, peaks


def cmd_absorb(a):
    layer = cr.Layer.parse(a.layer)
    n = latest(a.work, "plan")
    state = load_plan(a.work, n)
    s = settings_of(state)
    path = a.from_model or a.work / f"round-{n}.cpt"
    marks = load_transitions(state.get("verdicts"), layer)
    rects = cr.beam_rects(path, layer)
    slab_left, beam_left = split_beam(cr.bars(path, layer, cr.PROGRAM), rects)
    beam_short = [d for d in beam_left if not br.at_beam_end(d, rects)]
    real, peaks = split_peaks(slab_left, s, cr.Mesh(path), layer)
    real, _ = split_waived(real, marks)
    peaks, _ = split_waived(peaks, marks)
    groups = [rg.from_dict(g) for g in state["groups"]]
    groups, unplaced = rg.absorb(groups, real, s)
    groups += rg.seed(unplaced, s)
    peak_note = ""
    if a.absorb_peaks:
        groups, left = rg.absorb_peaks(groups, peaks, s, rects)
        peak_note = f", peaks stretched over {len(peaks) - len(left)} of {len(peaks)}"
        for d in left:
            print("  peak left", describe(d, layer))
    groups = rg.merge_until(groups, s, state["budget_lb"])
    plan = [asdict(g) for g in groups]
    if plan == state["groups"] and not beam_short:
        print("nothing left to absorb")
        note(a.work, "nothing left to absorb; finished")
        return False
    state["groups"] = plan
    state["beam_groups"] = br.grow_beam_groups(state.get("beam_groups", []), beam_short, rects)
    (a.work / f"plan-{n + 1}.json").write_text(json.dumps(state, indent=1))
    print(f"plan-{n + 1}: absorbed {len(real) - len(unplaced)}, new {len(unplaced)}{peak_note}; "
          f"{len(groups)} groups, {tons_of(groups, s):.1f} tons"
          + (f"; beam bars grown over {len(beam_short)} mid-span leftovers" if beam_short else ""))
    note(a.work, f"plan {n + 1} written: {len(groups)} groups, {tons_of(groups, s):.1f} tons")
    return True


def cmd_run(a):
    layer, before = cr.Layer.parse(a.layer), None
    for _ in range(a.rounds):
        cmd_apply(a)
        real, peaks = cmd_verify(a)
        if not real and not (a.absorb_peaks and peaks):
            print("no real leftovers; done")
            return
        now = sorted(describe(d, layer) for d in real)
        if now == before:
            # Growing the group over it did not clear it: a mesh spike at a slab edge or notch, not a
            # band problem. Another calc would only repeat; the engineer decides (2636 bot-lat, 2026-10-12).
            print("the same leftovers came back after absorbing them; stopped, the engineer's call:")
            for line in now:
                print("  stubborn", line)
            return
        before = now
        if not cmd_absorb(a):
            return
    print(f"stopped after {a.rounds} rounds; review the last round")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["baseline", "options", "apply", "verify", "absorb", "run"])
    p.add_argument("--layer", required=True, help="bot-long, bot-lat, top-long or top-lat")
    p.add_argument("--work", required=True, type=Path, help="per-layer work folder (job folder, not this repo)")
    p.add_argument("--port", type=int, help="API port (auto-detected when one session runs)")
    p.add_argument("--target-groups", type=int, default=50)
    p.add_argument("--max-tons", type=float, default=15.0)
    p.add_argument("--option", type=int, help="pick this row of the options table instead")
    p.add_argument("--pick", choices=["target", "knee"], default="target",
                   help="default row: closest to --target-groups within --max-tons, or the knee of the table")
    p.add_argument("--knee-tons-per-group", type=float, default=0.5,
                   help="knee: stop merging when a step costs more tons per group removed than this")
    p.add_argument("--peak-bars", type=int, default=2,
                   help="options: program demand of this many bars or fewer is peaking: listed, not banded (kept in the plan)")
    p.add_argument("--peak-length", type=float, default=5.0,
                   help="options: ... and no longer than this many ft; 0 for any length (office rule for bottom bars: "
                        "1 or 2 bar zones stay program bars)")
    p.add_argument("--reuse-calc", action="store_true",
                   help="baseline: keep the current calc when the layer has no user bars")
    p.add_argument("--plan", type=int, help="apply this plan number (default latest)")
    p.add_argument("--verdicts", type=Path,
                   help="options: verdicts.json from transition_check.py; notch-only bars are waived, "
                        "bands crossing a real mat boundary are drawn as two anchored sets")
    p.add_argument("--from-model", type=Path,
                   help="absorb: read the leftovers from this saved, calculated model instead of the folder's "
                        "last round (when a later run in another work folder holds the newest state)")
    p.add_argument("--rounds", type=int, default=4)
    p.add_argument("--absorb-peaks", action="store_true",
                   help="stretch the nearest group over peaking bars instead of only listing them")
    a = p.parse_args(argv)
    a.work = a.work.resolve()
    a.work.mkdir(parents=True, exist_ok=True)
    marker = a.work / ".working"             # dashboard.py shows "Working" while this exists
    marker.write_text(json.dumps(dict(pid=os.getpid(), t=time.time(), text=f"{a.layer} {a.command}")))
    try:
        {"baseline": cmd_baseline, "options": cmd_options, "apply": cmd_apply,
         "verify": cmd_verify, "absorb": cmd_absorb, "run": cmd_run}[a.command](a)
    finally:
        marker.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
