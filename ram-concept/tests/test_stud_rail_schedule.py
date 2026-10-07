"""Controlled tests for grouping stud rail sets into schedule types."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "skills"
sys.path.insert(0, str(SKILLS / "schedule-ram-concept-stud-rails" / "scripts"))

import stud_rail_schedule as srs  # noqa: E402


def row(x, studs, typical, first=None, rails=8):
    first = typical if first is None else first
    return dict(x=x, y=0, rails=rails, studs=studs, first=first, typical=typical, slab=16, comment=" ",
                ft=srs.rail_length(first, typical, studs))


def by_mark(rows):
    out = {}
    for r in rows:
        out.setdefault(r["mk"], []).append(r)
    return out


class ProposeTest(unittest.TestCase):
    def test_rail_length(self):
        self.assertAlmostEqual(srs.rail_length(5.25, 5.25, 12), 5.25)
        self.assertAlmostEqual(srs.rail_length(4.875, 7.25, 4), 2.21875)

    def test_every_type_has_one_real_row_that_covers_it(self):
        rows = [row(1, 8, 6.5), row(2, 8, 7.75), row(3, 12, 5.25), row(4, 20, 4.0), row(5, 16, 5.0),
                row(6, 24, 3.25), row(7, 28, 3.25), row(8, 36, 3.0), row(9, 8, 7.25, 4.875, rails=10), row(10, 16, 4.75, rails=10)]
        types = srs.propose(rows)
        for best, group in types:
            self.assertEqual(sum(1 for r in group if r.get("controlling")), 1)
            self.assertTrue(best.get("controlling"))
            for r in group:
                self.assertTrue(srs.covers(best, r), (best, r))
        self.assertEqual(sum(len(g) for _, g in types), len(rows))
        self.assertEqual({r["rails"] for r in by_mark(rows)[types[-1][0]["mk"]]}, {10})      # rail counts never mix

    def test_same_length_at_two_spacings_stays_two_types(self):
        rows = [row(1, 20, 4.0), row(2, 25, 3.25)]            # 6.67 ft light and 6.77 ft heavy
        self.assertEqual(len(srs.propose(rows)), 2)

    def test_short_light_rails_borrow_a_covering_row_instead_of_splitting(self):
        # rows 1 and 2 are left over below the 1.5 ft step, and the tighter of them has the shorter rail, so neither
        # covers the other. The 12 @ 5.25 row is taken out of the type above to control them.
        rows = [row(1, 8, 6.5), row(2, 8, 6.75), row(3, 8, 7.75), row(4, 12, 5.25), row(5, 20, 4.0)]
        types = srs.propose(rows, step_ft=1.5)
        self.assertEqual(len(types), 2)
        short = next(g for b, g in types if b["studs"] == 12)
        self.assertEqual(sorted(r["x"] for r in short), [1, 2, 4])
        long = next(g for b, g in types if b["studs"] == 20)
        self.assertEqual(sorted(r["x"] for r in long), [3, 5])

    def test_a_wider_step_never_adds_studs_per_column_below_the_design(self):
        rows = [row(i, n, s) for i, (n, s) in enumerate([(8, 6.5), (12, 5.25), (20, 4.0), (24, 3.5), (28, 3.25), (36, 3.0)])]
        designed = sum(r["rails"] * r["studs"] for r in rows)
        for step in (0.5, 1.0, 1.5, 2.0):
            typed = srs.studs_typed(srs.propose([dict(r) for r in rows], step))
            self.assertGreaterEqual(typed, designed)


if __name__ == "__main__":
    unittest.main()
