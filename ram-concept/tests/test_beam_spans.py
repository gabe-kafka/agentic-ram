"""Controlled tests for finding design spans along beams and classifying T or L."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "set-ram-concept-beam-strips" / "scripts"))

import beam_spans as bs  # noqa: E402

BEAM = ((100.0, 50.0), (100.0, 80.0), 2.0)          # north-south beam, 2 ft wide


class BeamAlongTests(unittest.TestCase):
    def test_span_on_the_beam_line_is_found(self) -> None:
        self.assertIs(bs.beam_along(((100.0, 52.0), (100.0, 78.0)), [BEAM]), BEAM)

    def test_span_crossing_the_beam_is_not_along_it(self) -> None:
        self.assertIsNone(bs.beam_along(((85.0, 65.0), (115.0, 65.0)), [BEAM]))

    def test_parallel_span_a_bay_away_is_not_along_it(self) -> None:
        self.assertIsNone(bs.beam_along(((110.0, 52.0), (110.0, 78.0)), [BEAM]))

    def test_span_past_the_end_of_the_beam_is_not_along_it(self) -> None:
        self.assertIsNone(bs.beam_along(((100.0, 90.0), (100.0, 110.0)), [BEAM]))


class BeamKindTests(unittest.TestCase):
    SPAN = ((100.0, 52.0), (100.0, 78.0))

    def test_slab_on_both_sides_is_a_t_beam(self) -> None:
        self.assertEqual(bs.beam_kind(self.SPAN, BEAM, lambda x, y: True), "T")

    def test_slab_on_one_side_is_an_l_beam(self) -> None:
        self.assertEqual(bs.beam_kind(self.SPAN, BEAM, lambda x, y: x < 100), "L")
        self.assertEqual(bs.beam_kind(self.SPAN, BEAM, lambda x, y: x > 100), "L")


if __name__ == "__main__":
    unittest.main()
