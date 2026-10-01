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
