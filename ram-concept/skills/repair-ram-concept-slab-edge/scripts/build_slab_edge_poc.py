#!/usr/bin/env python3
"""Build and mesh a separate RAM Concept slab-edge proof model."""

from __future__ import annotations

import argparse
import csv
import json
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
from ram_concept.line_segment_2D import LineSegment2D  # noqa: E402
from ram_concept.model import DesignCode, StructureType  # noqa: E402
from ram_concept.point_2D import Point2D  # noqa: E402
from ram_concept.polygon_2D import Polygon2D  # noqa: E402
from ram_concept.slab_area import SlabAreaBehavior  # noqa: E402


def read_walls(path: Path) -> list[dict[str, float | int]]:
    walls: list[dict[str, float | int]] = []
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream, delimiter="\t"):
            if row and row[0] == "WALL":
                walls.append(
                    {
                        "uid": int(row[3]),
                        "label": int(row[4]),
                        "start_x": float(row[5]),
                        "start_y": float(row[6]),
                        "end_x": float(row[7]),
                        "end_y": float(row[8]),
                        "thickness": float(row[9]),
                    }
                )
    if not walls:
        raise ValueError("No walls were found in the geometry export.")
    return walls


def build_model(
    polygon: list[dict[str, float]],
    walls: list[dict[str, float | int]],
    output_path: Path,
) -> dict[str, object]:
    concept = Concept.start_concept(
        headless=True,
        start_timeout_seconds=90,
        inactivity_timeout_seconds=3600,
    )
    model = None
    try:
        model = concept.new_model()
        model.setup_new_model(
            DesignCode.ACI318_19US,
            StructureType.ELEVATED,
        )

        units = model.units
        units.set_US_user_units()
        saved_units = units.get_units()
        units.set_US_API_units()

        signs = model.signs
        signs.set_standard_signs()
        saved_signs = signs.get_signs()
        signs.set_positive_signs()

        concrete = model.concretes.concretes[0]
        cad_manager = model.cad_manager
        structure_layer = cad_manager.structure_layer

        default_slab = cad_manager.default_slab_area
        default_slab.thickness = 10.0
        default_slab.toc = 0.0
        default_slab.behavior = SlabAreaBehavior.TWO_WAY_SLAB
        default_slab.concrete = concrete
        default_slab.priority = 1
        default_slab.r_axis = 0.0

        slab_polygon = Polygon2D(
            [Point2D(point["x"], point["y"]) for point in polygon]
        )
        structure_layer.add_slab_area(slab_polygon)

        default_wall = cad_manager.default_wall
        default_wall.below_slab = True
        default_wall.compressible = True
        default_wall.concrete = concrete
        default_wall.height = 120.0
        default_wall.fixed_near = False
        default_wall.fixed_far = False
        default_wall.shear_wall = False
        default_wall.use_specified_LLR_parameters = False

        for wall_record in walls:
            default_wall.thickness = float(wall_record["thickness"])
            structure_layer.add_wall(
                LineSegment2D(
                    Point2D(
                        float(wall_record["start_x"]),
                        float(wall_record["start_y"]),
                    ),
                    Point2D(
                        float(wall_record["end_x"]),
                        float(wall_record["end_y"]),
                    ),
                )
            )

        model.generate_mesh()

        slab_count = len(structure_layer.slab_areas)
        wall_count = len(structure_layer.walls_below)
        mesh_element_count = len(
            model.cad_manager.element_layer.slab_elements
        )

        units.set_units(saved_units)
        signs.set_signs(saved_signs)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        model.save_file(str(output_path.resolve()))

        return {
            "output": str(output_path.resolve()),
            "slab_count": slab_count,
            "wall_count": wall_count,
            "mesh_slab_element_count": mesh_element_count,
            "design_code": "ACI 318-19 (US defaults)",
            "structure_type": "Elevated",
            "model_units": "US user units; inches during API creation",
            "proof_slab_thickness_in": 10.0,
            "proof_wall_height_in": 120.0,
        }
    finally:
        try:
            if model is not None:
                concept.shut_down()
            else:
                concept.shut_down()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repair_json", type=Path)
    parser.add_argument("geometry_tsv", type=Path)
    parser.add_argument("output_cpt", type=Path)
    parser.add_argument("validation_json", type=Path)
    args = parser.parse_args()

    with args.repair_json.open(encoding="utf-8") as stream:
        repair = json.load(stream)

    if repair["repaired_wall_footprint_failures"] != 0:
        raise ValueError(
            "The repair proposal has remaining wall-footprint failures."
        )

    walls = read_walls(args.geometry_tsv)
    validation = build_model(
        repair["repaired_polygon"],
        walls,
        args.output_cpt,
    )
    validation.update(
        {
            "repair_source": str(args.repair_json.resolve()),
            "clearance_past_wall_face_in": repair["clearance"],
            "source_vertices": repair["source_vertex_count"],
            "repaired_vertices": repair["repaired_vertex_count"],
            "source_wall_footprint_failures": repair[
                "source_wall_footprint_failures"
            ],
            "repaired_wall_footprint_failures": repair[
                "repaired_wall_footprint_failures"
            ],
        }
    )

    args.validation_json.parent.mkdir(parents=True, exist_ok=True)
    with args.validation_json.open("w", encoding="utf-8") as stream:
        json.dump(validation, stream, indent=2)
        stream.write("\n")
    print(json.dumps(validation, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
