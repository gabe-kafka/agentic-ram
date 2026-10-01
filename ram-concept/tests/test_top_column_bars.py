"""Controlled tests for the per-column top bar logic."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "skills"
sys.path.insert(0, str(SKILLS / "simplify-ram-concept-rebar" / "scripts"))
sys.path.insert(0, str(SKILLS / "simplify-ram-concept-top-rebar" / "scripts"))

import rebar_groups as rg  # noqa: E402
import top_columns as tc  # noqa: E402


def demand(a0, a1, b0, b1, count, size="#9"):
    d = rg.Demand(a0, a1, b0, b1, count, size)
    d.elevation = -2.56
    return d


def column_bars(count, length, column=0):
    return tc.ColumnBars(column, 5, 50, count, 0, 10, 50 - length / 2, 50 + length / 2, -2.56, "#9")


class AssignTests(unittest.TestCase):
    def test_demand_goes_to_the_column_under_it(self) -> None:
        columns = [(5, 50), (35, 50)]
        bars, loose = tc.assign([demand(0, 10, 45, 55, 8), demand(31, 39, 44, 56, 12)], columns)
        self.assertEqual([(c.column, c.count) for c in bars], [(0, 8), (1, 12)])
        self.assertEqual(loose, [])

    def test_two_demands_at_one_column_add_up(self) -> None:
        bars, _ = tc.assign([demand(0, 6, 45, 55, 4), demand(4, 10, 46, 57, 3)], [(5, 50)])
        self.assertEqual((bars[0].count, bars[0].a0, bars[0].a1, bars[0].b0, bars[0].b1), (7, 0, 10, 45, 57))

    def test_demand_over_no_column_is_left_loose(self) -> None:
        bars, loose = tc.assign([demand(100, 110, 45, 55, 6)], [(5, 50)])
        self.assertEqual((bars, len(loose)), ([], 1))


class TypedTests(unittest.TestCase):
    def test_smallest_typical_count_that_covers_else_own_count(self) -> None:
        bars = [column_bars(4, 9.5, 0), column_bars(10, 11.6, 1), column_bars(12, 12.2, 2), column_bars(22, 10.4, 3)]
        groups = tc.typed(bars, (10, 15))
        self.assertEqual([(g.count, g.length, g.kind) for g in groups],
                         [(10, 12, "typical"), (10, 12, "typical"), (15, 13, "typical"), (22, 11, "own")])
        self.assertEqual(tc.schedule(groups), [("10#9 x 12'", 2), ("15#9 x 13'", 1), ("22#9 x 11'", 1)])

    def test_an_inch_over_does_not_earn_another_foot(self) -> None:
        self.assertEqual(tc.typed([column_bars(9, 15.07)], (10,))[0].length, 15)

    def test_bar_keeps_the_program_end_at_a_slab_edge(self) -> None:
        edge = tc.ColumnBars(0, 5, 50, 6, 0, 10, 50, 56, -2.56, "#9")       # slab ends at b = 50
        long_one = column_bars(8, 12, 1)
        groups = tc.typed([edge, long_one], (10,), on_slab=lambda a, b: b >= 50)
        self.assertEqual((groups[0].b0, groups[0].b1), (50, 62))

    def test_tons_follow_count_length_and_bar_weight(self) -> None:
        groups = tc.typed([column_bars(10, 12)], (10,))
        self.assertAlmostEqual(tc.tons(groups), 10 * 12 * 3.4 / 2000)


class OptionTests(unittest.TestCase):
    def test_more_callouts_never_cost_more(self) -> None:
        bars = [column_bars(n, 10 + n % 3, i) for i, n in enumerate([2, 4, 5, 8, 8, 9, 10, 12, 14, 27])]
        rows = tc.type_options(bars)
        self.assertEqual(rows[0]["schedule"], [(27, 12, 10)])
        tons = [r["tons"] for r in rows]
        self.assertEqual(tons, sorted(tons, reverse=True))
        self.assertEqual(sum(k for _, _, k in rows[2]["schedule"]), 10)


if __name__ == "__main__":
    unittest.main()
