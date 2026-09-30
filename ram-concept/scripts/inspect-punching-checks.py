#!/usr/bin/env python3
"""Inspect saved RAM Concept punching inputs and generated SSR geometry.

The source is opened as immutable, query-only SQLite. This is a diagnostic
reader for a separately copied saved checkpoint; it does not calculate, save,
or modify a RAM Concept model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any


POINT_PATTERN = re.compile(
    r"\[(-?\d+(?:\.\d+)?)\]\[(-?\d+(?:\.\d+)?)\]"
)
REQUIRED_TABLES = {"PunchCheck", "SsrSet", "SsrSystem"}


class ConceptCheckpointError(RuntimeError):
    """Raised when the saved checkpoint lacks a required invariant."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_points(value: str | None) -> list[tuple[float, float]]:
    if not value:
        return []
    return [
        (float(match.group(1)), float(match.group(2)))
        for match in POINT_PATTERN.finditer(value)
    ]


def parse_integers(value: str | None) -> list[int]:
    if not value:
        return []
    return [int(token) for token in re.findall(r"\[(-?\d+)\]", value)]


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def validate_schema(connection: sqlite3.Connection) -> set[str]:
    tables = table_names(connection)
    missing = sorted(REQUIRED_TABLES - tables)
    if missing:
        raise ConceptCheckpointError(
            "Checkpoint does not contain required RAM Concept tables: "
            + ", ".join(missing)
        )
    return tables


