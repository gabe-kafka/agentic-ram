#!/usr/bin/env python3
"""Move a complete RAM layout-column block into an earlier empty floor type."""

from __future__ import annotations

import argparse
import re
import struct
import zipfile
from pathlib import Path


FLOOR_RECORD_SIZE = 472
STORY_RECORD_SIZE = 336
COLUMN_RECORD_SIZE = 1072
COLUMN_COUNT_OFFSET = 24
COLUMN_START_OFFSET = 76
LAST_COLUMN_LABEL_OFFSET = 288
STORY_COLUMN_COUNT_OFFSET = 52
STORY_COLUMN_START_OFFSET = 168
FLOOR_STORY_SIGNATURE_OFFSETS = (
    (24, 52),
    (28, 56),
    (32, 60),
    (76, 168),
    (80, 172),
    (84, 176),
)


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def put_u32(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", data, offset, value)


def label(record: bytes) -> str:
    return record[:24].split(b"\0", 1)[0].decode("ascii", errors="replace")


def ram_u32_field(data: bytes, name: str) -> int:
    pattern = re.compile(
        rb'<field name="' + re.escape(name.encode("ascii")) + rb'">([0-9A-Fa-f]{8})</field>'
    )
    matches = list(pattern.finditer(data))
    if len(matches) != 1:
        raise SystemExit(f"Expected one RAM field named {name}; found {len(matches)}")
    return struct.unpack("<I", bytes.fromhex(matches[0].group(1).decode("ascii")))[0]


def put_ram_u32_field(data: bytes, name: str, value: int) -> bytes:
    pattern = re.compile(
        rb'(<field name="' + re.escape(name.encode("ascii")) + rb'">)([0-9A-Fa-f]{8})(</field>)'
    )
    replacement = struct.pack("<I", value).hex().upper().encode("ascii")
    updated, count = pattern.subn(lambda match: match.group(1) + replacement + match.group(3), data)
    if count != 1:
        raise SystemExit(f"Expected one RAM field named {name}; found {count}")
    return updated


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
        c3d_info = next((item for item in infos if item.filename.lower().endswith(".c3d")), None)
        sty_info = next((item for item in infos if item.filename.lower().endswith(".sty")), None)
        ram_info = next((item for item in infos if item.filename.lower().endswith(".ram")), None)
        if flt_info is None or c3d_info is None or sty_info is None or ram_info is None:
            raise SystemExit("RSS is missing .flt, .c3d, .sty, or .ram data")

        floors = bytearray(archive.read(flt_info))
        columns = archive.read(c3d_info)
        stories = bytearray(archive.read(sty_info))
        ram_data = archive.read(ram_info)
        if len(floors) % FLOOR_RECORD_SIZE:
            raise SystemExit("Unexpected FLT record size")
        if len(columns) % COLUMN_RECORD_SIZE:
            raise SystemExit("Unexpected C3D record size")
        if not stories or len(stories) % STORY_RECORD_SIZE:
            raise SystemExit("Unexpected STY record size")
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
        metadata_total = sum(
            u32(floors, i * FLOOR_RECORD_SIZE + COLUMN_COUNT_OFFSET)
            for i in range(floor_count)
        )
        total_count = len(columns) // COLUMN_RECORD_SIZE
        if source_count == 0:
            raise SystemExit("Source layout contains no columns")
        if target_count != 0:
            raise SystemExit("Target layout is not empty")
        if metadata_total != total_count:
            raise SystemExit(
                f"FLT/C3D column totals disagree: metadata={metadata_total}, C3D={total_count}"
            )
        if source_count != total_count:
            raise SystemExit(
                f"Source does not own the complete column block: "
                f"source={source_count}, total={total_count}"
            )
        source_start = u32(floors, source_base + COLUMN_START_OFFSET)
        if source_start != 0:
            raise SystemExit("Source column block does not start at index 0")

        def floor_signature(base: int) -> tuple[int, ...]:
            return tuple(u32(floors, base + floor_offset) for floor_offset, _ in FLOOR_STORY_SIGNATURE_OFFSETS)

        def story_signature(base: int) -> tuple[int, ...]:
            return tuple(u32(stories, base + story_offset) for _, story_offset in FLOOR_STORY_SIGNATURE_OFFSETS)

        target_signature = floor_signature(target_base)
        source_signature = floor_signature(source_base)
        story_count = len(stories) // STORY_RECORD_SIZE
        target_story_indexes = [
            index
            for index in range(story_count)
            if story_signature(index * STORY_RECORD_SIZE) == target_signature
        ]
        source_story_indexes = [
            index
            for index in range(story_count)
            if story_signature(index * STORY_RECORD_SIZE) == source_signature
        ]
        if not target_story_indexes:
            raise SystemExit("Target layout is not represented in Story Data")
        if source_story_indexes:
            raise SystemExit("Source layout is represented in Story Data; this case is not supported")

        story_column_total = sum(
            u32(stories, index * STORY_RECORD_SIZE + STORY_COLUMN_COUNT_OFFSET)
            for index in range(story_count)
        )
        ram_gravity_columns = ram_u32_field(ram_data, "nNumGravColumns")
        if ram_gravity_columns != story_column_total:
            raise SystemExit(
                f"RAM/STY gravity-column totals disagree: RAM={ram_gravity_columns}, "
                f"STY={story_column_total}"
            )

        merged_count = source_count
        merged_last_label = u32(floors, source_base + LAST_COLUMN_LABEL_OFFSET)
        put_u32(floors, target_base + COLUMN_COUNT_OFFSET, merged_count)
        put_u32(floors, target_base + COLUMN_START_OFFSET, 0)
        put_u32(floors, target_base + LAST_COLUMN_LABEL_OFFSET, merged_last_label)
        for floor_index in range(target_index + 1, floor_count):
            base = floor_index * FLOOR_RECORD_SIZE
            put_u32(floors, base + COLUMN_START_OFFSET, merged_count)
        put_u32(floors, source_base + COLUMN_COUNT_OFFSET, 0)
        put_u32(floors, source_base + LAST_COLUMN_LABEL_OFFSET, 0)

        for story_index in target_story_indexes:
            base = story_index * STORY_RECORD_SIZE
            put_u32(stories, base + STORY_COLUMN_COUNT_OFFSET, merged_count)
            put_u32(stories, base + STORY_COLUMN_START_OFFSET, 0)

        migrated_story_columns = merged_count * len(target_story_indexes)
        ram_data = put_ram_u32_field(ram_data, "bModelHasSteelColumns", 1)
        ram_data = put_ram_u32_field(
            ram_data,
            "nNumGravColumns",
            story_column_total + migrated_story_columns,
        )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w") as output:
            output.comment = archive.comment
            for info in infos:
                if info.filename == flt_info.filename:
                    payload = bytes(floors)
                elif info.filename == sty_info.filename:
                    payload = bytes(stories)
                elif info.filename == ram_info.filename:
                    payload = ram_data
                else:
                    payload = archive.read(info)
                original_external_attr = info.external_attr
                output.writestr(info, payload)
                info.external_attr = original_external_attr

    print(f"Created: {args.output}")
    print(f"Moved {source_count} columns into {args.target_layout}")
    print(f"Updated {len(target_story_indexes)} matching Story Data record(s)")
    print(f"{args.source_layout} now contains 0 columns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
