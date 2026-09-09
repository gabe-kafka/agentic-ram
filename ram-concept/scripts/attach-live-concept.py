#!/usr/bin/env python3
"""Compatibility launcher for the canonical live Concept API attach skill."""

from pathlib import Path
import runpy


TARGET = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "attach-ram-concept-api"
    / "scripts"
    / "attach_live_concept.py"
)
runpy.run_path(str(TARGET), run_name="__main__")
