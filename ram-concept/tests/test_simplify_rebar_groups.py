"""Controlled tests for the RAM Concept rebar simplification grouping logic."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "simplify-ram-concept-rebar"
    / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIRECTORY))

import rebar_groups as rg  # noqa: E402
from cpt_reader import Layer  # noqa: E402


def demand(a0, a1, b0, b1, count, size="#7"):
    return rg.Demand(a0, a1, b0, b1, count, size)


class RebarGroupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = rg.Settings(size="#7")

    def test_spacing_step_covers_density(self) -> None:
        # #7 @ 12 in gives 0.60 in^2/ft; a hair more needs the next step (9 in)
        self.assertEqual(self.s.spacings[rg.step_for(0.60, self.s)], 12)
        self.assertEqual(self.s.spacings[rg.step_for(0.61, self.s)], 9)
        self.assertEqual(self.s.spacings[rg.step_for(9.0, self.s)], 4)

    def test_peaking_is_few_short_bars(self) -> None:
        self.assertTrue(rg.is_peak(demand(0, 4, 0, 3.5, 1), self.s))
        self.assertFalse(rg.is_peak(demand(0, 4, 0, 12, 1), self.s))
        self.assertFalse(rg.is_peak(demand(0, 20, 0, 4, 8), self.s))

    def test_adjacent_demands_merge_within_budget(self) -> None:
        groups = rg.seed([demand(0, 10, 0, 16, 7), demand(12, 22, 0, 16, 7)], self.s)
        merged = rg.merge_until(groups, self.s, budget_lb=500)
        self.assertEqual(len(merged), 1)
        self.assertEqual((merged[0].a0, merged[0].a1), (0, 22))

    def test_zero_budget_keeps_costly_merge_apart(self) -> None:
        groups = rg.seed([demand(0, 10, 0, 16, 7), demand(25, 35, 0, 16, 7)], self.s)
        self.assertEqual(len(rg.merge_until(groups, self.s, budget_lb=0)), 2)

    def test_spacing_classes_too_far_apart_do_not_merge(self) -> None:
        light = demand(0, 10, 0, 16, 5)           # 18 in
        heavy = demand(11, 21, 0, 16, 30)         # 4 in
        groups = rg.merge_until(rg.seed([light, heavy], self.s), self.s, budget_lb=1e9)
        self.assertEqual(len(groups), 2)

    def test_options_trade_groups_for_tonnage(self) -> None:
        demands = [demand(x, x + 8, 0, 14, 5) for x in range(0, 200, 12)]
        plans = rg.options(demands, self.s)
        counts = [p["groups"] for p in plans]
        tons = [p["tons"] for p in plans]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(tons, sorted(tons))
        picked = rg.pick(plans, target_groups=5, max_tons=tons[-1])
        self.assertLessEqual(picked["tons"], tons[-1])

    def test_knee_stops_before_tonnage_jumps(self) -> None:
        table = lambda rows: [dict(groups=g, tons=t) for g, t in rows]
        bottom = table([(85, 12.5), (59, 13.0), (48, 13.8), (38, 15.0), (33, 16.8), (25, 21.7)])
        top = table([(113, 21.7), (94, 22.1), (83, 22.9), (70, 25.1), (54, 30.7), (47, 35.1), (36, 49.7)])
        self.assertEqual(rg.knee(bottom)["groups"], 33)
        self.assertEqual(rg.knee(top)["groups"], 54)
        self.assertEqual(rg.knee(top, max_tons_per_group=0.1)["groups"], 83)

    def test_absorb_grows_cheapest_host_with_development(self) -> None:
        host = rg.seed([demand(0, 20, 0, 16, 14)], self.s)[0]   # 18 in
        far = rg.seed([demand(100, 120, 0, 16, 14)], self.s)[0]
        leftover = demand(5, 9, 14, 18, 2)
        groups, unplaced = rg.absorb([host, far], [leftover], self.s)
        self.assertEqual(unplaced, [])
        grown = groups[0]
        self.assertEqual(grown.b1, 20)                       # 18 + 2 ft development
        self.assertLess(grown.spacing(self.s), 18)           # tightened at least one step
        self.assertEqual(groups[1], far)

    def test_absorb_leaves_isolated_leftover_unplaced(self) -> None:
        host = rg.seed([demand(0, 20, 0, 16, 14)], self.s)[0]
        _, unplaced = rg.absorb([host], [demand(60, 64, 50, 60, 3)], self.s)
        self.assertEqual(len(unplaced), 1)

    def test_peak_beside_group_stretches_it_without_tightening(self) -> None:
        host = rg.seed([demand(0, 20, 0, 16, 13)], self.s)[0]   # 18 in
        peak = demand(20.5, 24, 6, 11, 1)
        groups, left = rg.absorb_peaks([host], [peak], self.s)
        self.assertEqual(left, [])
        self.assertEqual((groups[0].a0, groups[0].a1), (0, 24))
        self.assertEqual(groups[0].spacing(self.s), 18)

    def test_band_is_continued_over_a_chain_of_zones_in_line(self) -> None:
        s = rg.Settings(continue_reach=50.0)
        band = rg.Group(40, 60, 80, 100, 2)                       # 20 ft wide, bars 20 ft long
        chain = [demand(42, 46, 82, 96, 1), demand(44, 48, 84, 98, 1)]   # beside is not the case: in line, further across
        chain = [demand(60 + 8, 60 + 12, 82, 96, 1), demand(60 + 20, 60 + 24, 84, 98, 1)]
        groups, left = rg.absorb_peaks([band], chain, s)
        self.assertEqual(left, [])
        self.assertEqual((groups[0].a0, groups[0].a1, groups[0].step), (40, 84, 2))   # continued across, same spacing
        self.assertEqual((groups[0].b0, groups[0].b1), (80, 100))                     # bar length unchanged
        far = demand(60 + 60, 60 + 64, 82, 96, 1)                 # 60 ft across: no band in line
        off = demand(50, 54, 120, 124, 1)                         # 20 ft past the bar ends: not in line
        groups, left = rg.absorb_peaks([band], [far, off], s)
        self.assertEqual(len(left), 2)

    def test_continuation_never_crosses_a_beam_and_a_spike_is_a_peak(self) -> None:
        s = rg.Settings(continue_reach=50.0)
        band = rg.Group(40, 60, 80, 100, 2)
        zone = demand(70, 74, 82, 96, 1)                         # in line, 10 ft across
        beam = (64, 66, 60, 120)                                 # a beam between them, along the bars
        self.assertEqual(rg.absorb_peaks([band], [zone], s, beams=[beam])[1], [zone])
        self.assertEqual(rg.absorb_peaks([band], [zone], s)[1], [])
        self.assertTrue(rg.is_peak(demand(0, 3, 0, 3.5, 3), s))       # 3 bars x 3.5 ft: a spike
        self.assertFalse(rg.is_peak(demand(0, 3, 0, 8, 3), s))        # 3 bars x 8 ft: real demand

    def test_peak_inside_or_far_from_groups_is_left_listed(self) -> None:
        host = rg.seed([demand(0, 20, 0, 16, 14)], self.s)[0]
        inside, far = demand(5, 9, 4, 9, 1), demand(90, 94, 4, 9, 1)
        groups, left = rg.absorb_peaks([host], [inside, far], self.s)
        self.assertEqual(groups, [host])
        self.assertEqual([d.tag for d in left], ["inside a group", "no band in line within 5 ft across, 5 ft along"])

    def test_patch_over_a_band_is_dropped_to_one_spacing(self) -> None:
        s = rg.Settings()
        band = rg.Group(0, 100, 0, 20, 3)          # 6 in over 100 ft
        patch = rg.Group(40, 50, 2, 18, 4)         # 4 in laid over 10 ft of it
        apart = rg.Group(120, 130, 0, 20, 4)       # not touching
        out = rg.one_spacing([band, patch, apart])
        self.assertEqual(len(out), 2)
        region = next(g for g in out if g.a0 == 0)
        self.assertEqual((region.a1, region.step), (100, 3))
        self.assertEqual(len(rg.merge_until([band, patch, apart], s, 0)), 2)

    def test_callout_counts_bars_across_zone(self) -> None:
        g = rg.Group(0, 10, 0, 16, step=1)                   # 12 in over 10 ft
        self.assertEqual(g.callout(self.s, "B"), "(11)#7x16@12B")


class LayerTests(unittest.TestCase):
    def test_longitude_bars_run_along_plan_y(self) -> None:
        layer = Layer.parse("bot-long")
        self.assertEqual((layer.face, layer.letter), ("bottom", "B"))
        self.assertEqual(layer.to_local(3, 7), (3, 7))

    def test_latitude_bars_run_along_plan_x(self) -> None:
        layer = Layer.parse("top-lat")
        self.assertEqual(layer.letter, "T")
        self.assertEqual(layer.to_local(3, 7), (7, 3))
        self.assertEqual(layer.to_plan(*layer.to_local(3, 7)), (3, 7))


if __name__ == "__main__":
    unittest.main()
