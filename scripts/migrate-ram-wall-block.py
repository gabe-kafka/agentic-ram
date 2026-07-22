#!/usr/bin/env python3
"""Experimentally reassign a complete contiguous RAM wall block between floor types.

This operates on a copy of an RSS ZIP container. It intentionally supports only
the proven case where the target floor has zero walls and the source owns the
entire W3D wall array.
"""

from __future__ import annotations

import argparse
import io
import struct
import zipfile
from pathlib import Path


FLOOR_RECORD_SIZE = 472
WALL_RECORD_SIZE = 584
WALL_COUNT_OFFSET = 28
WALL_START_OFFSET = 80
NEXT_WALL_LABEL_OFFSET = 292


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def put_u32(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", data, offset, value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-floor", type=int, required=True)
    parser.add_argument("--target-floor", type=int, required=True)
    args = parser.parse_args()

    if args.source.resolve() == args.output.resolve():
        raise SystemExit("Refusing to overwrite the source RSS")
    if args.output.exists():
        raise SystemExit(f"Output already exists: {args.output}")

    with zipfile.ZipFile(args.source, "r") as archive:
        infos = archive.infolist()
        flt_info = next((item for item in infos if item.filename.lower().endswith(".flt")), None)
        w3d_info = next((item for item in infos if item.filename.lower().endswith(".w3d")), None)
        if flt_info is None or w3d_info is None:
            raise SystemExit("RSS is missing .flt or .w3d data")

        floors = bytearray(archive.read(flt_info))
        walls = archive.read(w3d_info)
        if len(floors) % FLOOR_RECORD_SIZE:
            raise SystemExit("Unexpected FLT record size")
        if len(walls) % WALL_RECORD_SIZE:
            raise SystemExit("Unexpected W3D record size")

        floor_count = len(floors) // FLOOR_RECORD_SIZE
        if not (0 <= args.source_floor < floor_count and 0 <= args.target_floor < floor_count):
            raise SystemExit("Floor index is outside the FLT array")
        if args.target_floor >= args.source_floor:
            raise SystemExit("This proven migration requires the target before the source")

        source_base = args.source_floor * FLOOR_RECORD_SIZE
        target_base = args.target_floor * FLOOR_RECORD_SIZE
        source_count = u32(floors, source_base + WALL_COUNT_OFFSET)
        target_count = u32(floors, target_base + WALL_COUNT_OFFSET)
        total_walls = len(walls) // WALL_RECORD_SIZE

        if target_count != 0:
            raise SystemExit("Target floor is not empty")
        if source_count != total_walls:
            raise SystemExit(
                f"Source does not own the complete wall block: source={source_count}, total={total_walls}"
            )

        max_label = max(u32(walls, offset + 52) for offset in range(0, len(walls), WALL_RECORD_SIZE))
        put_u32(floors, target_base + WALL_COUNT_OFFSET, source_count)
        put_u32(floors, target_base + NEXT_WALL_LABEL_OFFSET, max_label + 1)
        put_u32(floors, source_base + WALL_COUNT_OFFSET, 0)
        put_u32(floors, source_base + WALL_START_OFFSET, source_count)
        put_u32(floors, source_base + NEXT_WALL_LABEL_OFFSET, 1)

        for floor_index in range(args.source_floor + 1, floor_count):
            base = floor_index * FLOOR_RECORD_SIZE
            put_u32(floors, base + WALL_START_OFFSET, source_count)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w") as output:
            for info in infos:
                payload = bytes(floors) if info.filename == flt_info.filename else archive.read(info)
                output.writestr(info, payload)

    print(f"Created: {args.output}")
    print(f"Reassigned {source_count} walls from floor index {args.source_floor} to {args.target_floor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
