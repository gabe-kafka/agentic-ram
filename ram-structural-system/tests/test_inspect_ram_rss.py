from __future__ import annotations

import importlib.util
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "inspect-ram-rss.py"
SPEC = importlib.util.spec_from_file_location("inspect_ram_rss", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def ram_field(name: str, value: int) -> str:
    encoded = struct.pack("<I", value).hex().upper()
    return f'<field name="{name}">{encoded}</field>'


def load_property(
    label: str,
    *,
    dead: float,
    live: float,
    assignments: int,
    uid: int,
) -> bytes:
    record = bytearray(72)
    record[:20] = label.encode("ascii").ljust(20, b"\0")
    struct.pack_into("<f", record, 20, dead)
    struct.pack_into("<f", record, 32, live)
    struct.pack_into("<I", record, 40, MODULE.UNREDUCIBLE_LIVE_TYPE)
    struct.pack_into("<I", record, 44, assignments)
    struct.pack_into("<I", record, 52, uid)
    return bytes(record)


class InspectRamRssTests(unittest.TestCase):
    def make_archive(self, path: Path) -> None:
        ram = (
            "<ram>"
            + ram_field("NumFlrTypes", 1)
            + ram_field("NumStories", 1)
            + ram_field("nNumGravColumns", 1)
            + ram_field("nNumGravWalls", 1)
            + ram_field("NumSLoadProps", 1)
            + ram_field("NumLLoadProps", 1)
            + ram_field("NumPLoadProps", 1)
            + "</ram>"
        ).encode("ascii")

        floor = bytearray(MODULE.FLOOR_RECORD_SIZE)
        floor[:4] = b"1st\0"
        struct.pack_into("<I", floor, 24, 1)
        struct.pack_into("<I", floor, 28, 1)
        struct.pack_into("<I", floor, 52, 1)
        struct.pack_into("<I", floor, 56, 1)
        struct.pack_into("<I", floor, 60, 1)

        story = bytearray(MODULE.STORY_RECORD_SIZE)
        struct.pack_into("<I", story, 0, 1)
        story[4:10] = b"First\0"
        struct.pack_into("<f", story, 28, 120.0)
        struct.pack_into("<I", story, 52, 1)
        struct.pack_into("<I", story, 56, 1)

        column = bytearray(MODULE.COLUMN_RECORD_SIZE)
        struct.pack_into("<dd", column, 0, 120.0, 240.0)
        struct.pack_into("<I", column, 44, 7)
        column[48:54] = b"24x16\0"

        wall = bytearray(MODULE.WALL_RECORD_SIZE)
        struct.pack_into("<dddd", wall, 0, 0.0, 0.0, 120.0, 0.0)
        struct.pack_into("<I", wall, 52, 9)
        struct.pack_into("<f", wall, 56, 14.0)

        section = bytearray(MODULE.SECTION_RECORD_SIZE)
        section[:6] = b"24x16\0"
        struct.pack_into("<f", section, 20, 16.0)
        struct.pack_into("<f", section, 24, 24.0)
        struct.pack_into("<f", section, 60, 0.7)
        struct.pack_into("<f", section, 156, 1.0)
        struct.pack_into("<f", section, 160, 1.0)

        properties = (
            load_property(
                "Residential",
                dead=20.0 / MODULE.SURFACE_PSF_FACTOR,
                live=40.0 / MODULE.SURFACE_PSF_FACTOR,
                assignments=1,
                uid=1017,
            )
            + load_property(
                "EW1",
                dead=2.2 / MODULE.LINE_KLF_FACTOR,
                live=1.15 / MODULE.LINE_KLF_FACTOR,
                assignments=1,
                uid=1016,
            )
            + load_property(
                "Balcony Point",
                dead=2.186,
                live=2.73,
                assignments=1,
                uid=1015,
            )
        )
        points = [
            (0.0, 0.0),
            (120.0, 0.0),
            (120.0, 120.0),
            (0.0, 120.0),
            (12.0, 12.0),
            (108.0, 12.0),
            (60.0, 60.0),
        ]
        pol = b"".join(struct.pack("<dd", x, y) for x, y in points)
        lod = struct.pack("<5I", 4, 0, 0, 1, 1011) + struct.pack(
            "<5I", 2, 4, 0, 2, 2010
        ) + struct.pack("<5I", 1, 6, 0, 3, 3009)

        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("model.ram", ram)
            archive.writestr("model.flt", floor)
            archive.writestr("model.sty", story)
            archive.writestr("model.c3d", column)
            archive.writestr("model.w3d", wall)
            archive.writestr("model.sec", section)
            archive.writestr("model.lpt", properties)
            archive.writestr("model.pol", pol)
            archive.writestr("model.lod", lod)

    def test_archive_relationships_and_line_coordinates(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[1] / "out") as directory:
            path = Path(directory) / "model.rss"
            self.make_archive(path)
            report = MODULE.analyze_rss(path)

        self.assertTrue(all(check["passed"] for check in report["checks"]))
        self.assertEqual(report["global_counts"]["gravity_columns"], 1)
        self.assertEqual(report["global_counts"]["gravity_walls"], 1)
        line = next(
            placement
            for placement in report["load_placements"]
            if placement["category"] == "line"
        )
        self.assertEqual(line["property_label"], "EW1")
        self.assertEqual(line["points_ft"], [(1.0, 1.0), (9.0, 1.0)])
        point_property = report["load_properties"]["point"][0]
        self.assertEqual(point_property["units"], "kip")
        self.assertAlmostEqual(point_property["dead"], 2.186, places=5)

    def test_segment_correlation_finds_line_and_parallel_wall(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[1] / "out") as directory:
            path = Path(directory) / "model.rss"
            self.make_archive(path)
            report = MODULE.analyze_rss(path)

        correlation = MODULE.correlate_segment(
            ((1.0, 1.0), (9.0, 1.0)),
            report["load_placements"],
            report["walls"],
            0.001,
        )
        self.assertEqual(correlation["exact_line_matches"][0]["property"], "EW1")
        self.assertEqual(correlation["nearest_parallel_walls"][0]["number"], 9)


if __name__ == "__main__":
    unittest.main()
