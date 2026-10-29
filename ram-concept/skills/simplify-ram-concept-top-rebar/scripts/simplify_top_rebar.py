#!/usr/bin/env python3
"""Replace RAM Concept program top bars over columns with typical count-based user groups.

Both directions in one work folder. Uses the engine in
``../simplify-ram-concept-rebar/scripts`` for the live session and .cpt reads.

Over columns (bars by count):
  options  shared count lists for both directions, 1 to 5 typical counts, priced (from base.cpt)
  plan     write the next plan:  --typical 5 7 10 15 20   (heavier columns keep their own count; lengths even feet)
  run      plan (when --typical is given) -> apply -> verify

Away from columns, by count, the way the engineer finished 2636 building 1 (one group over each cluster of
program bars, one length per direction), once the column groups are in and calculated:
  clusters      write the next plan with the groups away from columns:  --cluster-length 14 12  (long, lat;
                default: the commonest program bar length per direction)
  run-clusters  clusters -> apply -> verify -> column groups take the leftovers beside them, until nothing
                real is left (3 rounds at most)

Away from columns as bands by spacing (the older way, like the bottom layers):
  band-options  groups-vs-tons table for the scattered top bars:  --band-size "#7"
  bands         add the chosen bands to the plan:  --band-size "#7" --option LONG LAT   (default: knee rows)
  run-bands     apply -> verify -> capture leftovers into the nearest group, until nothing changes
  merge-bands   merge neighbouring bands whose spacing is up to --class-jump steps apart (default 2)
                when one merge adds no more than --merge-budget lb (default 500)

  apply    delete user top bars, draw the column groups and any bands
  verify   calc, save round-N.cpt, report what the program still adds
  report   the same report on the latest saved round, without calculating
  dedupe   delete stacked copies of user top bars in the live session (same footprint, count, depth), both
           directions; --calc verifies after. The report flags stacks in a saved round.

Beam columns and "no bar called out" overrides follow ../clean-up-ram-concept-t-beams
(t_beam_cleanup.py override ...); the record is decisions.json beside the work folders.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "simplify-ram-concept-rebar" / "scripts"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE.parents[1] / "clean-up-ram-concept-t-beams" / "scripts"))

import beam_rules as br          # noqa: E402
import cpt_reader as cr          # noqa: E402
import rebar_groups as rg        # noqa: E402
import simplify_rebar as sr      # noqa: E402
import t_beam_cleanup as tb      # noqa: E402
import top_columns as tc         # noqa: E402

LAYERS = ("top-long", "top-lat")
FT = 3048.0


def columns_local(path: Path, layer: cr.Layer) -> list[tuple[float, float]]:
    out = []
    for (point,) in cr.connect(path).execute("select Point0 from Column"):
        x, y = (float(v) / FT for v in re.findall(r"\[([-\d.eE+]+)\]", point))
        out.append(layer.to_local(x, y))
    return out


def gather(path: Path, layer: cr.Layer, overrides=()):
    """Program top bars over each column, counted in the layer's dominant bar size.

    Returns the columns to reinforce, the program bars over no column, the bar
    size, and what is set aside with no bar called out: columns a beam runs
    through parallel to the bars, and anything at a recorded override.
    """
    demands = cr.bars(path, layer, cr.PROGRAM)
    size = cr.dominant_size(demands)
    for d in demands:
        if d.size != size:
            d.count = math.ceil(d.count * rg.BAR_AREA[d.size] / rg.BAR_AREA[size])
            d.size = size
    bars, loose = tc.assign(demands, columns_local(path, layer))
    through = tb.through_columns(path, layer)
    at_mark = lambda a, b: br.override_at(overrides, *layer.to_plan(a, b)) is not None
    aside = [c for c in bars if c.column in through or at_mark(c.a, c.b)]
    loose_aside = [d for d in loose if at_mark((d.a0 + d.a1) / 2, (d.b0 + d.b1) / 2)]
    aside += [tc.ColumnBars(-1, (d.a0 + d.a1) / 2, (d.b0 + d.b1) / 2, d.count, d.a0, d.a1, d.b0, d.b1,
                            getattr(d, "elevation", 0.0), d.size) for d in loose_aside]
    return ([c for c in bars if c not in aside], [d for d in loose if d not in loose_aside], size, aside)


def beam_note(aside, layer: cr.Layer, overrides=()) -> str:
    """What is deliberately not called out, and what the program would have added there."""
    parts = []
    for c in aside:
        x, y = layer.to_plan(c.a, c.b)
        o = br.override_at(overrides, x, y)
        reason = o["reason"] if o else tb.THROUGH
        parts.append(f"({x:.0f},{y:.0f}) {reason} [program would add {c.count}{c.size}]")
    return "no top bar called out (override): " + "; ".join(parts) if parts else ""


def _point(text: str) -> tuple[float, float]:
    x, y = (float(v) / FT for v in re.findall(r"\[([-\d.eE+]+)\]", text))
    return x, y


def beam_check(path: Path, reach: float = 1.5) -> tuple[int, int, list[tuple[float, float]]]:
    """Design spans along beams still on slab strip settings, all spans along beams, columns on beams."""
    db = cr.connect(path)
    beams = [(_point(a), _point(b)) for a, b in db.execute("select Point0, Point1 from Beam")]

    def beam_under(x, y):
        for (a, b), (c, d) in beams:
            length = math.hypot(c - a, d - b)
            if not length:
                continue
            s = max(0.0, min(1.0, ((x - a) * (c - a) + (y - b) * (d - b)) / length ** 2))
            if math.hypot(x - a - s * (c - a), y - b - s * (d - b)) <= reach:
                return (c - a) / length, (d - b) / length
        return None

    along = slab_set = 0
    for p0, p1, section in db.execute("select Point0, Point1, ColumnStripCrossSectionAutoTrim from SpanSegment"):
        (x0, y0), (x1, y1) = _point(p0), _point(p1)
        axis = beam_under((x0 + x1) / 2, (y0 + y1) / 2)
        span = math.hypot(x1 - x0, y1 - y0)
        if axis and span and abs((x1 - x0) * axis[0] + (y1 - y0) * axis[1]) / span > 0.95:
            along += 1
            slab_set += section == "slab rectangle"
    columns = [_point(p) for (p,) in db.execute("select Point0 from Column")]
    return slab_set, along, [c for c in columns if beam_under(*c)]


def warn_beams(path: Path) -> None:
    slab_set, along, columns = beam_check(path)
    if slab_set:
        print(f"WARNING: {slab_set} of {along} design spans along beams still use slab strip settings. "
              f"Set them to T or L beam and recalc first; the {len(columns)} columns on beams will change:")
        print("   " + ", ".join(f"({x:.0f},{y:.0f})" for x, y in columns))


def latest(work: Path, prefix: str, ext: str) -> int:
    nums = [int(m.group(1)) for p in work.glob(f"{prefix}-*.{ext}")
            if (m := re.fullmatch(rf"{prefix}-(\d+)\.{ext}", p.name))]
    return max(nums, default=0)


def loose_tons(loose) -> float:
    return sum(d.count * d.length * rg.BAR_WEIGHT[d.size] for d in loose) / 2000


def cmd_options(a):
    """Shared count lists for both directions, 1 to --most typical counts, cheapest of each, with the schedules."""
    base = a.work / "base.cpt"
    warn_beams(base)
    by_layer, sizes = {}, {}
    for name in LAYERS:
        layer = cr.Layer.parse(name)
        overrides = br.overrides(a.work.parent, name)
        bars, loose, size, beam_bars = gather(base, layer, overrides)
        by_layer[name], sizes[name] = bars, size
        print(f"{name}: {len(bars)} columns with top demand, {size}; "
              f"{len(loose)} program groups not over a column ({loose_tons(loose):.1f} tons)")
        if beam_bars:
            print("   " + beam_note(beam_bars, layer, overrides))
    print("\nOne count list for both directions (the engineer picks a row; 2636 building 1 took 5 counts):")
    print(" types   tons   counts")
    for row in tc.type_options_shared(by_layer, a.most):
        print(f"   {row['types']}    {row['tons']:5.1f}   {', '.join(map(str, row['counts']))}")
        for name, v in row["per"].items():
            text = "; ".join(f"{n}{sizes[name]} x {length}' at {k}" + ("" if kind == "typical" else " (own)")
                             for n, length, k, kind in v["schedule"])
            print(f"            {name} {v['tons']:5.1f} t: {text}")


def cmd_plan(a):
    base = a.work / "base.cpt"
    warn_beams(base)
    mesh = cr.Mesh(base)
    state = dict(typical=sorted(a.typical), layers={})
    for name in LAYERS:
        layer = cr.Layer.parse(name)
        columns = columns_local(base, layer)
        for i in sorted(tb.through_columns(base, layer)):
            br.add_override(a.work.parent, name, *layer.to_plan(*columns[i]), reason=tb.THROUGH,
                            source="rule: beam runs through the column, parallel to the bars")
        overrides = br.overrides(a.work.parent, name)
        bars, loose, _, beam_bars = gather(base, layer, overrides)
        on_slab = lambda p, q: mesh.thickness(*layer.to_plan(p, q)) is not None
        groups = tc.typed(bars, tuple(a.typical), on_slab, tb.end_columns(base, layer))
        state["layers"][name] = [asdict(g) for g in groups]
        print(f"{name}: {len(groups)} columns, {tc.tons(groups):.1f} tons")
        if beam_bars:
            print("   " + beam_note(beam_bars, layer, overrides))
        for callout, k in tc.schedule(groups):
            print(f"   {callout} at {k}")
    n = latest(a.work, "columns-plan", "json") + 1
    (a.work / f"columns-plan-{n}.json").write_text(json.dumps(state, indent=1))
    sr.note(a.work, f"plan {n}: typical {state['typical']}")
    print(f"-> columns-plan-{n}.json")


def scattered(path: Path, layer: cr.Layer, verdicts=None, overrides=()):
    """The general top class: program top bars over no column, as (real demand, peaking bars, waived).

    Waived bars sit on a mat-boundary notch that the transition check judged not required.
    """
    _, loose, size, _ = gather(path, layer, overrides)
    s = rg.Settings(size=size)
    loose, waived = sr.split_waived(loose, sr.load_transitions(verdicts, layer))
    return [d for d in loose if not rg.is_peak(d, s)], [d for d in loose if rg.is_peak(d, s)], waived


def load_state(work: Path) -> tuple[int, dict]:
    n = latest(work, "columns-plan", "json")
    return n, json.loads((work / f"columns-plan-{n}.json").read_text())


def save_state(work: Path, n: int, state: dict, text: str) -> None:
    (work / f"columns-plan-{n}.json").write_text(json.dumps(state, indent=1))
    sr.note(work, text)
    print(f"-> columns-plan-{n}.json")


def band_tons(bands: list[dict], s: rg.Settings) -> float:
    return sr.tons_of([rg.from_dict(b) for b in bands], s)


def band_schedule(bands: list[dict], s: rg.Settings) -> str:
    """Spaced bars written the office way, e.g. '#7 @18" at 14 bands; #7 @12" at 6'."""
    groups = [rg.from_dict(b) for b in bands]
    counts = {}
    for g in groups:
        counts[g.spacing(s)] = counts.get(g.spacing(s), 0) + 1
    return "; ".join(f'{s.size} @{spacing:g}" at {k}' for spacing, k in sorted(counts.items(), reverse=True))


def cmd_band_options(a):
    """Groups-vs-tons table for the scattered top bars, from a calc that has the column groups but no bands."""
    n, state = load_state(a.work)
    source = a.work / state.get("bands_from", f"round-{n}.cpt")
    s = rg.Settings(size=a.band_size)
    for name in LAYERS:
        layer = cr.Layer.parse(name)
        real, peaks, waived = scattered(source, layer, a.verdicts or state.get("verdicts"), br.overrides(a.work.parent, name))
        program = sum(d.count * d.length * rg.BAR_WEIGHT[d.size] for d in real) / 2000
        plans = rg.options(real, s)
        knee = rg.knee(plans, a.knee_tons_per_group)
        print(f"\n{name}: {len(real)} scattered program groups ({program:.1f} tons program-only), "
              f"{len(peaks)} peaking left out, {len(waived)} waived at mat-boundary notches; bands in {a.band_size}")
        print(f"{'option':>6} {'bands':>6} {'tons':>6}   spacing")
        for i, p in enumerate(plans, 1):
            print(f"{i:>6} {p['groups']:>6} {p['tons']:>6}   {band_schedule(p['plan'], s)}{'   <- knee' if p is knee else ''}")


def cmd_bands(a):
    """Add spaced bands for the scattered top bars to the plan; the column groups are kept as they are."""
    n, state = load_state(a.work)
    source_name = state.get("bands_from", f"round-{n}.cpt")
    source = a.work / source_name
    s = rg.Settings(size=a.band_size)
    picks = dict(zip(LAYERS, a.option or []))
    verdicts = a.verdicts or state.get("verdicts")
    state.update(bands={}, band_budget={}, band_elevation={}, band_settings=asdict(s), bands_from=source_name,
                 verdicts=str(Path(verdicts).resolve()) if verdicts else None)
    for name in LAYERS:
        layer = cr.Layer.parse(name)
        real, _, _ = scattered(source, layer, verdicts, br.overrides(a.work.parent, name))
        plans = rg.options(real, s)
        chosen = plans[picks[name] - 1] if name in picks else rg.knee(plans, a.knee_tons_per_group)
        # top of slab is flush, so one depth per direction: where most of the program's bars sit
        depths = [round(d.elevation, 3) for d in real]
        state["bands"][name] = chosen["plan"]
        state["band_budget"][name] = chosen["budget_lb"]
        state["band_elevation"][name] = max(set(depths), key=depths.count)
        print(f"{name}: option {plans.index(chosen) + 1}: {chosen['groups']} bands, {chosen['tons']} tons: "
              f"{band_schedule(chosen['plan'], s)}")
    save_state(a.work, n + 1, state, f"plan {n + 1}: scattered top bands added")


def cmd_apply(a):
    model = sr.live_model(a.port)
    from ram_concept.line_segment_2D import LineSegment2D
    from ram_concept.point_2D import Point2D
    BarEnd, _, ElevationReference, SlabFace, SpanSet = sr.enums()
    n, state = load_state(a.work)
    band_s = sr.settings_of({"settings": state["band_settings"]}) if state.get("bands") else None

    def draw(layer, a0, a1, b0, b1, size, elevation):
        mid = (a0 + a1) / 2
        b = model.cad_manager.rebar_layer.add_concentrated_rebar(
            LineSegment2D(Point2D(*layer.to_plan(mid, b1)), Point2D(*layer.to_plan(mid, b0))))
        b.span_set = SpanSet.LONGITUDE if layer.direction == "long" else SpanSet.LATITUDE
        b.slab_face = SlabFace.TOP
        b.bar_type = model.rebars.rebar(size)
        b.elevation_reference = ElevationReference.ABSOLUTE
        b.elevation_from_reference = elevation
        b.ending_anchorage_1 = BarEnd.STRAIGHT
        b.ending_anchorage_2 = BarEnd.STRAIGHT
        b.extent_zone_width = a1 - a0
        b.set_extent_zone_width_fractions(0.5)
        return b

    for name in LAYERS:
        layer = cr.Layer.parse(name)
        old = sr.user_bars(model, layer, sr.owned_footprints(a.work, layer))
        for b in old:
            b.delete()
        groups = [tc.ColumnGroup(**g) for g in state["layers"][name]]
        clusters = [tc.ColumnGroup(**g) for g in state.get("clusters", {}).get(name, [])]
        for g in groups + clusters:
            draw(layer, g.a0, g.a1, g.b0, g.b1, g.size, g.elevation).count = g.count
        bands = [rg.from_dict(b) for b in state.get("bands", {}).get(name, [])]
        for g in bands:
            draw(layer, g.a0, g.a1, g.b0, g.b1, band_s.size, state["band_elevation"][name]).spacing = g.spacing(band_s)
        print(f"{name}: replaced {len(old)} user groups with {len(groups)} column groups"
              + (f", {len(clusters)} groups away from columns" if clusters else "")
              + (f" and {len(bands)} bands" if bands else ""))
    sr.note(a.work, f"plan {n} applied")


def cmd_verify(a) -> dict:
    """Calc, save, report. Returns the scattered leftovers per direction as (real, peaking)."""
    model = sr.live_model(a.port)
    n, state = load_state(a.work)
    path = a.work / f"round-{n}.cpt"
    sr.note(a.work, f"round {n}: calc started")
    secs = sr.calc_and_save(model, path)
    print(f"round {n} (calc+save {secs:.0f}s)")
    left_over = report(a, state, path)
    sr.note(a.work, f"round {n} calc done in {secs:.0f}s")
    return left_over


def cmd_report(a) -> dict:
    """Report the latest saved round again, without calculating (picks up new overrides)."""
    n, state = load_state(a.work)
    rounds = latest(a.work, "round", "cpt")
    print(f"round {rounds}, plan {n} (no calc)")
    return report(a, state, a.work / f"round-{rounds}.cpt")


def report(a, state: dict, path: Path) -> dict:
    """What the program still adds, per direction: (real leftovers away from columns, noise, real over columns).

    Over a column, a leftover whose footprint lies beside the column group's extent is reported as
    "beside" (the engineer widens the group once over it; a second time it is the next strip's bar), not
    as the column still needing bars. Away from columns, noise (``tc.is_noise``: one or two bars up to
    10 ft, or a sliver under 3 ft wide) is counted but not chased: the engineer left 31 such on 2636.
    """
    left_over = {}
    for name in LAYERS:
        layer = cr.Layer.parse(name)
        groups = [tc.ColumnGroup(**g) for g in state["layers"][name]]
        clusters = [tc.ColumnGroup(**g) for g in state.get("clusters", {}).get(name, [])]
        overrides = br.overrides(a.work.parent, name)
        bars, loose, size, beam_bars = gather(path, layer, overrides)
        s = rg.Settings(size=size)
        by_col = {g.column: g for g in groups}
        short = [c for c in bars if not (c.count <= s.peak_bars and c.length <= s.peak_length)]
        beside = [c for c in short if c.column in by_col
                  and min(c.a1, by_col[c.column].a1) - max(c.a0, by_col[c.column].a0) < 0.5 * (c.a1 - c.a0)]
        short = [c for c in short if c not in beside]
        loose, waived = sr.split_waived(loose, sr.load_transitions(state.get("verdicts"), layer))
        noise = [d for d in loose if rg.is_peak(d, s) or tc.is_noise(d)]
        real_loose = [d for d in loose if d not in noise]
        left_over[name] = (real_loose, noise, short + beside)
        left = len(bars) + len(loose)
        print(f"{name}: {len(groups)} column groups, {tc.tons(groups):.1f} tons"
              + (f"; {len(clusters)} groups away from columns, {tc.tons(clusters):.1f} tons" if clusters else "")
              + f"; program left: {left} groups ({len(short)} real over columns, {len(beside)} beside a column group, "
              f"{len(real_loose)} real elsewhere, {left - len(short) - len(beside) - len(real_loose)} noise)")
        if clusters:
            print("   away from columns: " + "; ".join(f"{c} at {k}" for c, k in tc.schedule(clusters)))
        bands = state.get("bands", {}).get(name)
        if bands:
            band_s = sr.settings_of({"settings": state["band_settings"]})
            print(f"   {len(bands)} bands, {band_tons(bands, band_s):.1f} tons: {band_schedule(bands, band_s)}")
        for c in short:
            x, y = layer.to_plan(c.a, c.b)
            print(f"   column at ({x:.1f},{y:.1f}) still needs {c.count}{size} x {c.length:.1f}'")
        for c in beside:
            g = by_col[c.column]
            x, y = layer.to_plan(c.a, c.b)
            gap = max(g.a0 - c.a1, c.a0 - g.a1, 0.0)
            print(f"   beside the group at ({x:.1f},{y:.1f}), {gap:.1f} ft across: {c.count}{size} x {c.length:.1f}' "
                  + ("(group already widened once: the next strip's bar)" if g.widened
                     else "(capturing widens the group once over it and moves it up a count)"))
        for d in real_loose:
            print("   elsewhere", sr.describe(d, layer))
        if beam_bars:
            print("   " + beam_note(beam_bars, layer, overrides))
        for stack in cr.stacks(cr.bars(path, layer, cr.USER)):
            d = stack[0]
            x, y = layer.to_plan((d.a0 + d.a1) / 2, (d.b0 + d.b1) / 2)
            print(f"   STACKED: {len(stack)} copies of {d.count}{d.size} at ({x:.0f},{y:.0f}); run dedupe")
    return left_over


def capture_columns(a, state: dict, name: str, over_columns: list, peaks: list) -> list:
    """Fold leftovers into the column group beside them; returns the peaking bars no column group took.

    Anything the program still adds over a column goes to that column's
    group; a column with no group yet gets one. A peaking bar away from the
    columns goes to a column group within reach, else it is left for the bands.
    """
    base = a.work / "base.cpt"
    layer = cr.Layer.parse(name)
    columns = columns_local(base, layer)
    mesh = cr.Mesh(base)
    groups = [tc.ColumnGroup(**g) for g in state["layers"][name]]
    have = {g.column for g in groups}
    fresh = [c for c in over_columns if c.column not in have]          # a column strip of its own: its own group
    grown, changed, longer, left = tc.capture(groups, [c for c in over_columns if c.column in have] + list(peaks),
                                              a.capture_reach)
    demands = [tc.ColumnBars(g.column, *columns[g.column], g.count, g.a0, g.a1, g.b0, g.b1, g.elevation, g.size)
               for g in grown] + fresh
    on_slab = lambda p, q: mesh.thickness(*layer.to_plan(p, q)) is not None
    retyped = {g.column: g for g in tc.typed(demands, tuple(state["typical"]), on_slab,
                                             tb.end_columns(base, layer), own=frozenset(longer),
                                             widened=frozenset(g.column for g in grown if g.widened))}
    final = [retyped[g.column] if g.column in changed else g for g in groups] + [retyped[c.column] for c in fresh]
    for old in groups:
        new = retyped[old.column]
        if old.column in changed and new.callout() != old.callout():
            x, y = layer.to_plan(*columns[old.column])
            print(f"   ({x:.0f},{y:.0f}) {old.callout()} -> {new.callout()}")
    for c in fresh:
        x, y = layer.to_plan(*columns[c.column])
        print(f"   ({x:.0f},{y:.0f}) new group {retyped[c.column].callout()}")
    state["layers"][name] = [asdict(g) for g in final]
    print(f"{name}: column groups took {len(over_columns) + len(peaks) - len(left)} leftovers; "
          f"{len(final)} column groups, {tc.tons(final):.1f} tons")
    return [d for d in left if not isinstance(d, tc.ColumnBars)]


def cmd_merge_bands(a):
    """One pass: merge neighbouring bands whose spacing is a few steps apart, where it costs little."""
    n, state = load_state(a.work)
    s = sr.settings_of({"settings": dict(state["band_settings"], max_class_jump=a.class_jump)})
    before = json.dumps(state["bands"], sort_keys=True)
    for name in LAYERS:
        groups = [rg.from_dict(b) for b in state["bands"][name]]
        merged = rg.merge_until(list(groups), s, a.merge_budget)
        state["bands"][name] = [asdict(g) for g in merged]
        print(f"{name}: {len(groups)} -> {len(merged)} bands, {sr.tons_of(groups, s):.1f} -> {sr.tons_of(merged, s):.1f} tons: "
              f"{band_schedule(state['bands'][name], s)}")
    if json.dumps(state["bands"], sort_keys=True) == before:
        print("nothing to merge")
        return
    save_state(a.work, n + 1, state, f"plan {n + 1}: bands merged across {a.class_jump} spacing steps")


def cmd_absorb_bands(a, left_over: dict) -> bool:
    """Capture what the program still adds: column groups first, then the bands; writes the next plan."""
    n, state = load_state(a.work)
    s = sr.settings_of({"settings": state["band_settings"]})
    before = json.dumps([state["bands"], state["layers"]], sort_keys=True)
    for name in LAYERS:
        real, peaks, over_columns = left_over[name]
        peaks = capture_columns(a, state, name, over_columns, peaks)
        groups = [rg.from_dict(b) for b in state["bands"][name]]
        groups, unplaced = rg.absorb(groups, real, s)
        groups += rg.seed(unplaced, s)
        groups, left = rg.absorb_peaks(groups, peaks, s)
        groups = rg.merge_until(groups, s, state["band_budget"][name])
        state["bands"][name] = [asdict(g) for g in groups]
        print(f"{name}: absorbed {len(real) - len(unplaced)} real, {len(unplaced)} new, "
              f"{len(peaks) - len(left)} of {len(peaks)} peaking; {len(groups)} bands, {sr.tons_of(groups, s):.1f} tons")
    if json.dumps([state["bands"], state["layers"]], sort_keys=True) == before:
        print("nothing left to absorb")
        return False
    save_state(a.work, n + 1, state, f"plan {n + 1}: leftovers captured by the groups beside them")
    return True


def cmd_run(a):
    if a.typical:
        cmd_plan(a)
    cmd_apply(a)
    cmd_verify(a)


def cmd_dedupe(a):
    """Delete stacked copies of user top bars in the live session, both directions; --calc verifies after."""
    model = sr.live_model(a.port)
    total = 0
    for name in LAYERS:
        layer = cr.Layer.parse(name)
        removed = sr.dedupe_live(model, layer)
        for (a0, a1, b0, b1), callout, n in removed:
            x, y = layer.to_plan((a0 + a1) / 2, (b0 + b1) / 2)
            print(f"{name}: removed {n} stacked {'copy' if n == 1 else 'copies'} of {callout} at ({x:.0f},{y:.0f})")
            total += n
        if not removed:
            print(f"{name}: no stacked copies")
    sr.note(a.work, f"dedupe: removed {total} stacked copies")
    if total and a.calc:
        cmd_verify(a)


def cmd_clusters(a):
    """Count groups for the program top bars away from columns, from the newest round; earlier clusters grow."""
    n, state = load_state(a.work)
    rounds = latest(a.work, "round", "cpt")
    if not rounds:
        raise SystemExit("no round-N.cpt yet: run the column groups first")
    source = a.work / f"round-{rounds}.cpt"
    base = a.work / "base.cpt"
    mesh = cr.Mesh(base)
    state.setdefault("clusters", {})
    state.setdefault("cluster_length", {})
    asked = dict(zip(LAYERS, a.cluster_length or []))
    for name in LAYERS:
        layer = cr.Layer.parse(name)
        overrides = br.overrides(a.work.parent, name)
        _, loose, size, _ = gather(source, layer, overrides)
        loose, _ = sr.split_waived(loose, sr.load_transitions(state.get("verdicts"), layer))
        # the column groups first: a stray alongside one adds to its count, one beside it widens it once
        # (2636: 10#8 to 12#8 and 15#8 over the strays beside two columns), the rest is clustered
        loose = capture_columns(a, state, name, [], loose)
        standard = asked.get(name) or state["cluster_length"].get(name) or tc.standard_length(loose)
        state["cluster_length"][name] = standard
        seeds = []
        for g in (tc.ColumnGroup(**g) for g in state["clusters"].get(name, [])):
            d = cr.Demand(g.a0, g.a1, g.b0, g.b1, g.count, g.size, "seed")
            d.elevation = g.elevation
            seeds.append(d)
        on_slab = lambda p, q: mesh.thickness(*layer.to_plan(p, q)) is not None
        walls = cr.walls(base, layer)
        groups = tc.cluster_groups(seeds + loose, tuple(state["typical"]), standard, size, on_slab, walls)
        state["clusters"][name] = [asdict(g) for g in groups]
        print(f"{name}: {len(groups)} groups away from columns, {tc.tons(groups):.1f} tons, {standard:g}' long: "
              + "; ".join(f"{c} at {k}" for c, k in tc.schedule(groups)))
        for g in groups:
            if g.a1 - g.a0 > 18.0:
                x0, y0 = layer.to_plan(g.a0, g.b0)
                x1, y1 = layer.to_plan(g.a1, g.b1)
                print(f"   run over a wall, {g.a1 - g.a0:.0f} ft at x {min(x0, x1):.0f}-{max(x0, x1):.0f} "
                      f"y {min(y0, y1):.0f}-{max(y0, y1):.0f}: {g.callout()} (about {12 * (g.a1 - g.a0) / g.count:.0f} in); "
                      "the engineer sets these (2636 went one to two spacing steps tighter)")
    save_state(a.work, n + 1, state, f"plan {n + 1}: count groups away from columns, {state['cluster_length']}")


def cmd_run_clusters(a):
    """clusters -> apply -> verify -> the column groups take what is beside them, until nothing real is left."""
    for _ in range(a.rounds):
        cmd_clusters(a)
        cmd_apply(a)
        left_over = cmd_verify(a)
        if not any(real or over for real, _, over in left_over.values()):
            print("nothing real left away from or over the columns; done")
            return
        n, state = load_state(a.work)
        for name in LAYERS:
            real, noise, over = left_over[name]
            capture_columns(a, state, name, over, noise)
        save_state(a.work, n + 1, state, f"plan {n + 1}: column groups took the leftovers beside them")
    print(f"stopped after {a.rounds} rounds; review the last round")


def cmd_run_bands(a):
    """apply -> verify -> absorb until the program adds nothing real away from columns."""
    for _ in range(a.rounds):
        cmd_apply(a)
        left_over = cmd_verify(a)
        if not any(real or peaks or over for real, peaks, over in left_over.values()):
            print("no program bars left; done")
            return
        if not cmd_absorb_bands(a, left_over):
            return
    print(f"stopped after {a.rounds} rounds; review the last round")


def main(argv=None):
    commands = {"options": cmd_options, "plan": cmd_plan, "apply": cmd_apply, "verify": cmd_verify, "run": cmd_run,
                "clusters": cmd_clusters, "run-clusters": cmd_run_clusters, "dedupe": cmd_dedupe,
                "band-options": cmd_band_options, "bands": cmd_bands, "run-bands": cmd_run_bands,
                "report": cmd_report, "merge-bands": cmd_merge_bands}
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=list(commands))
    p.add_argument("--work", required=True, type=Path, help="work folder holding base.cpt (no user top bars, calculated)")
    p.add_argument("--typical", type=int, nargs="+", help="typical bar counts, one list for both directions, e.g. 5 7 10 15 20")
    p.add_argument("--most", type=int, default=5, help="options: longest count list to price (default 5)")
    p.add_argument("--calc", action="store_true", help="dedupe: calc, save and report after removing copies")
    p.add_argument("--cluster-length", type=float, nargs=2, metavar=("LONG", "LAT"),
                   help="clusters: the one bar length per direction, even feet (default: commonest program length)")
    p.add_argument("--band-size", default="#9", help="bar size for the scattered bands, e.g. #7")
    p.add_argument("--option", type=int, nargs=2, metavar=("LONG", "LAT"),
                   help="bands: table row for top-long and top-lat (default: the knee row)")
    p.add_argument("--knee-tons-per-group", type=float, default=0.5)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--verdicts", type=Path, help="bands: verdicts.json from transition_check.py; notch-only bars are waived")
    p.add_argument("--capture-reach", type=float, default=5.0,
                   help="run-bands: feet a column group reaches to take a leftover bar")
    p.add_argument("--class-jump", type=int, default=2, help="merge-bands: spacing steps two merged bands may differ by")
    p.add_argument("--merge-budget", type=float, default=500.0, help="merge-bands: most lb one merge may add")
    p.add_argument("--port", type=int, help="API port (auto-detected when one session runs)")
    a = p.parse_args(argv)
    a.work = a.work.resolve()
    if a.command == "plan" and not a.typical:
        p.error("plan needs --typical")
    marker = a.work / ".working"
    marker.write_text(json.dumps(dict(pid=os.getpid(), t=time.time(), text=f"top bars {a.command}")))
    try:
        commands[a.command](a)
    finally:
        marker.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
