"""Tests for live RAM Concept API attach helpers. No Concept.exe required."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "attach-ram-concept-api"
    / "scripts"
    / "attach_live_concept.py"
)
SPEC = importlib.util.spec_from_file_location("attach_live_concept", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AttachLiveConceptTests(unittest.TestCase):
    def test_parses_port_flag_from_command_line(self) -> None:
        command = (
            r'"C:\Program Files\Bentley\Engineering\RAM Concept'
            r'\RAM Concept 2025\Concept.exe" -apiServerWithGui '
            r"-version 25.0.0 -port 1999 -inactivityTimeout 3600"
        )
        self.assertEqual(MODULE.parse_port_from_command_line(command), 1999)
        self.assertTrue(MODULE.command_has_api_server(command))
        self.assertFalse(MODULE.command_has_api_server(r"C:\Concept.exe"))

    def test_maps_exe_folder_to_python_api(self) -> None:
        concept_root = Path(r"C:\Program Files\Bentley\Engineering\RAM Concept")
        for version in ("RAM Concept 2025", "RAM Concept 2024"):
            exe = concept_root / version / "Concept.exe"
            python_dir = concept_root / version / "python"
            if not (python_dir / "ram_concept" / "concept.py").is_file():
                continue
            self.assertEqual(MODULE.python_api_dir_for_exe(str(exe)), python_dir)
            return
        self.skipTest("Installed RAM Concept Python API was not found.")

    def test_parses_netstat_listeners_by_pid(self) -> None:
        text = "\n".join(
            [
                "  TCP    127.0.0.1:1999    0.0.0.0:0    LISTENING    4242",
                "  TCP    0.0.0.0:445       0.0.0.0:0    LISTENING    4",
                "  TCP    127.0.0.1:1999    127.0.0.1:9  ESTABLISHED  4242",
            ]
        )
        self.assertEqual(MODULE.parse_netstat_listeners(text), {4242: [1999], 4: [445]})

    def test_parses_rss_launched_cpt_path(self) -> None:
        command = (
            r'"C:\Program Files\Bentley\Engineering\RAM Concept'
            r'\RAM Concept 2025\concept.exe" -updateRSS '
            r'"2636_02_gravity_slab.ram" -workdir '
            r'"C:\ProgramData\Bentley\Engineering\RAM Structural System\Working"'
            r' -import None -results None -story 1027 '
            r'"2636_02_gravity_slab.cpt1027E"'
        )
        self.assertEqual(
            MODULE.parse_open_cpt_from_command_line(command),
            r"C:\ProgramData\Bentley\Engineering\RAM Structural System\Working"
            r"\2636_02_gravity_slab.cpt1027E",
        )
        self.assertFalse(MODULE.command_has_api_server(command))

    def test_extracts_cpt_from_window_title(self) -> None:
        self.assertEqual(
            MODULE.extract_cpt_from_title(
                r"C:\Models\2636_02_gravity_slab.cpt - RAM Concept"
            ),
            r"C:\Models\2636_02_gravity_slab.cpt",
        )
        self.assertEqual(
            MODULE.extract_cpt_from_title("2636_02_gravity_slab.cpt - RAM Concept"),
            "2636_02_gravity_slab.cpt",
        )

    def test_relaunch_hint_keeps_live_window_untouched(self) -> None:
        hint = MODULE.relaunch_hint(
            {"open_cpt": r"C:\Models\2636_02_gravity_slab.cpt"}
        )
        self.assertIn("--start-gui", hint)
        self.assertIn(r"C:\Models\2636_02_gravity_slab.cpt", hint)
        self.assertNotIn("taskkill", hint.lower())


if __name__ == "__main__":
    unittest.main()