def distance_to_segment(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if dx == 0 and dy == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    projection = (
        (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
    ) / (dx * dx + dy * dy)
    projection = max(0.0, min(1.0, projection))
    closest = (start[0] + projection * dx, start[1] + projection * dy)
    return math.hypot(point[0] - closest[0], point[1] - closest[1])


def nearest_polygon_edge_distance(
    point: tuple[float, float],
    polygons: list[list[tuple[float, float]]],
) -> float | None:
    distances: list[float] = []
    for polygon in polygons:
        if len(polygon) < 2:
            continue
        edges = zip(polygon, polygon[1:] + polygon[:1])
        distances.extend(
            distance_to_segment(point, start, end)
            for start, end in edges
        )
    return min(distances) if distances else None


def inspect_checkpoint(
    checkpoint: Path,
    *,
    internal_units_per_foot: float = 3048.0,
    near_limit_ratio: float = 0.95,
) -> dict[str, Any]:
    checkpoint = checkpoint.resolve()
    if not checkpoint.is_file():
        raise ConceptCheckpointError(f"Checkpoint not found: {checkpoint}")
    if internal_units_per_foot <= 0:
        raise ConceptCheckpointError("Internal-units-per-foot must be positive.")
    if not 0 < near_limit_ratio <= 1:
        raise ConceptCheckpointError("Near-limit ratio must be in (0, 1].")
    with checkpoint.open("rb") as stream:
        header = stream.read(16)
    if header != b"SQLite format 3\x00":
        raise ConceptCheckpointError(
            "Checkpoint is not a RAM Concept SQLite model copy."
        )

    uri = f"{checkpoint.as_uri()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        tables = validate_schema(connection)

        opening_polygons = (
            [
                parse_points(row[0])
                for row in connection.execute(
                    "SELECT MultiPoint FROM SlabOpening ORDER BY Number"
                )
            ]
            if "SlabOpening" in tables
            else []
        )
        slab_boundary_polygons = (
            [
                parse_points(row[0])
                for row in connection.execute(
                    "SELECT MultiPoint FROM SlabArea ORDER BY Number"
                )
            ]
            if "SlabArea" in tables
            else []
        )

        systems = {
            row[0]: {
                "name": row[1],
                "stud_area_internal": row[2],
                "fy_internal": row[3],
            }
            for row in connection.execute(
                "SELECT UID, Name, StudArea, Fy FROM SsrSystem"
            )
        }

        layouts_by_location: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in connection.execute(
            """
            SELECT UID, LocationPoint, Point0, Point1, SsrSystem,
                   StudSpacingFirst, StudSpacingTypical, MaxStudCount,
                   StudCount
            FROM SsrSet
            ORDER BY Number
            """
        ):
            (
                uid,
                location,
                point0,
                point1,
                system_uid,
                first_spacing,
                typical_spacing,
                max_stud_count,
                stud_counts,
            ) = row
            layouts_by_location[location].append(
                {
                    "uid": uid,
                    "system_uid": system_uid,
                    "system_name": systems.get(system_uid, {}).get("name"),
                    "rail_start_points_internal": parse_points(point0),
                    "rail_end_points_internal": parse_points(point1),
                    "first_spacing_internal": first_spacing,
                    "typical_spacing_internal": typical_spacing,
                    "max_stud_count": max_stud_count,
                    "stud_counts": parse_integers(stud_counts),
                }
            )

        checks: list[dict[str, Any]] = []
        for row in connection.execute(
            """
            SELECT UID, Number, Name, Point0, MaxRadius, SsrDesignDesired,
                   SsrSystem, ConnectionType, EdgeTreatment
            FROM PunchCheck
            ORDER BY Number
            """
        ):
            (
                uid,
                number,
                name,
                location_text,
                max_radius,
                ssr_desired,
                system_uid,
                connection_type,
                edge_treatment,
            ) = row
            location_points = parse_points(location_text)
            if len(location_points) != 1:
                raise ConceptCheckpointError(
                    f"Punch check {number + 1} has an invalid Point0 value."
                )
            location = location_points[0]
            layouts = layouts_by_location.get(location_text, [])
            end_points = [
                point
                for layout in layouts
                for point in layout["rail_end_points_internal"]
            ]
            max_reach = (
                max(
                    math.hypot(point[0] - location[0], point[1] - location[1])
                    for point in end_points
                )
                if end_points
                else None
            )
            ratio = (
                max_reach / max_radius
                if max_reach is not None and max_radius
                else None
            )
            opening_distance = nearest_polygon_edge_distance(
                location,
                opening_polygons,
            )
            slab_boundary_distance = nearest_polygon_edge_distance(
                location,
                slab_boundary_polygons,
            )
            checks.append(
                {
                    "check_number": number + 1,
                    "uid": uid,
                    "name": name,
                    "location_internal": list(location),
                    "location_ft": [
                        coordinate / internal_units_per_foot
                        for coordinate in location
                    ],
                    "maximum_search_radius_internal": max_radius,
                    "maximum_search_radius_ft": (
                        max_radius / internal_units_per_foot
                    ),
                    "ssr_design_desired": bool(ssr_desired),
                    "ssr_system_uid": system_uid,
                    "ssr_system_name": systems.get(system_uid, {}).get("name"),
                    "connection_type": connection_type,
                    "edge_treatment": edge_treatment,
                    "generated_ssr_layout_count": len(layouts),
                    "generated_rail_count": sum(
                        len(layout["rail_end_points_internal"])
                        for layout in layouts
                    ),
                    "maximum_generated_stud_count": max(
                        (
                            count
                            for layout in layouts
                            for count in layout["stud_counts"]
                        ),
                        default=None,
                    ),
                    "maximum_generated_rail_reach_ft": (
                        max_reach / internal_units_per_foot
                        if max_reach is not None
                        else None
                    ),
                    "search_radius_usage_ratio": ratio,
                    "generated_rails_near_search_limit": (
                        ratio is not None and ratio >= near_limit_ratio
                    ),
                    "nearest_slab_opening_edge_distance_ft": (
                        opening_distance / internal_units_per_foot
                        if opening_distance is not None
                        else None
                    ),
                    "nearest_slab_boundary_edge_distance_ft": (
                        slab_boundary_distance / internal_units_per_foot
                        if slab_boundary_distance is not None
                        else None
                    ),
                    "slab_opening_within_search_radius": (
                        opening_distance is not None
                        and opening_distance <= max_radius
                    ),
                    "slab_boundary_within_search_radius": (
                        slab_boundary_distance is not None
                        and slab_boundary_distance <= max_radius
                    ),
                }
            )
    finally:
        connection.close()

    with_layout = [
        check for check in checks if check["generated_ssr_layout_count"] > 0
    ]
    near_limit = [
        check for check in checks if check["generated_rails_near_search_limit"]
    ]
    without_layout = [
        check for check in checks if check["generated_ssr_layout_count"] == 0
    ]
    opening_within_radius = [
        check for check in checks if check["slab_opening_within_search_radius"]
    ]
    boundary_within_radius = [
        check for check in checks if check["slab_boundary_within_search_radius"]
    ]

    return {
        "source": {
            "path": str(checkpoint),
            "sha256": sha256(checkpoint),
            "size_bytes": checkpoint.stat().st_size,
        },
        "method": {
            "access": "SQLite URI mode=ro, immutable=1, PRAGMA query_only=ON",
            "internal_units_per_foot": internal_units_per_foot,
            "near_limit_ratio": near_limit_ratio,
            "scope": (
                "Saved PunchCheck inputs and generated SsrSet geometry only; "
                "no calculation, save, or mutation."
            ),
        },
        "summary": {
            "punch_check_count": len(checks),
            "checks_with_generated_ssr_layouts": len(with_layout),
            "checks_without_generated_ssr_layouts": len(without_layout),
            "generated_ssr_layouts_near_search_limit": len(near_limit),
            "near_limit_check_numbers": [
                check["check_number"] for check in near_limit
            ],
            "no_layout_check_numbers": [
                check["check_number"] for check in without_layout
            ],
            "slab_opening_within_search_radius_check_numbers": [
                check["check_number"] for check in opening_within_radius
            ],
            "slab_boundary_within_search_radius_check_numbers": [
                check["check_number"] for check in boundary_within_radius
            ],
        },
        "interpretation_limits": [
            (
                "A missing SsrSet is ambiguous: the check may not require SSR, "
                "or SSR design may have failed before a layout was generated."
            ),
            (
                "The saved SQLite checkpoint and the official 2024 API do not "
                "expose the live warnings list or the punching-audit failure "
                "message. Exported warnings or punching-audit output is needed "
                "to identify exact failed checks."
            ),
            (
                "Treat undocumented SQLite names and internal units as "
                "version-specific diagnostic evidence. Verify displayed units "
                "through the official RAM Concept API or UI."
            ),
        ],
        "checks": checks,
    }


def markdown_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# RAM Concept punching checkpoint inspection",
        "",
        f"- Source: `{result['source']['path']}`",
        f"- SHA-256: `{result['source']['sha256']}`",
        f"- Punch checks: {summary['punch_check_count']}",
        (
            "- Checks with generated SSR layouts: "
            f"{summary['checks_with_generated_ssr_layouts']}"
        ),
        (
            "- Checks without generated SSR layouts: "
            f"{summary['checks_without_generated_ssr_layouts']}"
        ),
        (
            "- Generated layouts near the search-radius limit: "
            f"{summary['generated_ssr_layouts_near_search_limit']}"
        ),
        (
            "- Checks with a slab-opening edge inside the search radius: "
            f"{len(summary['slab_opening_within_search_radius_check_numbers'])}"
        ),
        (
            "- Checks with a slab-boundary edge inside the search radius: "
            f"{len(summary['slab_boundary_within_search_radius_check_numbers'])}"
        ),
        "",
        "## Near-limit generated layouts",
        "",
        "| Check | Location (ft) | Radius (ft) | Rail reach (ft) | Usage | Max studs |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    near_limit_checks = [
        check
        for check in result["checks"]
        if check["generated_rails_near_search_limit"]
    ]
    for check in near_limit_checks:
        x, y = check["location_ft"]
        lines.append(
            "| {check_number} | {x:.2f}, {y:.2f} | {radius:.2f} | "
            "{reach:.2f} | {usage:.1%} | {studs} |".format(
                check_number=check["check_number"],
                x=x,
                y=y,
                radius=check["maximum_search_radius_ft"],
                reach=check["maximum_generated_rail_reach_ft"],
                usage=check["search_radius_usage_ratio"],
                studs=check["maximum_generated_stud_count"],
            )
        )
    if not near_limit_checks:
        lines.append("| — | — | — | — | — | — |")

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            *[
                f"- {statement}"
                for statement in result["interpretation_limits"]
            ],
            "",
            (
                "Checks without a generated SSR layout: "
                + ", ".join(
                    str(number)
                    for number in summary["no_layout_check_numbers"]
                )
            ),
            (
                "Checks with a slab-opening edge inside the search radius: "
                + ", ".join(
                    str(number)
                    for number in summary[
                        "slab_opening_within_search_radius_check_numbers"
                    ]
                )
            ),
            (
                "Checks with a slab-boundary edge inside the search radius: "
                + ", ".join(
                    str(number)
                    for number in summary[
                        "slab_boundary_within_search_radius_check_numbers"
                    ]
                )
            ),
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument(
        "--internal-units-per-foot",
        type=float,
        default=3048.0,
        help=(
            "Verified RAM Concept internal coordinate units per foot. "
            "Default 3048 is valid for the tested 2024 checkpoint."
        ),
    )
    parser.add_argument(
        "--near-limit-ratio",
        type=float,
        default=0.95,
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    args = parser.parse_args()

    result = inspect_checkpoint(
        args.checkpoint,
        internal_units_per_foot=args.internal_units_per_foot,
        near_limit_ratio=args.near_limit_ratio,
    )
    if args.format == "markdown":
        print(markdown_report(result))
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
