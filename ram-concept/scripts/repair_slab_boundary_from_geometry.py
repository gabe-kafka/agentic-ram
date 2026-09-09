#!/usr/bin/env python3
"""Compatibility launcher for the canonical slab-edge repair skill."""

from pathlib import Path
import runpy


TARGET = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "repair-ram-concept-slab-edge"
    / "scripts"
    / "repair_slab_boundary_from_geometry.py"
)
runpy.run_path(str(TARGET), run_name="__main__")
