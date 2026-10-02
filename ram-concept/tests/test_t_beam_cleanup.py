"""Controlled tests for the beam rules and the "no bar called out" override record."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "skills"
sys.path.insert(0, str(SKILLS / "simplify-ram-concept-rebar" / "scripts"))
sys.path.insert(0, str(SKILLS / "clean-up-ram-concept-t-beams" / "scripts"))

import beam_rules as br  # noqa: E402
import rebar_groups as rg  # noqa: E402


def demand(a0, a1, b0, b1, count, size="#7"):
    return rg.Demand(a0, a1, b0, b1, count, size)


class BeamColumnTests(unittest.TestCase):
    BEAMS = [((100.0, 50.0), (100.0, 80.0), 2.0), ((100.0, 80.0), (100.0, 110.0), 2.0)]   # two bays, north-south
    NORTH, EAST = (0.0, 1.0), (1.0, 0.0)

    def test_beam_on_both_sides_parallel_to_the_bars(self) -> None:
        self.assertTrue(br.beam_runs_through((100.0, 80.0), self.NORTH, self.BEAMS))

    def test_column_at_the_end_of_the_beam_keeps_its_bars(self) -> None:
        self.assertFalse(br.beam_runs_through((100.0, 50.0), self.NORTH, self.BEAMS))
        self.assertFalse(br.beam_runs_through((100.0, 110.0), self.NORTH, self.BEAMS))
        self.assertEqual(br.beam_sides((100.0, 50.0), self.NORTH, self.BEAMS), 1)
        self.assertEqual(br.beam_sides((100.0, 80.0), self.NORTH, self.BEAMS), 2)
        self.assertEqual(br.beam_sides((120.0, 80.0), self.NORTH, self.BEAMS), 0)

    def test_bars_across_the_beam_are_not_affected(self) -> None:
        self.assertFalse(br.beam_runs_through((100.0, 80.0), self.EAST, self.BEAMS))

    def test_column_off_the_beam_line_is_not_affected(self) -> None:
        self.assertFalse(br.beam_runs_through((120.0, 80.0), self.NORTH, self.BEAMS))

    def test_columns_are_classed_per_bar_direction(self) -> None:
        columns = [(100.0, 50.0), (100.0, 80.0), (100.0, 110.0), (120.0, 80.0)]
        self.assertEqual(br.beam_columns(columns, self.BEAMS, "long"), {0: 1, 1: 2, 2: 1})
        self.assertEqual(br.beam_columns(columns, self.BEAMS, "lat"), {})


class BeamBarTests(unittest.TestCase):
    BEAM = [(99.0, 101.0, 50.0, 80.0)]                        # 2 ft wide, runs along the bars

    def test_bars_inside_a_beam_are_a_class_of_their_own(self) -> None:
        self.assertTrue(br.in_beam(demand(99.1, 100.8, 52, 78, 12), self.BEAM))
        self.assertFalse(br.in_beam(demand(95, 105, 52, 78, 12), self.BEAM))      # a slab band across the beam line
        self.assertFalse(br.in_beam(demand(99.1, 100.8, 85, 110, 12), self.BEAM)) # past the end of the beam
        d = demand(99.1, 100.8, 52.0, 77.6, 12)
        d.elevation = -33.56
        g = br.beam_group(d)
        self.assertEqual((g["count"], g["b1"] - g["b0"], g["elevation"]), (12, 26, -33.56))

    def test_a_bar_reaching_the_end_of_the_beam_is_a_beam_end_bar(self) -> None:
        self.assertTrue(br.at_beam_end(demand(99.1, 100.8, 74.5, 80, 18), self.BEAM))
        self.assertTrue(br.at_beam_end(demand(99.1, 100.8, 50, 58, 12), self.BEAM))
        self.assertFalse(br.at_beam_end(demand(99.1, 100.8, 60, 70.5, 3), self.BEAM))     # mid-span
        self.assertFalse(br.at_beam_end(demand(60, 70, 74.5, 80, 18), self.BEAM))         # not in the beam

    def test_mid_span_leftover_adds_to_the_beams_own_bars(self) -> None:
        group = br.beam_group(demand(99.1, 100.8, 52, 78, 12))
        grown = br.grow_beam_groups([group], [demand(99.2, 100.7, 60, 70.5, 3)], self.BEAM)
        self.assertEqual([(g["count"], g["b0"], g["b1"]) for g in grown], [(15, 52, 78)])
        self.assertEqual(group["count"], 12)                                              # input untouched

    def test_mid_span_leftover_in_a_beam_with_no_bars_gets_its_own_group(self) -> None:
        beams = self.BEAM + [(139.0, 141.0, 50.0, 80.0)]
        group = br.beam_group(demand(99.1, 100.8, 52, 78, 12))
        grown = br.grow_beam_groups([group], [demand(139.2, 140.7, 60, 70.5, 2)], beams)
        self.assertEqual([(g["count"], g["b1"] - g["b0"]) for g in grown], [(12, 26), (2, 11)])


class OverrideTests(unittest.TestCase):
    def test_override_is_recorded_once_and_found_by_location(self) -> None:
        with tempfile.TemporaryDirectory() as job:
            job = Path(job)
            self.assertEqual(br.overrides(job, "top-long"), [])
            self.assertTrue(br.add_override(job, "top-long", 269.0, 111.0, "beam carries this moment", "rule"))
            self.assertFalse(br.add_override(job, "top-long", 269.3, 111.2, "again", "engineer"))
            self.assertTrue(br.add_override(job, "top-lat", 191.0, 111.0, "beam carries this moment", "rule"))
            found = br.overrides(job, "top-long")
            self.assertEqual([(o["x"], o["y"], o["callout"]) for o in found], [(269.0, 111.0, "none")])
            self.assertEqual(br.override_at(found, 271.0, 114.0)["reason"], "beam carries this moment")
            self.assertIsNone(br.override_at(found, 269.0, 120.0))                        # outside the 6 ft reach
            self.assertIsNone(br.override_at(br.overrides(job, "bot-long"), 269.0, 111.0))


if __name__ == "__main__":
    unittest.main()
