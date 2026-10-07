"""Controlled tests for the one-way shear tools: joining regions into zones, the markup page fit."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "skills"
sys.path.insert(0, str(SKILLS / "design-ram-concept-one-way-shear" / "scripts"))

import markup_plan as mp  # noqa: E402
import shear_regions as sr  # noqa: E402


def region(x0, y0, x1, y1, legs=2, spacing=3.0):
    along = "x" if abs(x1 - x0) >= abs(y1 - y0) else "y"
    lo, hi = (min(x0, x1), max(x0, x1)) if along == "x" else (min(y0, y1), max(y0, y1))
    return dict(x0=x0, y0=y0, x1=x1, y1=y1, along=along, lo=lo, hi=hi, across=y0 if along == "x" else x0,
                mx=(x0 + x1) / 2, my=(y0 + y1) / 2, length=hi - lo, legs=legs, spacing=spacing, sdir=1 if along == "x" else 2)


class ChainsTest(unittest.TestCase):
    def test_short_region_at_the_face_joins_the_one_beyond(self):
        zones = sr.chains([region(10, 50, 11.2, 50, spacing=1.5), region(11.2, 50, 15, 50, spacing=4.0)])
        self.assertEqual(len(zones), 1)
        self.assertAlmostEqual(zones[0]["lo"], 10)
        self.assertAlmostEqual(zones[0]["hi"], 15)
        self.assertEqual(zones[0]["spacing"], 1.5)          # the zone carries its tightest spacing
        self.assertEqual(len(zones[0]["pieces"]), 2)

    def test_parallel_lines_and_gaps_stay_apart(self):
        zones = sr.chains([region(10, 50, 12, 50), region(10, 53, 12, 53), region(14, 50, 16, 50), region(20, 10, 20, 14)])
        self.assertEqual(len(zones), 4)

    def test_beam_web_is_between_the_ends_only(self):
        beams = [(100.0, 50.0, 130.0, 50.0, 20.0)]
        self.assertTrue(sr.on_beam(beams, 115, 50.5))
        self.assertFalse(sr.on_beam(beams, 132, 50))        # just past the end: slab, not web
        self.assertFalse(sr.on_beam(beams, 115, 53))


class MarkupFitTest(unittest.TestCase):
    def test_fit_recovers_the_page_scale_and_origin(self):
        targets = [(50.0, 54.0), (99.0, 54.0), (148.0, 84.0), (245.0, 218.0), (299.0, 285.0), (157.0, 307.0)]
        s, ox, oy = 0.2, 12.0, 340.0
        marks = [((X - ox) / s, (oy - Y) / s) for X, Y in targets]
        fs, fox, foy, matched, worst = mp.fit(marks, targets)
        self.assertEqual(matched, len(targets))
        self.assertAlmostEqual(fs, s, places=6)
        self.assertAlmostEqual(fox, ox, places=4)
        self.assertAlmostEqual(foy, oy, places=4)
        self.assertLess(worst, 1e-6)

    def test_marks_are_read_by_colour_and_the_page_frame_is_dropped(self):
        red, magenta = [1.0, 0.0, 0.0], [1.0, 0.0, 1.0]
        page = dict(annots=[
            dict(type="Square", rect=[500, 500, 560, 560], stroke=red),
            dict(type="Square", rect=[700, 500, 760, 560], stroke=red),
            dict(type="Square", rect=[900, 500, 960, 560], stroke=red),
            dict(type="Square", rect=[410, 10, 2500, 1700], stroke=red),          # page frame
            dict(type="Square", rect=[100, 100, 160, 160], stroke=red),           # legend sample, left of 400
            dict(type="Square", rect=[600, 700, 650, 780], stroke=magenta),
            dict(type="Polygon", rect=[800, 800, 820, 820], stroke=red, vertices=[[800, 810], [808, 820], [820, 800]]),
            dict(type="Ink", rect=[900, 895, 1000, 905], stroke=[0.0, 1.0, 0.0], vertices=[[900, 900], [950, 900], [1000, 900]]),
        ])
        marks = mp.read_marks(page, ignore_left_of=400)
        self.assertEqual(len(marks["ssr"]), 3)
        self.assertEqual(marks["boxes"], [[600, 700, 650, 780]])
        self.assertEqual(len(marks["checks"]), 1)
        self.assertEqual(len(marks["green"]), 1)


if __name__ == "__main__":
    unittest.main()
