#!/usr/bin/env python3
"""Reopen and validate a saved RAM Concept slab-edge proof model."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_CONCEPT_API = Path(
    r"C:\Program Files\Bentley\Engineering\RAM Concept"
    r"\RAM Concept 2024\python"
)
sys.path.insert(0, str(SCRIPT_DIRECTORY / "api_vendor"))
sys.path.insert(1, str(DEFAULT_CONCEPT_API))

from ram_concept.concept import Concept  # noqa: E402

from repair_slab_boundary_from_geometry import (  # noqa: E402
    Point,
    Wall,
    coverage_failures,
    validate_polygon,
)


def polygon_points(slab_area) -> list[Point]:
    return [
        Point(float(point.x), float(point.y))
        for point in slab_area.location.points
    ]


def model_walls(wall_entities) -> list[Wall]:
    walls: list[Wall] = []
    for index, entity in enumerate(wall_entities):
        location = entity.location
        walls.append(
            Wall(
                index=index,
                uid=index,
                label=index,
                start=Point(
                    float(location.start_point.x),
                    float(location.start_point.y),
                ),
                end=Point(
                    float(location.end_point.x),
                    float(location.end_point.y),
                ),
                thickness=float(entity.thickness),
                eccentricity=1,
                eccentric_distance=0.0,
            )
        )
    return walls


def cyclic_maximum_delta(
    expected: list[Point],
    actual: list[Point],
) -> float:
    if len(expected) != len(actual):
        return math.inf

    best = math.inf
    count = len(expected)
    for reverse in (False, True):
        candidate = list(reversed(actual)) if reverse else actual
        for offset in range(count):
            maximum = max(
                math.hypot(
                    expected[index].x
                    - candidate[(index + offset) % count].x,
                    expected[index].y
                    - candidate[(index + offset) % count].y,
                )
                for index in range(count)
            )
            best = min(best, maximum)
    return best


def validate_saved_model(
    model_path: Path,
    expected_polygon: list[Point],
    clearance: float,
) -> dict[str, object]:
    concept = Concept.start_concept(
        headless=True,
        start_timeout_seconds=90,
        inactivity_timeout_seconds=3600,
    )
    try:
        model = concept.open_file(str(model_path.resolve()))
        units = model.units
        saved_units = units.get_units()
        units.set_US_API_units()
        try:
            structure_layer = model.cad_manager.structure_layer
            slab_areas = structure_layer.slab_areas
            walls = model_walls(structure_layer.walls_below)
            if len(slab_areas) != 1:
                raise ValueError(
                    f"Expected one slab area; reopened model has "
                    f"{len(slab_areas)}."
                )

            actual_polygon = polygon_points(slab_areas[0])
            validate_polygon(actual_polygon)
            failures = coverage_failures(
                actual_polygon,
                walls,
                clearance,
            )
            mesh_count = len(
                model.cad_manager.element_layer.slab_elements
            )
            maximum_delta = cyclic_maximum_delta(
                expected_polygon,
                actual_polygon,
            )
        finally:
            units.set_units(saved_units)

        return {
            "fresh_process_reopen": "passed",
            "reopened_slab_count": len(slab_areas),
            "reopened_wall_count": len(walls),
            "reopened_polygon_vertices": len(actual_polygon),
            "reopened_mesh_slab_element_count": mesh_count,
            "reopened_wall_footprint_failures": len(failures),
            "maximum_saved_coordinate_delta_in": maximum_delta,
            "coordinate_acceptance_tolerance_in": 0.004,
            "coordinate_check": (
                "passed" if maximum_delta <= 0.004 else "failed"
            ),
        }
    finally:
        try:
            concept.shut_down()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_cpt", type=Path)
    parser.add_argument("repair_json", type=Path)
    parser.add_argument("validation_json", type=Path)
    args = parser.parse_args()

    with args.repair_json.open(encoding="utf-8") as stream:
        repair = json.load(stream)
    expected_polygon = [
        Point(float(record["x"]), float(record["y"]))
        for record in repair["repaired_polygon"]
    ]

    reopened = validate_saved_model(
        args.model_cpt,
        expected_polygon,
        float(repair["clearance"]),
    )
    if reopened["reopened_wall_footprint_failures"] != 0:
        raise ValueError("The reopened model does not cover every wall.")
    if reopened["coordinate_check"] != "passed":
        raise ValueError(
            "The reopened slab polygon differs from the repair proposal."
        )
    if reopened["reopened_mesh_slab_element_count"] <= 0:
        raise ValueError("The reopened model has no saved slab mesh.")

    if args.validation_json.exists():
        with args.validation_json.open(encoding="utf-8") as stream:
            validation = json.load(stream)
    else:
        validation = {}
    validation["reopen_validation"] = reopened

    args.validation_json.parent.mkdir(parents=True, exist_ok=True)
    with args.validation_json.open("w", encoding="utf-8") as stream:
        json.dump(validation, stream, indent=2)
        stream.write("\n")
    print(json.dumps(reopened, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
