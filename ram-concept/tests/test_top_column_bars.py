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

    def test_stray_bar_along_the_span_does_not_stretch_the_column_bars(self) -> None:
        main, stray = demand(0, 10, 45, 57.5, 27), demand(2, 8, 35, 48, 1)     # stray overlaps 3 of its 13 ft
        bars, loose = tc.assign([stray, main], [(5, 50)])
        self.assertEqual((bars[0].count, bars[0].b0, bars[0].b1), (27, 45, 57.5))
        self.assertEqual(loose, [stray])

    def test_demand_over_no_column_is_left_loose(self) -> None:
        bars, loose = tc.assign([demand(100, 110, 45, 55, 6)], [(5, 50)])
        self.assertEqual((bars, len(loose)), ([], 1))


class TypedTests(unittest.TestCase):
    def test_smallest_typical_count_that_covers_else_own_count(self) -> None:
        bars = [column_bars(4, 9.5, 0), column_bars(10, 11.6, 1), column_bars(12, 12.2, 2), column_bars(22, 10.4, 3)]
        groups = tc.typed(bars, (10, 15), step=1)
        self.assertEqual([(g.count, g.length, g.kind) for g in groups],
                         [(10, 12, "typical"), (10, 12, "typical"), (15, 13, "typical"), (22, 11, "own")])
        self.assertEqual(tc.schedule(groups), [("10#9 x 12'", 2), ("15#9 x 13'", 1), ("22#9 x 11'", 1)])

    def test_lengths_round_up_to_5_ft_steps(self) -> None:
        bars = [column_bars(4, 9.5, 0), column_bars(10, 11.6, 1), column_bars(12, 12.2, 2), column_bars(22, 10.4, 3)]
        groups = tc.typed(bars, (10, 15))
        self.assertEqual(tc.schedule(groups), [("10#9 x 15'", 2), ("15#9 x 15'", 1), ("22#9 x 15'", 1)])
        self.assertEqual(tc.typed([column_bars(9, 15.07)], (10,))[0].length, 15)
        self.assertEqual(tc.typed([column_bars(9, 15.3)], (10,))[0].length, 20)

    def test_beam_end_columns_keep_their_own_count_and_length(self) -> None:
        bars = [column_bars(8, 11.6, 0), column_bars(9, 16.8, 1), column_bars(28, 21.8, 2)]
        groups = tc.typed(bars, (10, 15), beam_ends=frozenset({1, 2}), step=1)
        self.assertEqual([(g.count, g.length, g.kind) for g in groups],
                         [(10, 12, "typical"), (9, 17, "beam end"), (28, 22, "beam end")])
        self.assertEqual(tc.schedule(groups), [("10#9 x 12'", 1), ("9#9 x 17' (beam end)", 1), ("28#9 x 22' (beam end)", 1)])

    def test_lengthened_columns_keep_their_own_callout(self) -> None:
        bars = [column_bars(8, 11.6, 0), column_bars(9, 22.6, 1)]
        groups = tc.typed(bars, (10, 15), own=frozenset({1}), step=1)
        self.assertEqual([(g.count, g.length, g.kind) for g in groups], [(10, 12, "typical"), (9, 23, "own")])

    def test_an_inch_over_does_not_earn_another_foot(self) -> None:
        self.assertEqual(tc.typed([column_bars(9, 15.07)], (10,), step=1)[0].length, 15)

    def test_bar_keeps_the_program_end_at_a_slab_edge(self) -> None:
        edge = tc.ColumnBars(0, 5, 50, 6, 0, 10, 50, 56, -2.56, "#9")       # slab ends at b = 50
        long_one = column_bars(8, 12, 1)
        groups = tc.typed([edge, long_one], (10,), on_slab=lambda a, b: b >= 50, step=1)
        self.assertEqual((groups[0].b0, groups[0].b1), (50, 62))

    def test_tons_follow_count_length_and_bar_weight(self) -> None:
        groups = tc.typed([column_bars(10, 12)], (10,))
        self.assertAlmostEqual(tc.tons(groups), 10 * 15 * 3.4 / 2000)


