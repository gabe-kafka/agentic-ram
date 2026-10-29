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
        groups = tc.typed(bars, (10, 15))
        self.assertEqual([(g.count, g.length, g.kind) for g in groups],
                         [(10, 12, "typical"), (10, 12, "typical"), (15, 14, "typical"), (22, 12, "own")])
        self.assertEqual(tc.schedule(groups), [("10#9 x 12'", 2), ("15#9 x 14'", 1), ("22#9 x 12'", 1)])

    def test_beam_end_columns_keep_their_own_count_and_length(self) -> None:
        bars = [column_bars(8, 11.6, 0), column_bars(9, 16.8, 1), column_bars(28, 21.8, 2)]
        groups = tc.typed(bars, (10, 15), beam_ends=frozenset({1, 2}))
        self.assertEqual([(g.count, g.length, g.kind) for g in groups],
                         [(10, 12, "typical"), (9, 18, "beam end"), (28, 22, "beam end")])
        self.assertEqual(tc.schedule(groups), [("10#9 x 12'", 1), ("9#9 x 18' (beam end)", 1), ("28#9 x 22' (beam end)", 1)])

    def test_lengthened_columns_keep_their_own_callout(self) -> None:
        bars = [column_bars(8, 11.6, 0), column_bars(9, 22.6, 1)]
        groups = tc.typed(bars, (10, 15), own=frozenset({1}))
        self.assertEqual([(g.count, g.length, g.kind) for g in groups], [(10, 12, "typical"), (9, 24, "own")])

    def test_lengths_are_even_feet_and_an_inch_over_does_not_earn_more(self) -> None:
        self.assertEqual(tc.typed([column_bars(9, 16.07)], (10,))[0].length, 16)
        self.assertEqual(tc.typed([column_bars(9, 15.07)], (10,))[0].length, 16)
        self.assertEqual(tc.typed([column_bars(9, 16.3)], (10,))[0].length, 18)

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



class CaptureTests(unittest.TestCase):
    def group(self, count, column=0, a0=0.0, a1=10.0, b0=44.0, b1=56.0, kind="typical"):
        return tc.ColumnGroup(column, count, b1 - b0, kind, a0, a1, b0, b1, -2.56, "#9")

    def test_a_single_bar_alongside_adds_to_the_count(self) -> None:
        groups, changed, longer, left = tc.capture([self.group(4, kind="beam end")], [demand(3, 6, 48, 52, 1)])
        self.assertEqual((groups[0].count, groups[0].length, changed, longer, left), (5, 12, {0}, set(), []))

    def test_a_bar_beside_the_extent_widens_the_group_once(self) -> None:
        stray = demand(10.4, 14, 47, 51, 1)
        groups, changed, _, left = tc.capture([self.group(15)], [stray])
        self.assertEqual((groups[0].count, groups[0].a0, groups[0].a1, groups[0].widened, changed, left),
                         (16, 0, 14, True, {0}, []))
        again = demand(14.5, 18, 47, 51, 2)                      # the next strip's bar: left
        groups, changed, _, left = tc.capture(groups, [again])
        self.assertEqual((groups[0].count, groups[0].a1, changed, left), (16, 14, set(), [again]))

    def test_a_bar_far_beside_the_extent_is_left(self) -> None:
        stray = demand(16, 20, 47, 51, 1)
        groups, changed, _, left = tc.capture([self.group(15)], [stray])
        self.assertEqual((groups[0].count, groups[0].a1, changed, left), (15, 10, set(), [stray]))

    def test_typed_keeps_the_widened_flag(self) -> None:
        bars = [column_bars(11, 14, 0), column_bars(6, 12, 1)]
        typed = tc.typed(bars, (10, 15), widened=frozenset({0}))
        self.assertEqual([(g.callout(), g.widened) for g in typed], [("15#9 x 14'", True), ("10#9 x 12'", False)])

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
        typed = tc.typed(bars, (10, 15), own=frozenset(longer))
        self.assertEqual([g.callout() for g in typed], ["15#9 x 14'", "15#9 x 14'"])


