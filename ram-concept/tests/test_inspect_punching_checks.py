from __future__ import annotations

import importlib.util
import sqlite3
import unittest
import uuid
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "inspect-punching-checks.py"
)
SPEC = importlib.util.spec_from_file_location(
    "inspect_punching_checks",
    SCRIPT_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "out" / "test-temp"


def create_checkpoint(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE SsrSystem (
                UID INTEGER,
                Name TEXT,
                StudArea REAL,
                Fy REAL
            );
            CREATE TABLE PunchCheck (
                UID INTEGER,
                Number INTEGER,
                Name TEXT,
                Point0 TEXT,
                MaxRadius REAL,
                SsrDesignDesired INTEGER,
                SsrSystem INTEGER,
                ConnectionType TEXT,
                EdgeTreatment TEXT
            );
            CREATE TABLE SsrSet (
                UID INTEGER,
                Number INTEGER,
                LocationPoint TEXT,
                Point0 TEXT,
                Point1 TEXT,
                SsrSystem INTEGER,
                StudSpacingFirst REAL,
                StudSpacingTypical REAL,
                MaxStudCount INTEGER,
                StudCount TEXT
            );
            CREATE TABLE SlabOpening (
                UID INTEGER,
                Number INTEGER,
                MultiPoint TEXT
            );
            CREATE TABLE SlabArea (
                UID INTEGER,
                Number INTEGER,
                MultiPoint TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO SsrSystem VALUES (?, ?, ?, ?)",
            (36, '3/4" SSR', 1.0, 60.0),
        )
        connection.executemany(
            "INSERT INTO PunchCheck VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    100,
                    0,
                    "Punching Check #1",
                    "[0][0]",
                    24384.0,
                    1,
                    36,
                    "auto",
                    "sector voids",
                ),
                (
                    101,
                    1,
                    "Punching Check #2",
                    "[30480][0]",
                    24384.0,
                    1,
                    36,
                    "auto",
                    "sector voids",
                ),
            ],
        )
        connection.execute(
            "INSERT INTO SsrSet VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                200,
                0,
                "[0][0]",
                "[[1000][0]][[-1000][0]]",
                "[[24000][0]][[-24000][0]]",
                36,
                1700.0,
                1700.0,
                11,
                "[11][11]",
            ),
        )
        connection.execute(
            "INSERT INTO SlabOpening VALUES (?, ?, ?)",
            (
                300,
                0,
                "[[15000][-1000]][[17000][-1000]]"
                "[[17000][1000]][[15000][1000]]",
            ),
        )
        connection.execute(
            "INSERT INTO SlabArea VALUES (?, ?, ?)",
            (
                400,
                0,
                "[[-30000][-30000]][[30000][-30000]]"
                "[[30000][30000]][[-30000][30000]]",
            ),
        )
        connection.commit()
    finally:
        connection.close()


class PunchingCheckpointInspectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)

    def test_inspection_correlates_layouts_and_flags_radius_limit(
        self,
    ) -> None:
        checkpoint = TEST_TEMP_ROOT / f"fixture-{uuid.uuid4().hex}.cpt"
        self.addCleanup(checkpoint.unlink, missing_ok=True)
        try:
            create_checkpoint(checkpoint)
            original_hash = MODULE.sha256(checkpoint)

            result = MODULE.inspect_checkpoint(checkpoint)

            self.assertEqual(MODULE.sha256(checkpoint), original_hash)
            self.assertEqual(result["summary"]["punch_check_count"], 2)
            self.assertEqual(
                result["summary"]["checks_with_generated_ssr_layouts"],
                1,
            )
            self.assertEqual(
                result["summary"]["checks_without_generated_ssr_layouts"],
                1,
            )
            self.assertEqual(
                result["summary"]["near_limit_check_numbers"],
                [1],
            )
            self.assertEqual(
                result["summary"]["no_layout_check_numbers"],
                [2],
            )
            self.assertAlmostEqual(
                result["checks"][0]["maximum_search_radius_ft"],
                8.0,
            )
            self.assertAlmostEqual(
                result["checks"][0]["maximum_generated_rail_reach_ft"],
                24000.0 / 3048.0,
            )
            self.assertEqual(
                result["checks"][0]["maximum_generated_stud_count"],
                11,
            )
            self.assertEqual(
                result["summary"][
                    "slab_opening_within_search_radius_check_numbers"
                ],
                [1, 2],
            )
            self.assertEqual(
                result["summary"][
                    "slab_boundary_within_search_radius_check_numbers"
                ],
                [2],
            )
        finally:
            checkpoint.unlink(missing_ok=True)

    def test_inspection_rejects_non_sqlite_file(self) -> None:
        checkpoint = TEST_TEMP_ROOT / f"not-a-model-{uuid.uuid4().hex}.cpt"
        self.addCleanup(checkpoint.unlink, missing_ok=True)
        try:
            checkpoint.write_bytes(b"not sqlite")

            with self.assertRaises(MODULE.ConceptCheckpointError):
                MODULE.inspect_checkpoint(checkpoint)
        finally:
            checkpoint.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
