#!/usr/bin/env python3
"""Reassign a complete contiguous RAM layout-column block to an earlier floor type."""

from __future__ import annotations

import argparse
import struct
import zipfile
from pathlib import Path


FLOOR_RECORD_SIZE = 472
COLUMN_COUNT_OFFSET = 24
COLUMN_START_OFFSET = 100
LAST_COLUMN_LABEL_OFFSET = 288


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def put_u32(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", data, offset, value)


def label(record: bytes) -> str:
    return record[:24].split(b"\0", 1)[0].decode("ascii", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-layout", required=True)
    parser.add_argument("--target-layout", required=True)
    args = parser.parse_args()

    if args.source.resolve() == args.output.resolve():
        raise SystemExit("Refusing to overwrite the source RSS")
    if args.output.exists():
        raise SystemExit(f"Output already exists: {args.output}")

    with zipfile.ZipFile(args.source, "r") as archive:
        infos = archive.infolist()
        flt_info = next((item for item in infos if item.filename.lower().endswith(".flt")), None)
        col_info = next((item for item in infos if item.filename.lower().endswith(".col")), None)
        if flt_info is None or col_info is None:
            raise SystemExit("RSS is missing .flt or .col data")

        floors = bytearray(archive.read(flt_info))
        if len(floors) % FLOOR_RECORD_SIZE:
            raise SystemExit("Unexpected FLT record size")
        floor_count = len(floors) // FLOOR_RECORD_SIZE
        labels = [label(floors[i * FLOOR_RECORD_SIZE:(i + 1) * FLOOR_RECORD_SIZE]) for i in range(floor_count)]
        try:
            source_index = next(i for i, value in enumerate(labels) if value.lower() == args.source_layout.lower())
            target_index = next(i for i, value in enumerate(labels) if value.lower() == args.target_layout.lower())
        except StopIteration:
            raise SystemExit(f"Layouts not found. Available layouts: {', '.join(labels)}")
        if target_index >= source_index:
            raise SystemExit("This operation requires the target layout to precede the source layout")

        target_base = target_index * FLOOR_RECORD_SIZE
        source_base = source_index * FLOOR_RECORD_SIZE
        target_count = u32(floors, target_base + COLUMN_COUNT_OFFSET)
        source_count = u32(floors, source_base + COLUMN_COUNT_OFFSET)
        total_count = sum(
            u32(floors, i * FLOOR_RECORD_SIZE + COLUMN_COUNT_OFFSET)
            for i in range(floor_count)
        )
        if target_count == 0 or source_count == 0:
            raise SystemExit(f"Expected nonempty layouts; target={target_count}, source={source_count}")
        if target_count + source_count != total_count:
            raise SystemExit(
                f"Target and source do not own the complete column block: "
                f"target={target_count}, source={source_count}, total={total_count}"
            )
        if u32(floors, target_base + COLUMN_START_OFFSET) != 0:
            raise SystemExit("Target column block does not start at index 0")
        if u32(floors, source_base + COLUMN_START_OFFSET) != target_count:
            raise SystemExit("Source column block is not contiguous with the target block")

        merged_count = target_count + source_count
        merged_last_label = (
            u32(floors, target_base + LAST_COLUMN_LABEL_OFFSET)
            + u32(floors, source_base + LAST_COLUMN_LABEL_OFFSET)
        )
        put_u32(floors, target_base + COLUMN_COUNT_OFFSET, merged_count)
        put_u32(floors, target_base + COLUMN_START_OFFSET, 0)
        put_u32(floors, target_base + LAST_COLUMN_LABEL_OFFSET, merged_last_label)
        for floor_index in range(target_index + 1, floor_count):
            base = floor_index * FLOOR_RECORD_SIZE
            put_u32(floors, base + COLUMN_START_OFFSET, merged_count)
        put_u32(floors, source_base + COLUMN_COUNT_OFFSET, 0)
        put_u32(floors, source_base + LAST_COLUMN_LABEL_OFFSET, 0)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w") as output:
            for info in infos:
                payload = bytes(floors) if info.filename == flt_info.filename else archive.read(info)
                output.writestr(info, payload)

    print(f"Created: {args.output}")
    print(f"Merged {target_count} + {source_count} = {merged_count} columns into {args.target_layout}")
    print(f"{args.source_layout} now contains 0 columns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