class SharedOptionTests(unittest.TestCase):
    def test_one_count_list_serves_both_directions(self) -> None:
        by_layer = {"top-long": [column_bars(5, 12, 0), column_bars(5, 12, 1), column_bars(14, 14, 2)],
                    "top-lat": [column_bars(7, 10, 0), column_bars(19, 14, 1)]}
        rows = tc.type_options_shared(by_layer, most=3)
        self.assertEqual([r["types"] for r in rows], [1, 2, 3])
        self.assertEqual(rows[1]["counts"], [7, 19])                 # 5s and 7 share 7; 14 and 19 share 19
        self.assertEqual(rows[1]["per"]["top-long"]["schedule"], [(7, 12, 2, "typical"), (19, 14, 1, "typical")])
        self.assertLessEqual(rows[2]["tons"], rows[1]["tons"])
        self.assertLessEqual(rows[1]["tons"], rows[0]["tons"])

    def test_the_largest_count_is_always_listed(self) -> None:
        rows = tc.type_options_shared({"top-long": [column_bars(5, 12), column_bars(30, 16)]}, most=1)
        self.assertEqual(rows[0]["counts"], [30])
        self.assertEqual(rows[0]["per"]["top-long"]["schedule"], [(30, 16, 2, "typical")])


class ClusterTests(unittest.TestCase):
    """The engineer's count groups away from columns, 2636 building 1 (2026-10-28)."""

    # local axes: a across the bars, b along them (2636 latitude: a is plan y, b is plan x)

    def test_touching_program_bars_make_one_group_at_the_next_typical_count(self) -> None:
        bars = [demand(107.6, 115.4, 67.2, 75.7, 3, "#8"), demand(115.4, 123.1, 67.2, 75.7, 3, "#8")]
        groups = tc.cluster_groups(bars, (5, 7, 10, 15, 20), 12, "#8")
        self.assertEqual([(g.callout(), g.kind, round(g.a1 - g.a0, 1)) for g in groups], [("7#8 x 12'", "cluster", 15.5)])
        self.assertAlmostEqual((groups[0].b0 + groups[0].b1) / 2, (67.2 + 75.7) / 2)

    def test_a_small_sum_stays_exact_and_a_big_one_takes_the_covering_typical(self) -> None:
        small = tc.cluster_groups([demand(89.1, 92.9, 36.8, 47.8, 2, "#8"), demand(92.9, 96.6, 37, 48, 2, "#8")],
                                  (5, 7, 10, 15, 20), 12, "#8")
        big = tc.cluster_groups([demand(99.7, 107.9, 127.2, 138.7, 9, "#8"), demand(97.5, 99.7, 126.2, 138.7, 3, "#8"),
                                 demand(95.2, 96.6, 126.2, 138.2, 2, "#8"), demand(90.6, 95.2, 129.6, 135.1, 1, "#8")],
                                (5, 7, 10, 15, 20), 12, "#8")
        self.assertEqual(([g.count for g in small], [g.count for g in big]), ([4], [15]))

    def test_bars_apart_across_or_along_stay_separate(self) -> None:
        bars = [demand(90, 100, 0, 12, 3, "#8"), demand(102, 110, 0, 12, 3, "#8"), demand(90, 100, 20, 32, 3, "#8")]
        self.assertEqual(len(tc.cluster_groups(bars, (5, 7), 12, "#8")), 3)

    def test_a_chain_wider_than_a_strip_is_cut_at_its_widest_gap(self) -> None:
        middle = [demand(75.4, 80.2, 127.3, 135.3, 1, "#8"), demand(80.6, 86.1, 127.6, 134.6, 2, "#8"),
                  demand(86.1, 88.4, 127.6, 136.1, 1, "#8"), demand(89.1, 90.6, 128.7, 136.2, 2, "#8"),
                  demand(90.6, 92.9, 125.9, 136.9, 1, "#8")]
        column = [demand(95.2, 96.6, 126.2, 138.2, 2, "#8"), demand(97.5, 99.7, 126.2, 138.7, 3, "#8"),
                  demand(99.7, 107.9, 127.2, 138.7, 9, "#8")]
        bridge = [demand(90.6, 95.2, 129.6, 135.1, 1, "#8")]
        groups = sorted(tc.cluster_groups(middle + bridge + column, (5, 7, 10, 15, 20), 12, "#8"), key=lambda g: g.a0)
        self.assertEqual([(round(g.a0, 1), round(g.a1, 1), g.count) for g in groups],
                         [(89.1, 96.6, 7), (97.5, 107.9, 15)])          # the noise-only piece at 75-88 is left
        wall = [((84.0, 131.0), (102.0, 131.0))]                         # a wall across the bars does not make this a run
        self.assertEqual(len(tc.cluster_groups(middle + bridge + column, (5, 7, 10, 15, 20), 12, "#8", walls=wall)), 2)

    def test_a_run_over_a_wall_stays_whole_at_its_densest_bars_spacing(self) -> None:
        bars = [demand(126.9, 134.8, 94.9, 107.4, 10, "#8"), demand(134.8, 137.4, 94.9, 107.4, 4, "#8"),
                demand(138.1, 142.4, 94.9, 107.4, 6, "#8"), demand(143.6, 147.0, 95.1, 106.6, 5, "#8")]
        wall = [((131.0, 102.0), (156.0, 102.0))]
        groups = tc.cluster_groups(bars, (5, 7, 10, 15, 20), 14, "#8", walls=wall)
        self.assertEqual([(g.count, g.length, round(g.a1 - g.a0, 1)) for g in groups], [(31, 14, 20.1)])   # 4 over 2.6 ft
        self.assertEqual(len(tc.cluster_groups(bars, (5, 7, 10, 15, 20), 14, "#8")), 2)                   # no wall: cut

    def test_noise_alone_gets_no_group_but_a_seed_is_kept(self) -> None:
        noise = demand(62.3, 68.8, 50.1, 54.0, 1, "#8")
        self.assertEqual(tc.cluster_groups([noise], (5, 7), 12, "#8"), [])
        seed = demand(60, 72, 50, 54, 2, "#8")
        seed.tag = "seed"
        self.assertEqual([g.callout() for g in tc.cluster_groups([seed], (5, 7), 12, "#8")], ["2#8 x 12'"])
        grown = tc.cluster_groups([seed, demand(72.5, 76, 50.5, 58, 4, "#8")], (5, 7), 12, "#8")
        self.assertEqual([g.callout() for g in grown], ["7#8 x 12'"])

    def test_noise_joins_a_real_bar_beside_it(self) -> None:
        pair, lone = demand(91.8, 101.3, 217.1, 227.8, 2, "#8"), demand(95.0, 100.0, 226.0, 231.0, 1, "#8")
        self.assertEqual([g.callout() for g in tc.cluster_groups([pair, lone], (5, 7), 10, "#8")], ["3#8 x 10'"])

    def test_an_edge_sliver_is_set_aside(self) -> None:
        sliver = demand(141.2, 143.6, 270.2, 281.2, 3, "#8")
        edge = lambda a, b: a < 144.0
        self.assertEqual(tc.cluster_groups([sliver], (5, 7), 12, "#8", on_slab=edge), [])
        self.assertEqual(len(tc.cluster_groups([sliver], (5, 7), 12, "#8")), 1)

    def test_noise_is_a_lone_bar_to_ten_feet_or_a_pair_to_seven(self) -> None:
        self.assertTrue(tc.is_noise(demand(0, 5, 0, 9.5, 1, "#8")))
        self.assertTrue(tc.is_noise(demand(0, 4, 0, 6.5, 2, "#8")))
        self.assertFalse(tc.is_noise(demand(0, 5, 0, 9.5, 2, "#8")))
        self.assertFalse(tc.is_noise(demand(0, 7, 0, 5, 3, "#8")))

    def test_standard_length_is_the_commonest_real_program_length(self) -> None:
        bars = [demand(0, 8, 0, 11.5, 4, "#8"), demand(0, 8, 0, 12, 3, "#8"), demand(0, 8, 0, 13.5, 3, "#8"),
                demand(0, 4, 0, 6, 1, "#8")]
        self.assertEqual(tc.standard_length(bars), 12)

    def test_schedule_lists_clusters_last(self) -> None:
        col = tc.ColumnGroup(0, 5, 12, "typical", 0, 7.5, 0, 12, -1.5, "#8")
        away = tc.ColumnGroup(-1, 7, 12, "cluster", 20, 35, 0, 12, -1.5, "#8")
        self.assertEqual(tc.schedule([away, col]), [("5#8 x 12'", 1), ("7#8 x 12' (away from columns)", 1)])


if __name__ == "__main__":
    unittest.main()
