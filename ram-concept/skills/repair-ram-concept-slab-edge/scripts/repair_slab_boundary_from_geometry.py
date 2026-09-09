#!/usr/bin/env python3
"""Propose a guarded slab-boundary repair from exported geometry.

The input is the tab-separated interchange produced by
RamSlabGeometryExporter.cs. All input coordinates and command-line distances
are inches. The output JSON contains the original and repaired slab polygons.

This script does not open or modify a RAM Structural System or RAM Concept
model.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


EPSILON = 1.0e-6


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Point") -> "Point":
        return Point(self.x - other.x, self.y - other.y)

    def scaled(self, factor: float) -> "Point":
        return Point(self.x * factor, self.y * factor)


@dataclass(frozen=True)
class Wall:
    index: int
    uid: int
    label: int
    start: Point
    end: Point
    thickness: float
    eccentricity: int
    eccentric_distance: float


@dataclass(frozen=True)
class EdgeRepair:
    edge_index: int
    wall_uid: int
    wall_label: int
    current_offset: float
    required_offset: float
    outward_shift: float
    overlap: float


def dot(first: Point, second: Point) -> float:
    return first.x * second.x + first.y * second.y


def cross(first: Point, second: Point) -> float:
    return first.x * second.y - first.y * second.x


def length(vector: Point) -> float:
    return math.hypot(vector.x, vector.y)


def unit(vector: Point) -> Point:
    magnitude = length(vector)
    if magnitude <= EPSILON:
        raise ValueError("Zero-length geometry is not supported.")
    return vector.scaled(1.0 / magnitude)


def signed_area(polygon: Sequence[Point]) -> float:
    return 0.5 * sum(
        cross(polygon[index], polygon[(index + 1) % len(polygon)])
        for index in range(len(polygon))
    )


def distance_to_segment(point: Point, start: Point, end: Point) -> float:
    vector = end - start
    magnitude_squared = dot(vector, vector)
    if magnitude_squared <= EPSILON:
        return length(point - start)
    factor = max(
        0.0,
        min(1.0, dot(point - start, vector) / magnitude_squared),
    )
    projection = start + vector.scaled(factor)
    return length(point - projection)


def point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        if distance_to_segment(point, start, end) <= EPSILON:
            return True

    inside = False
    previous = polygon[-1]
    for current in polygon:
        if (current.y > point.y) != (previous.y > point.y):
            crossing_x = (
                (previous.x - current.x)
                * (point.y - current.y)
                / (previous.y - current.y)
                + current.x
            )
            if point.x < crossing_x:
                inside = not inside
        previous = current
    return inside


def interval_overlap(
    first_start: float,
    first_end: float,
    second_start: float,
    second_end: float,
) -> float:
    first_min, first_max = sorted((first_start, first_end))
    second_min, second_max = sorted((second_start, second_end))
    return max(0.0, min(first_max, second_max) - max(first_min, second_min))


def outward_normal(
    edge_direction: Point,
    polygon_area: float,
) -> Point:
    tangent = unit(edge_direction)
    if polygon_area > 0:
        return Point(tangent.y, -tangent.x)
    return Point(-tangent.y, tangent.x)


def line_intersection(
    first_point: Point,
    first_direction: Point,
    second_point: Point,
    second_direction: Point,
) -> Point | None:
    denominator = cross(first_direction, second_direction)
    if abs(denominator) <= EPSILON:
        return None
    factor = cross(second_point - first_point, second_direction) / denominator
    return first_point + first_direction.scaled(factor)


def orientations(start: Point, end: Point, point: Point) -> float:
    return cross(end - start, point - start)


def segments_intersect(
    first_start: Point,
    first_end: Point,
    second_start: Point,
    second_end: Point,
) -> bool:
    first_a = orientations(first_start, first_end, second_start)
    first_b = orientations(first_start, first_end, second_end)
    second_a = orientations(second_start, second_end, first_start)
    second_b = orientations(second_start, second_end, first_end)
    return (
        first_a * first_b < -EPSILON
        and second_a * second_b < -EPSILON
    )


def validate_polygon(polygon: Sequence[Point]) -> None:
    if len(polygon) < 3:
        raise ValueError("A slab polygon must have at least three vertices.")
    if abs(signed_area(polygon)) <= EPSILON:
        raise ValueError("The repaired slab polygon has zero area.")

    edge_count = len(polygon)
    for first_index in range(edge_count):
        first_start = polygon[first_index]
        first_end = polygon[(first_index + 1) % edge_count]
        if length(first_end - first_start) <= EPSILON:
            raise ValueError(
                f"Repaired edge {first_index} has zero length."
            )
        for second_index in range(first_index + 1, edge_count):
            if second_index in {
                first_index,
                (first_index + 1) % edge_count,
                (first_index - 1) % edge_count,
            }:
                continue
            if first_index == 0 and second_index == edge_count - 1:
                continue
            second_start = polygon[second_index]
            second_end = polygon[(second_index + 1) % edge_count]
            if segments_intersect(
                first_start,
                first_end,
                second_start,
                second_end,
            ):
                raise ValueError(
                    "The repaired slab polygon self-intersects at edges "
                    f"{first_index} and {second_index}."
                )


def simplify_polygon(polygon: Sequence[Point]) -> list[Point]:
    simplified: list[Point] = []
    for point in polygon:
        if not simplified or length(point - simplified[-1]) > EPSILON:
            simplified.append(point)
    if (
        len(simplified) > 1
        and length(simplified[0] - simplified[-1]) <= EPSILON
    ):
        simplified.pop()

    changed = True
    while changed and len(simplified) >= 3:
        changed = False
        retained: list[Point] = []
        for index, point in enumerate(simplified):
            previous = simplified[(index - 1) % len(simplified)]
            following = simplified[(index + 1) % len(simplified)]
            incoming = point - previous
            outgoing = following - point
            if (
                abs(cross(incoming, outgoing)) <= EPSILON
                and dot(incoming, outgoing) >= 0
            ):
                changed = True
                continue
            retained.append(point)
        simplified = retained
    return simplified


def parse_geometry(path: Path) -> tuple[list[Point], list[Wall]]:
    vertices: list[Point] = []
    walls: list[Wall] = []
    floor_indices: set[int] = set()
    perimeter_indices: set[tuple[int, int]] = set()
    vertex_perimeters: set[tuple[int, int]] = set()
    wall_floors: set[int] = set()
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream, delimiter="\t"):
            if not row:
                continue
            if row[0] == "FLOOR":
                floor_indices.add(int(row[1]))
            elif row[0] == "PERIMETER":
                perimeter_indices.add((int(row[1]), int(row[2])))
            elif row[0] == "VERTEX":
                vertex_perimeters.add((int(row[1]), int(row[2])))
                vertices.append(Point(float(row[4]), float(row[5])))
            elif row[0] == "WALL":
                wall_floors.add(int(row[1]))
                wall = Wall(
                    index=int(row[2]),
                    uid=int(row[3]),
                    label=int(row[4]),
                    start=Point(float(row[5]), float(row[6])),
                    end=Point(float(row[7]), float(row[8])),
                    thickness=float(row[9]),
                    eccentricity=int(row[10]),
                    eccentric_distance=float(row[11]),
                )
                if wall.thickness <= EPSILON:
                    raise ValueError(
                        f"Wall {wall.label} has nonpositive thickness."
                    )
                if length(wall.end - wall.start) <= EPSILON:
                    raise ValueError(
                        f"Wall {wall.label} has zero length."
                    )
                if abs(wall.eccentric_distance) > EPSILON:
                    raise ValueError(
                        f"Wall {wall.label} has nonzero eccentric distance."
                    )
                walls.append(wall)
    if len(floor_indices) != 1:
        raise ValueError(
            "This proof workflow requires exactly one RSS floor type."
        )
    if len(perimeter_indices) != 1:
        raise ValueError(
            "This proof workflow requires exactly one slab perimeter."
        )
    if vertex_perimeters != perimeter_indices:
        raise ValueError(
            "The slab vertices do not belong to the sole perimeter."
        )
    if wall_floors != floor_indices:
        raise ValueError(
            "The walls do not belong to the sole exported floor type."
        )
    if not vertices:
        raise ValueError("No slab perimeter vertices were found.")
    if not walls:
        raise ValueError("No walls were found.")
    validate_polygon(vertices)
    return vertices, walls


def select_edge_repairs(
    polygon: Sequence[Point],
    walls: Sequence[Wall],
    clearance: float,
    search_distance: float,
    parallel_tolerance: float,
) -> tuple[list[float], list[EdgeRepair]]:
    area = signed_area(polygon)
    shifts = [0.0] * len(polygon)
    repairs: list[EdgeRepair] = []

    for edge_index, edge_start in enumerate(polygon):
        edge_end = polygon[(edge_index + 1) % len(polygon)]
        edge_vector = edge_end - edge_start
        tangent = unit(edge_vector)
        normal = outward_normal(edge_vector, area)
        edge_start_projection = dot(edge_start, tangent)
        edge_end_projection = dot(edge_end, tangent)
        best: EdgeRepair | None = None

        for wall in walls:
            wall_vector = wall.end - wall.start
            wall_tangent = unit(wall_vector)
            if abs(cross(tangent, wall_tangent)) > parallel_tolerance:
                continue

            overlap = interval_overlap(
                edge_start_projection,
                edge_end_projection,
                dot(wall.start, tangent),
                dot(wall.end, tangent),
            )
            if overlap <= EPSILON:
                continue

            wall_midpoint = Point(
                (wall.start.x + wall.end.x) / 2.0,
                (wall.start.y + wall.end.y) / 2.0,
            )
            wall_normal = Point(wall_tangent.y, -wall_tangent.x)
            if dot(wall_normal, normal) < 0:
                wall_normal = wall_normal.scaled(-1.0)
            normal_alignment = dot(normal, wall_normal)
            if normal_alignment <= EPSILON:
                continue

            current_offset = dot(
                edge_start - wall_midpoint,
                wall_normal,
            )
            if abs(current_offset) > search_distance:
                continue

            # Wall layout eccentricity is currently centered in the proof
            # model (eccentricity=1, distance=0). Refuse an unproven case.
            if wall.eccentric_distance > EPSILON:
                raise ValueError(
                    f"Wall {wall.label} has a nonzero eccentric distance."
                )

            required_offset = wall.thickness / 2.0 + clearance
            outward_shift = (
                required_offset - current_offset
            ) / normal_alignment
            if outward_shift <= EPSILON:
                continue

            candidate = EdgeRepair(
                edge_index=edge_index,
                wall_uid=wall.uid,
                wall_label=wall.label,
                current_offset=current_offset,
                required_offset=required_offset,
                outward_shift=outward_shift,
                overlap=overlap,
            )
            if best is None or (
                candidate.overlap,
                -abs(candidate.current_offset),
            ) > (
                best.overlap,
                -abs(best.current_offset),
            ):
                best = candidate

        if best is not None:
            shifts[edge_index] = best.outward_shift
            repairs.append(best)

    return shifts, repairs


def rebuild_polygon(
    polygon: Sequence[Point],
    shifts: Sequence[float],
) -> list[Point]:
    area = signed_area(polygon)
    shifted_points: list[Point] = []
    directions: list[Point] = []

    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        direction = end - start
        normal = outward_normal(direction, area)
        shifted_points.append(start + normal.scaled(shifts[index]))
        directions.append(direction)

    repaired: list[Point] = []
    for vertex_index in range(len(polygon)):
        previous_index = (vertex_index - 1) % len(polygon)
        intersection = line_intersection(
            shifted_points[previous_index],
            directions[previous_index],
            shifted_points[vertex_index],
            directions[vertex_index],
        )
        if intersection is None:
            previous_normal = outward_normal(
                directions[previous_index],
                area,
            )
            current_normal = outward_normal(
                directions[vertex_index],
                area,
            )
            displacement = previous_normal.scaled(
                shifts[previous_index]
            ) + current_normal.scaled(shifts[vertex_index])
            intersection = polygon[vertex_index] + displacement.scaled(0.5)
        repaired.append(intersection)

    repaired = simplify_polygon(repaired)
    validate_polygon(repaired)
    if signed_area(repaired) * area <= 0:
        raise ValueError("The repaired polygon orientation changed.")
    return repaired


def wall_corners(wall: Wall, clearance: float) -> list[Point]:
    tangent = unit(wall.end - wall.start)
    normal = Point(-tangent.y, tangent.x)
    half_width = wall.thickness / 2.0 + clearance
    offset = normal.scaled(half_width)
    return [
        wall.start + offset,
        wall.start - offset,
        wall.end + offset,
        wall.end - offset,
    ]


def coverage_failures(
    polygon: Sequence[Point],
    walls: Iterable[Wall],
    clearance: float,
) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    for wall in walls:
        outside = [
            corner
            for corner in wall_corners(wall, clearance)
            if not point_in_polygon(corner, polygon)
        ]
        if outside:
            failures.append(
                {
                    "wall_uid": wall.uid,
                    "wall_label": wall.label,
                    "outside_corners": [
                        {"x": point.x, "y": point.y}
                        for point in outside
                    ],
                }
            )
    return failures


def point_records(points: Sequence[Point]) -> list[dict[str, float]]:
    return [{"x": point.x, "y": point.y} for point in points]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("geometry_tsv", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument(
        "--clearance-in",
        type=float,
        default=1.0,
        help="Required slab projection past the wall exterior face.",
    )
    parser.add_argument(
        "--search-distance-in",
        type=float,
        default=31.0,
        help="Maximum wall-centerline distance considered for an edge.",
    )
    parser.add_argument(
        "--parallel-tolerance",
        type=float,
        default=1.0e-3,
    )
    args = parser.parse_args()

    if args.clearance_in <= 0:
        raise ValueError("Clearance must be greater than zero.")
    if args.search_distance_in <= 0:
        raise ValueError("Search distance must be greater than zero.")
    if args.parallel_tolerance <= 0:
        raise ValueError("Parallel tolerance must be greater than zero.")

    polygon, walls = parse_geometry(args.geometry_tsv)
    shifts, repairs = select_edge_repairs(
        polygon,
        walls,
        args.clearance_in,
        args.search_distance_in,
        args.parallel_tolerance,
    )
    repaired = rebuild_polygon(polygon, shifts)

    source_failures = coverage_failures(
        polygon,
        walls,
        args.clearance_in,
    )
    repaired_failures = coverage_failures(
        repaired,
        walls,
        args.clearance_in,
    )

    report = {
        "source": str(args.geometry_tsv.resolve()),
        "units": "in",
        "acceptance_rule": (
            "slab offset >= wall thickness / 2 + clearance"
        ),
        "clearance": args.clearance_in,
        "source_vertex_count": len(polygon),
        "wall_count": len(walls),
        "modified_edge_count": len(repairs),
        "repaired_vertex_count": len(repaired),
        "source_wall_footprint_failures": len(source_failures),
        "repaired_wall_footprint_failures": len(repaired_failures),
        "repairs": [
            {
                "edge_index": repair.edge_index,
                "wall_uid": repair.wall_uid,
                "wall_label": repair.wall_label,
                "current_offset": repair.current_offset,
                "required_offset": repair.required_offset,
                "outward_shift": repair.outward_shift,
                "overlap": repair.overlap,
            }
            for repair in repairs
        ],
        "source_polygon": point_records(polygon),
        "repaired_polygon": point_records(repaired),
        "remaining_failures": repaired_failures,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")

    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "source_vertex_count",
                    "repaired_vertex_count",
                    "wall_count",
                    "modified_edge_count",
                    "source_wall_footprint_failures",
                    "repaired_wall_footprint_failures",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