class ZoneTests(unittest.TestCase):
    """The bars sit at 12 in on centre: the zone is count x spacing wide, not the program's strip."""

    def test_ten_bars_at_12_in_take_a_10_ft_zone_on_the_column(self) -> None:
        strip = tc.ColumnBars(0, 7, 50, 10, 0, 14, 44, 56, -2.56, "#9")        # column mid-strip, 14 ft strip
        g = tc.typed([strip], (10,))[0]
        self.assertEqual((g.a0, g.a1, g.spacing), (0, 14, 1.0))                 # the strip is kept for capture
        self.assertEqual(g.zone(), (2, 12))

    def test_an_edge_column_zone_starts_at_the_edge(self) -> None:
        edge = tc.ColumnBars(0, 0.5, 50, 10, 0, 14, 44, 56, -2.56, "#9")
        self.assertEqual(tc.typed([edge], (10,))[0].zone(), (0, 10))

    def test_a_count_wider_than_the_strip_overhangs_both_sides(self) -> None:
        narrow = tc.ColumnBars(0, 3, 50, 10, 0, 8, 44, 56, -2.56, "#9")
        self.assertEqual(tc.typed([narrow], (10,))[0].zone(), (-1, 9))

    def test_tighter_spacing_narrows_the_zone(self) -> None:
        strip = tc.ColumnBars(0, 7, 50, 12, 0, 14, 44, 56, -2.56, "#9")
        self.assertEqual(tc.typed([strip], (12,), spacing=0.75)[0].zone(), (2.5, 11.5))

    def test_no_spacing_spreads_over_the_strip_as_before(self) -> None:
        strip = tc.ColumnBars(0, 7, 50, 10, 0, 14, 44, 56, -2.56, "#9")
        self.assertEqual(tc.typed([strip], (10,), spacing=0)[0].zone(), (0, 14))
        self.assertEqual(tc.ColumnGroup(0, 10, 12, "typical", 0, 14, 44, 56, -2.56, "#9").zone(), (0, 14))

    def test_a_captured_bar_widens_the_zone_by_one_spacing(self) -> None:
        g = tc.ColumnGroup(0, 10, 12, "typical", 0, 14, 44, 56, -2.56, "#9", 1.0, 7)
        grown, _, _, _ = tc.capture([g], [demand(3, 6, 48, 52, 1)])
        self.assertEqual((grown[0].count, grown[0].zone()), (11, (1.5, 12.5)))


class OptionTests(unittest.TestCase):
    def test_more_callouts_never_cost_more(self) -> None:
        bars = [column_bars(n, 10 + n % 3, i) for i, n in enumerate([2, 4, 5, 8, 8, 9, 10, 12, 14, 27])]
        rows = tc.type_options(bars)
        self.assertEqual(rows[0]["schedule"], [(27, 15, 10)])          # 12 ft demand -> 15 ft callout
        tons = [r["tons"] for r in rows]
        self.assertEqual(tons, sorted(tons, reverse=True))
        self.assertEqual(sum(k for _, _, k in rows[2]["schedule"]), 10)



class CaptureTests(unittest.TestCase):
    def group(self, count, column=0, a0=0.0, a1=10.0, b0=44.0, b1=56.0, kind="typical"):
        return tc.ColumnGroup(column, count, b1 - b0, kind, a0, a1, b0, b1, -2.56, "#9")

    def test_a_single_bar_alongside_adds_to_the_count(self) -> None:
        groups, changed, longer, left = tc.capture([self.group(4, kind="beam end")], [demand(3, 6, 48, 52, 1)])
        self.assertEqual((groups[0].count, groups[0].length, changed, longer, left), (5, 12, {0}, set(), []))

    def test_a_bar_beside_the_extent_is_the_next_strips_bar(self) -> None:
        stray = demand(10.4, 14, 47, 51, 1)
        groups, changed, _, left = tc.capture([self.group(15)], [stray])
        self.assertEqual((groups[0].count, groups[0].a0, groups[0].a1, changed, left), (15, 0, 10, set(), [stray]))

    def test_a_bar_past_the_end_lengthens_the_group_without_adding_bars(self) -> None:
        groups, changed, longer, _ = tc.capture([self.group(8)], [demand(2, 8, 58.5, 66.5, 1)])
        self.assertEqual((groups[0].count, groups[0].b0, groups[0].b1, groups[0].length), (8, 44, 66.5, 22.5))
        self.assertEqual((changed, longer), ({0}, {0}))

    def test_the_nearest_group_takes_it_and_far_bars_are_left(self) -> None:
        near, far = self.group(10, 0), self.group(10, 1, a0=30.0, a1=40.0)
        stray, lost = demand(31, 33, 48, 52, 2), demand(100, 104, 48, 52, 1)
        groups, changed, _, left = tc.capture([near, far], [stray, lost])
        self.assertEqual(([g.count for g in groups], changed, left), ([10, 12], {1}, [lost]))

    def test_the_input_groups_are_not_changed(self) -> None:
        original = self.group(10)
        tc.capture([original], [demand(3, 6, 48, 52, 1)])
        self.assertEqual(original.count, 10)

    def test_a_typical_group_that_needs_more_moves_to_the_next_typical(self) -> None:
        groups, changed, longer, _ = tc.capture([self.group(10, 0), self.group(15, 1, a0=30.0, a1=40.0, b0=43.5, b1=56.5)],
                                                [demand(3, 6, 48, 52, 1)])
        bars = [tc.ColumnBars(g.column, 5, 50, g.count, g.a0, g.a1, g.b0, g.b1, g.elevation, g.size) for g in groups]
        typed = tc.typed(bars, (10, 15), own=frozenset(longer), step=1)
        self.assertEqual([g.callout() for g in typed], ["15#9 x 13'", "15#9 x 13'"])


if __name__ == "__main__":
    unittest.main()
