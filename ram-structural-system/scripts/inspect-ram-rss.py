#!/usr/bin/env python3
"""Read-only structural inspection of a Bentley RAM Structural System RSS archive.

The RSS format is proprietary and undocumented. This tool only decodes fields
that have been confirmed through controlled model diffs and RAM UI validation.
It never writes to the source archive.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


FLOOR_RECORD_SIZE = 472
STORY_RECORD_SIZE = 336
COLUMN_RECORD_SIZE = 1072
WALL_RECORD_SIZE = 584
SECTION_RECORD_SIZE = 184
LOAD_PROPERTY_RECORD_SIZE = 72
LOAD_PLACEMENT_RECORD_SIZE = 20
POINT_RECORD_SIZE = 16

SURFACE_PSF_FACTOR = 144_000.0
LINE_KLF_FACTOR = 12.0
UNREDUCIBLE_LIVE_TYPE = 1265


class RssFormatError(RuntimeError):
    """Raised when an RSS invariant needed for safe decoding is not satisfied."""


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def c_string(data: bytes, offset: int, length: int) -> str:
    return data[offset : offset + length].split(b"\0", 1)[0].decode(
        "ascii", errors="replace"
    )


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def f32(data: bytes, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]


def f64(data: bytes, offset: int) -> float:
    return struct.unpack_from("<d", data, offset)[0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ram_fields(data: bytes) -> dict[str, list[bytes]]:
    result: dict[str, list[bytes]] = {}
    pattern = re.compile(rb'<field name="([^"]+)">([0-9A-Fa-f]*)</field>')
    for match in pattern.finditer(data):
        name = match.group(1).decode("ascii", errors="replace")
        result.setdefault(name, []).append(bytes.fromhex(match.group(2).decode("ascii")))
    return result


def ram_u32(fields: dict[str, list[bytes]], name: str) -> int:
    values = fields.get(name, [])
    if len(values) != 1 or len(values[0]) != 4:
        raise RssFormatError(
            f"Expected one four-byte .ram field named {name}; found {len(values)}"
        )
    return struct.unpack("<I", values[0])[0]


def member_by_suffix(
    payloads: dict[str, bytes], suffix: str, *, required: bool = True
) -> tuple[str, bytes] | tuple[None, None]:
    matches = [(name, data) for name, data in payloads.items() if name.lower().endswith(suffix)]
    if len(matches) == 1:
        return matches[0]
    if not matches and not required:
        return None, None
    raise RssFormatError(f"Expected one {suffix} archive member; found {len(matches)}")


def fixed_records(data: bytes, size: int, name: str) -> list[bytes]:
    if len(data) % size:
        raise RssFormatError(
            f"{name} length {len(data)} is not divisible by confirmed record size {size}"
        )
    return [data[offset : offset + size] for offset in range(0, len(data), size)]


def parse_floor_types(data: bytes) -> list[dict[str, Any]]:
    floors = []
    for index, record in enumerate(fixed_records(data, FLOOR_RECORD_SIZE, ".flt")):
        floors.append(
            {
                "index": index,
                "label": c_string(record, 0, 24),
                "counts": {
                    "columns": u32(record, 24),
                    "walls": u32(record, 28),
                    "beams": u32(record, 32),
                    "surface_loads": u32(record, 52),
                    "line_loads": u32(record, 56),
                    "point_loads": u32(record, 60),
                },
                "starts": {
                    "columns": u32(record, 76),
                    "walls": u32(record, 80),
                    "beams": u32(record, 84),
                },
                "next_labels": {
                    "columns": u32(record, 288),
                    "walls": u32(record, 292),
                },
            }
        )
    return floors


def parse_stories(data: bytes) -> list[dict[str, Any]]:
    stories = []
    for index, record in enumerate(fixed_records(data, STORY_RECORD_SIZE, ".sty")):
        stories.append(
            {
                "index": index,
                "number": u32(record, 0),
                "label": c_string(record, 4, 24),
                "height_in": f32(record, 28),
                "counts": {
                    "columns": u32(record, 52),
                    "walls": u32(record, 56),
                    "beams": u32(record, 60),
                },
                "starts": {
                    "columns": u32(record, 168),
                    "walls": u32(record, 172),
                    "beams": u32(record, 176),
                },
            }
        )
    return stories


def parse_columns(data: bytes) -> list[dict[str, Any]]:
    columns = []
    for index, record in enumerate(fixed_records(data, COLUMN_RECORD_SIZE, ".c3d")):
        columns.append(
            {
                "record_index": index,
                "number": u32(record, 44),
                "x_ft": f64(record, 0) / 12.0,
                "y_ft": f64(record, 8) / 12.0,
                "section": c_string(record, 48, 16),
                "fpc_ksi": f32(record, 112),
                "unit_weight_pcf": f32(record, 116),
                "poisson": f32(record, 120),
                "self_weight_pcf": f32(record, 416),
            }
        )
    return columns


def parse_walls(data: bytes) -> list[dict[str, Any]]:
    walls = []
    for index, record in enumerate(fixed_records(data, WALL_RECORD_SIZE, ".w3d")):
        walls.append(
            {
                "record_index": index,
                "number": u32(record, 52),
                "x1_ft": f64(record, 0) / 12.0,
                "y1_ft": f64(record, 8) / 12.0,
                "x2_ft": f64(record, 16) / 12.0,
                "y2_ft": f64(record, 24) / 12.0,
                "thickness_in": f32(record, 56),
                "fpc_ksi": f32(record, 60),
                "unit_weight_pcf": f32(record, 64),
                "poisson": f32(record, 68),
                "material_enum": u32(record, 80),
                "self_weight_pcf": f32(record, 232),
                "cracked_membrane": f32(record, 172),
                "cracked_bending": f32(record, 300),
                "fy_distributed_ksi": f64(record, 368),
                "fy_boundary_ksi": f64(record, 376),
                "fy_ties_ksi": f64(record, 384),
            }
        )
    return walls


def parse_concrete_column_sections(data: bytes | None) -> list[dict[str, Any]]:
    if not data:
        return []
    sections = []
    for index, record in enumerate(fixed_records(data, SECTION_RECORD_SIZE, ".sec")):
        sections.append(
            {
                "record_index": index,
                "label": c_string(record, 0, 20),
                "b_in": f32(record, 20),
                "h_in": f32(record, 24),
                "flexure_factor": f32(record, 60),
                "shape_enum": u32(record, 152),
                "axial_factor": f32(record, 156),
                "torsion_factor": f32(record, 160),
            }
        )
    return sections


def parse_load_properties(
    data: bytes,
    surface_count: int,
    line_count: int,
    point_count: int,
) -> dict[str, list[dict[str, Any]]]:
    records = fixed_records(data, LOAD_PROPERTY_RECORD_SIZE, ".lpt")
    expected = surface_count + line_count + point_count
    if len(records) != expected:
        raise RssFormatError(
            f".ram/.lpt property totals disagree: .ram={expected}, .lpt={len(records)}"
        )

    result: dict[str, list[dict[str, Any]]] = {
        "surface": [],
        "line": [],
        "point": [],
    }
    cursor = 0
    for category, count in (
        ("surface", surface_count),
        ("line", line_count),
        ("point", point_count),
    ):
        factor = {
            "surface": SURFACE_PSF_FACTOR,
            "line": LINE_KLF_FACTOR,
            "point": 1.0,
        }[category]
        for local_index, record in enumerate(records[cursor : cursor + count]):
            result[category].append(
                {
                    "index": local_index,
                    "label": c_string(record, 0, 20),
                    "dead": f32(record, 20) * factor,
                    "construction_dead": f32(record, 24) * factor,
                    "construction_live": f32(record, 28) * factor,
                    "live": f32(record, 32) * factor,
                    "mass_dead": f32(record, 36) * factor,
                    "live_type": u32(record, 40),
                    "assignment_count": u32(record, 44),
                    "uid": u32(record, 52),
                    "partition": f32(record, 64) * factor,
                    "units": {
                        "surface": "psf",
                        "line": "klf",
                        "point": "kip",
                    }[category],
                }
            )
        cursor += count
    return result


def parse_points(data: bytes) -> list[tuple[float, float]]:
    records = fixed_records(data, POINT_RECORD_SIZE, ".pol")
    return [(f64(record, 0) / 12.0, f64(record, 8) / 12.0) for record in records]


def parse_placements(
    lod_data: bytes,
    points: list[tuple[float, float]],
    properties: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[Check]]:
    raw_records = fixed_records(lod_data, LOAD_PLACEMENT_RECORD_SIZE, ".lod")
    raw = [
        {
            "point_count": u32(record, 0),
            "point_start": u32(record, 4),
            "property_index": u32(record, 8),
            "id": u32(record, 12),
            "uid": u32(record, 16),
        }
        for record in raw_records
    ]
    checks: list[Check] = []
    expected_placements = sum(
        prop["assignment_count"]
        for category in properties.values()
        for prop in category
    )
    checks.append(
        Check(
            "load property assignment totals equal .lod records",
            expected_placements == len(raw),
            f"property totals={expected_placements}, .lod={len(raw)}",
        )
    )
    if expected_placements != len(raw):
        raise RssFormatError(checks[-1].detail)

    placements: list[dict[str, Any]] = []
    cursor = 0
    for category in ("surface", "line", "point"):
        category_properties = properties[category]
        category_count = sum(prop["assignment_count"] for prop in category_properties)
        category_records = raw[cursor : cursor + category_count]
        observed: Counter[int] = Counter()
        for ordinal, item in enumerate(category_records, start=cursor):
            property_index = item["property_index"]
            if property_index >= len(category_properties):
                raise RssFormatError(
                    f".lod record {ordinal} has invalid {category} property index "
                    f"{property_index}"
                )
            start = item["point_start"]
            end = start + item["point_count"]
            if end > len(points):
                raise RssFormatError(
                    f".lod record {ordinal} references .pol points {start}:{end}, "
                    f"but only {len(points)} exist"
                )
            prop = category_properties[property_index]
            observed[property_index] += 1
            placements.append(
                {
                    **item,
                    "record_index": ordinal,
                    "category": category,
                    "property_label": prop["label"],
                    "points_ft": points[start:end],
                }
            )
        expected = Counter(
            {
                prop["index"]: prop["assignment_count"]
                for prop in category_properties
                if prop["assignment_count"]
            }
        )
        checks.append(
            Check(
                f"{category} property assignment counts match .lod block",
                observed == expected,
                f"expected={dict(expected)}, observed={dict(observed)}",
            )
        )
        cursor += category_count
    return placements, checks


def endpoint_distance(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> float:
    direct = max(math.dist(a1, b1), math.dist(a2, b2))
    reverse = max(math.dist(a1, b2), math.dist(a2, b1))
    return min(direct, reverse)


def point_to_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    px, py = point
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.dist(point, start)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    return math.dist(point, (x1 + t * dx, y1 + t * dy))


def segment_angle(start: tuple[float, float], end: tuple[float, float]) -> float:
    return math.atan2(end[1] - start[1], end[0] - start[0])


def parallel_angle_difference(a: float, b: float) -> float:
    difference = abs(a - b) % math.pi
    return min(difference, math.pi - difference)


def correlate_segment(
    segment: tuple[tuple[float, float], tuple[float, float]],
    placements: list[dict[str, Any]],
    walls: list[dict[str, Any]],
    tolerance_ft: float,
) -> dict[str, Any]:
    p1, p2 = segment
    line_candidates = []
    for placement in placements:
        if placement["category"] != "line" or len(placement["points_ft"]) != 2:
            continue
        q1, q2 = placement["points_ft"]
        line_candidates.append(
            {
                "record_index": placement["record_index"],
                "id": placement["id"],
                "uid": placement["uid"],
                "property": placement["property_label"],
                "points_ft": placement["points_ft"],
                "endpoint_distance_ft": endpoint_distance(p1, p2, q1, q2),
            }
        )
    line_candidates.sort(key=lambda item: item["endpoint_distance_ft"])

    warning_angle = segment_angle(p1, p2)
    midpoint = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
    wall_candidates = []
    for wall in walls:
        w1 = (wall["x1_ft"], wall["y1_ft"])
        w2 = (wall["x2_ft"], wall["y2_ft"])
        angle_difference = parallel_angle_difference(
            warning_angle, segment_angle(w1, w2)
        )
        wall_candidates.append(
            {
                "number": wall["number"],
                "points_ft": [w1, w2],
                "midpoint_distance_ft": point_to_segment_distance(midpoint, w1, w2),
                "parallel_angle_difference_deg": math.degrees(angle_difference),
            }
        )
    wall_candidates.sort(
        key=lambda item: (
            item["parallel_angle_difference_deg"] > 2.0,
            item["midpoint_distance_ft"],
        )
    )
    exact = [
        candidate
        for candidate in line_candidates
        if candidate["endpoint_distance_ft"] <= tolerance_ft
    ]
    return {
        "segment_ft": [p1, p2],
        "exact_line_matches": exact,
        "nearest_line_placements": line_candidates[:3],
        "nearest_parallel_walls": [
            candidate
            for candidate in wall_candidates
            if candidate["parallel_angle_difference_deg"] <= 2.0
        ][:3],
    }


COORDINATE_PAIR = re.compile(
    r"\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)"
)
FINDING = re.compile(r"^\s*(Warning|Error)\s+(\d+)\s*-\s*(.+?)\s*$", re.I)


def parse_data_check(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rb") as stream:
        root = ET.fromstring(stream.read())
    labels: list[tuple[int, str]] = []
    for index, element in enumerate(root.iter()):
        text = element.attrib.get("Text")
        if text:
            labels.append((index, text))

    findings = []
    coordinate_labels = [
        (index, text, COORDINATE_PAIR.findall(text))
        for index, text in labels
        if "Detected at coordinates" in text
    ]
    used_coordinate_indexes: set[int] = set()
    for index, text in labels:
        match = FINDING.match(text)
        if not match:
            continue
        coordinate_match = min(
            (
                item
                for item in coordinate_labels
                if item[0] not in used_coordinate_indexes
            ),
            key=lambda item: abs(item[0] - index),
            default=None,
        )
        coordinates: list[tuple[float, float]] = []
        if coordinate_match is not None and abs(coordinate_match[0] - index) <= 4:
            used_coordinate_indexes.add(coordinate_match[0])
            coordinates = [
                (float(x), float(y)) for x, y in coordinate_match[2]
            ]
        findings.append(
            {
                "kind": match.group(1).title(),
                "number": int(match.group(2)),
                "message": match.group(3),
                "coordinates_ft": coordinates,
            }
        )
    return sorted(findings, key=lambda item: (item["kind"], item["number"]))


def analyze_rss(
    path: Path,
    *,
    data_check_path: Path | None = None,
    coordinate_tolerance_ft: float = 0.02,
) -> dict[str, Any]:
    if not path.is_file():
        raise RssFormatError(f"RSS does not exist: {path}")
    with zipfile.ZipFile(path, "r") as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RssFormatError(f"ZIP CRC failure: {bad_member}")
        infos = archive.infolist()
        payloads = {info.filename: archive.read(info) for info in infos}

    _, ram_data = member_by_suffix(payloads, ".ram")
    _, flt_data = member_by_suffix(payloads, ".flt")
    _, sty_data = member_by_suffix(payloads, ".sty")
    _, c3d_data = member_by_suffix(payloads, ".c3d")
    _, w3d_data = member_by_suffix(payloads, ".w3d")
    _, lpt_data = member_by_suffix(payloads, ".lpt")
    _, lod_data = member_by_suffix(payloads, ".lod")
    _, pol_data = member_by_suffix(payloads, ".pol")
    _, sec_data = member_by_suffix(payloads, ".sec", required=False)

    fields = ram_fields(ram_data)
    surface_property_count = ram_u32(fields, "NumSLoadProps")
    line_property_count = ram_u32(fields, "NumLLoadProps")
    point_property_count = ram_u32(fields, "NumPLoadProps")

    floor_types = parse_floor_types(flt_data)
    stories = parse_stories(sty_data)
    columns = parse_columns(c3d_data)
    walls = parse_walls(w3d_data)
    sections = parse_concrete_column_sections(sec_data)
    properties = parse_load_properties(
        lpt_data,
        surface_property_count,
        line_property_count,
        point_property_count,
    )
    points = parse_points(pol_data)
    placements, placement_checks = parse_placements(lod_data, points, properties)

    checks = [
        Check("RSS ZIP CRC", True, "all members passed"),
        Check(
            ".ram NumFlrTypes equals .flt records",
            ram_u32(fields, "NumFlrTypes") == len(floor_types),
            f".ram={ram_u32(fields, 'NumFlrTypes')}, .flt={len(floor_types)}",
        ),
        Check(
            ".ram NumStories equals .sty records",
            ram_u32(fields, "NumStories") == len(stories),
            f".ram={ram_u32(fields, 'NumStories')}, .sty={len(stories)}",
        ),
        Check(
            ".flt column totals equal .c3d records",
            sum(floor["counts"]["columns"] for floor in floor_types) == len(columns),
            f".flt={sum(floor['counts']['columns'] for floor in floor_types)}, "
            f".c3d={len(columns)}",
        ),
        Check(
            ".flt wall totals equal .w3d records",
            sum(floor["counts"]["walls"] for floor in floor_types) == len(walls),
            f".flt={sum(floor['counts']['walls'] for floor in floor_types)}, "
            f".w3d={len(walls)}",
        ),
        Check(
            ".ram gravity-column total does not exceed .sty member totals",
            ram_u32(fields, "nNumGravColumns")
            <= sum(story["counts"]["columns"] for story in stories),
            f".ram={ram_u32(fields, 'nNumGravColumns')}, "
            f".sty={sum(story['counts']['columns'] for story in stories)}",
        ),
        Check(
            ".ram gravity-wall total does not exceed .sty member totals",
            ram_u32(fields, "nNumGravWalls")
            <= sum(story["counts"]["walls"] for story in stories),
            f".ram={ram_u32(fields, 'nNumGravWalls')}, "
            f".sty={sum(story['counts']['walls'] for story in stories)}",
        ),
        *placement_checks,
    ]

    result: dict[str, Any] = {
        "source": str(path),
        "sha256": sha256(path),
        "archive_members": [
            {
                "name": info.filename,
                "size": info.file_size,
                "compressed_size": info.compress_size,
            }
            for info in infos
        ],
        "global_counts": {
            "floor_types": ram_u32(fields, "NumFlrTypes"),
            "stories": ram_u32(fields, "NumStories"),
            "gravity_columns": ram_u32(fields, "nNumGravColumns"),
            "gravity_walls": ram_u32(fields, "nNumGravWalls"),
            "surface_load_properties": surface_property_count,
            "line_load_properties": line_property_count,
            "point_load_properties": point_property_count,
            "load_placements": len(placements),
            "coordinate_pool_points": len(points),
        },
        "floor_types": floor_types,
        "stories": stories,
        "concrete_column_sections": sections,
        "columns": columns,
        "walls": walls,
        "load_properties": properties,
        "load_placements": placements,
        "checks": [check.__dict__ for check in checks],
    }

    if data_check_path is not None:
        findings = parse_data_check(data_check_path)
        for finding in findings:
            if len(finding["coordinates_ft"]) == 2:
                finding["rss_correlation"] = correlate_segment(
                    (
                        finding["coordinates_ft"][0],
                        finding["coordinates_ft"][1],
                    ),
                    placements,
                    walls,
                    coordinate_tolerance_ft,
                )
        result["data_check"] = {
            "source": str(data_check_path),
            "findings": findings,
        }
    return result


def compact_report(
    report: dict[str, Any],
    *,
    list_columns: bool,
    list_walls: bool,
    list_loads: bool,
) -> str:
    lines = [
        f"RSS: {report['source']}",
        f"SHA256: {report['sha256']}",
        "Counts: " + ", ".join(
            f"{name}={value}" for name, value in report["global_counts"].items()
        ),
        "",
        "Floor types:",
    ]
    for floor in report["floor_types"]:
        lines.append(
            f"  [{floor['index']}] {floor['label']}: "
            + ", ".join(f"{key}={value}" for key, value in floor["counts"].items())
        )
    lines.append("Stories:")
    for story in report["stories"]:
        lines.append(
            f"  [{story['index']}] {story['label']} "
            f"(height={story['height_in']:g} in): "
            + ", ".join(f"{key}={value}" for key, value in story["counts"].items())
        )
    lines.append("Checks:")
    for check in report["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"  {status}: {check['name']} ({check['detail']})")

    if list_loads:
        lines.append("Load properties:")
        for category, properties in report["load_properties"].items():
            for prop in properties:
                lines.append(
                    f"  {category}[{prop['index']}] {prop['label']}: "
                    f"DL={prop['dead']:.4g}, LL={prop['live']:.4g}, "
                    f"assignments={prop['assignment_count']} {prop['units']}"
                )
    if list_columns:
        lines.append("Columns:")
        for column in report["columns"]:
            lines.append(
                f"  Column {column['number']} at "
                f"({column['x_ft']:.4f}, {column['y_ft']:.4f}) ft, "
                f"section={column['section']}"
            )
    if list_walls:
        lines.append("Walls:")
        for wall in report["walls"]:
            lines.append(
                f"  Wall {wall['number']}: "
                f"({wall['x1_ft']:.4f}, {wall['y1_ft']:.4f}) -> "
                f"({wall['x2_ft']:.4f}, {wall['y2_ft']:.4f}) ft, "
                f"t={wall['thickness_in']:g} in"
            )
    if "data_check" in report:
        lines.append("Data Check correlation:")
        for finding in report["data_check"]["findings"]:
            lines.append(
                f"  {finding['kind']} {finding['number']}: {finding['message']}"
            )
            correlation = finding.get("rss_correlation")
            if not correlation:
                continue
            exact = correlation["exact_line_matches"]
            if exact:
                match = exact[0]
                lines.append(
                    f"    exact .lod match: record={match['record_index']}, "
                    f"property={match['property']}, id={match['id']}, uid={match['uid']}"
                )
            elif correlation["nearest_line_placements"]:
                match = correlation["nearest_line_placements"][0]
                lines.append(
                    f"    nearest .lod: record={match['record_index']}, "
                    f"property={match['property']}, "
                    f"endpoint distance={match['endpoint_distance_ft']:.4f} ft"
                )
            if correlation["nearest_parallel_walls"]:
                wall = correlation["nearest_parallel_walls"][0]
                lines.append(
                    f"    nearest parallel wall: Wall {wall['number']}, "
                    f"midpoint distance={wall['midpoint_distance_ft']:.4f} ft"
                )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only inspection and consistency checks for a RAM RSS archive"
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--data-check", type=Path, help="Optional RAM Data Check .prnx")
    parser.add_argument(
        "--coordinate-tolerance-ft",
        type=float,
        default=0.02,
        help="Endpoint tolerance for matching Data Check segments (default: 0.02 ft)",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--list-columns", action="store_true")
    parser.add_argument("--list-walls", action="store_true")
    parser.add_argument("--list-loads", action="store_true")
    args = parser.parse_args()

    report = analyze_rss(
        args.source,
        data_check_path=args.data_check,
        coordinate_tolerance_ft=args.coordinate_tolerance_ft,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            compact_report(
                report,
                list_columns=args.list_columns,
                list_walls=args.list_walls,
                list_loads=args.list_loads,
            )
        )
    return 0 if all(check["passed"] for check in report["checks"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
