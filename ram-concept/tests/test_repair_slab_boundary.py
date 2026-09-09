"""Controlled tests for the RAM Concept slab-boundary repair geometry."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "repair-ram-concept-slab-edge"
    / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIRECTORY))

from repair_slab_boundary_from_geometry import (  # noqa: E402
    Point,
    Wall,
    coverage_failures,
    rebuild_polygon,
    select_edge_repairs,
)


class SlabBoundaryRepairTests(unittest.TestCase):
    def test_moves_slab_past_exterior_wall_face(self) -> None:
        polygon = [
            Point(0.0, 0.0),
            Point(100.0, 0.0),
            Point(100.0, 100.0),
            Point(0.0, 100.0),
        ]
        wall = Wall(
            index=0,
            uid=1,
            label=1,
            start=Point(10.0, 6.0),
            end=Point(90.0, 6.0),
            thickness=14.0,
            eccentricity=1,
            eccentric_distance=0.0,
        )

        self.assertEqual(len(coverage_failures(polygon, [wall], 1.0)), 1)
        shifts, repairs = select_edge_repairs(
            polygon,
            [wall],
            clearance=1.0,
            search_distance=31.0,
            parallel_tolerance=1.0e-3,
        )
        repaired = rebuild_polygon(polygon, shifts)

        self.assertEqual(len(repairs), 1)
        self.assertAlmostEqual(repairs[0].outward_shift, 2.0)
        self.assertAlmostEqual(min(point.y for point in repaired), -2.0)
        self.assertEqual(
            coverage_failures(repaired, [wall], clearance=1.0),
            [],
        )


if __name__ == "__main__":
    unittest.main()
