#!/usr/bin/env python3
"""Append unassigned RAM Modeler line-load properties to a separate RSS copy."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import re
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path


PROPERTY_RECORD_SIZE = 72
LINE_UID_SUFFIX = 16
UNREDUCIBLE_LIVE_TYPE = 1265


@dataclass(frozen=True)
class LineLoad:
    label: str
    dead_klf: float
    live_klf: float


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        rb'(<field name="' + re.escape(name.encode("ascii")) + rb'">)'
        rb'([0-9A-Fa-f]{8})(</field>)'
    )
    replacement = struct.pack("<I", value).hex().upper().encode("ascii")
    updated, count = pattern.subn(
        lambda match: match.group(1) + replacement + match.group(3), data
    )
    if count != 1:
        raise SystemExit(f"Expected one RAM field named {name}; found {count}")
    return updated


def read_manifest(path: Path) -> list[LineLoad]:
    loads: list[LineLoad] = []
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        expected = {"Label", "DeadKlf", "LiveKlf"}
        if set(reader.fieldnames or []) != expected:
            raise SystemExit(
                f"CSV columns must be exactly {sorted(expected)}; got {reader.fieldnames}"
            )
        for row_number, row in enumerate(reader, start=2):
            label = (row["Label"] or "").strip()
            try:
                encoded = label.encode("ascii")
            except UnicodeEncodeError as exc:
                raise SystemExit(f"Row {row_number}: label must be ASCII") from exc
            if not encoded or len(encoded) > 20:
                raise SystemExit(
                    f"Row {row_number}: label must contain 1-20 ASCII bytes"
                )
            try:
                dead_klf = float(row["DeadKlf"])
                live_klf = float(row["LiveKlf"])
            except ValueError as exc:
                raise SystemExit(f"Row {row_number}: invalid numeric load") from exc
            if not all(
                math.isfinite(value) and 0 <= value <= 100
                for value in (dead_klf, live_klf)
            ):
                raise SystemExit(
                    f"Row {row_number}: loads must be finite and between 0 and 100 klf"
                )
            loads.append(LineLoad(label, dead_klf, live_klf))
    if not loads:
        raise SystemExit("CSV contains no line loads")
    labels = [load.label.casefold() for load in loads]
    if len(labels) != len(set(labels)):
        raise SystemExit("CSV contains duplicate line-load labels")
    return loads


def make_record(load: LineLoad, ordinal: int) -> bytes:
    label = load.label.encode("ascii").ljust(20, b"\0")
    dead_kip_per_in = load.dead_klf / 12.0
    live_kip_per_in = load.live_klf / 12.0
    uid = ordinal * 1000 + LINE_UID_SUFFIX
    record = struct.pack(
        "<20s5f4i8sfi",
        label,
        dead_kip_per_in,
        0.0,
        0.0,
        live_kip_per_in,
        0.0,
        UNREDUCIBLE_LIVE_TYPE,
        0,
        0,
        uid,
        b"\0" * 8,
        0.0,
        0,
    )
    if len(record) != PROPERTY_RECORD_SIZE:
        raise AssertionError("Internal line-load record size error")
    return record


def decode_record(record: bytes) -> tuple[str, float, float, int, int]:
    label = record[:20].split(b"\0", 1)[0].decode("ascii")
    dead_klf = struct.unpack_from("<f", record, 20)[0] * 12.0
    live_klf = struct.unpack_from("<f", record, 32)[0] * 12.0
    live_type = struct.unpack_from("<i", record, 40)[0]
    uid = struct.unpack_from("<i", record, 52)[0]
    return label, dead_klf, live_klf, live_type, uid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--loads-csv", required=True, type=Path)
    args = parser.parse_args()

    if not args.source.is_file():
        raise SystemExit(f"Source does not exist: {args.source}")
    if args.source.resolve() == args.output.resolve():
        raise SystemExit("Refusing to overwrite the source RSS")
    if args.output.exists():
        raise SystemExit(f"Output already exists: {args.output}")
    loads = read_manifest(args.loads_csv)
    source_hash_before = sha256(args.source)

    with zipfile.ZipFile(args.source, "r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise SystemExit(f"Source ZIP CRC failure: {bad_member}")
        infos = archive.infolist()
        lpt_info = next(
            (info for info in infos if info.filename.lower().endswith(".lpt")), None
        )
        ram_info = next(
            (info for info in infos if info.filename.lower().endswith(".ram")), None
        )
        if lpt_info is None or ram_info is None:
            raise SystemExit("RSS is missing .lpt or .ram data")

        lpt_data = archive.read(lpt_info)
        ram_data = archive.read(ram_info)
        if len(lpt_data) % PROPERTY_RECORD_SIZE:
            raise SystemExit("Unexpected LPT record size")

        surface_count = ram_u32_field(ram_data, "NumSLoadProps")
        line_count = ram_u32_field(ram_data, "NumLLoadProps")
        point_count = ram_u32_field(ram_data, "NumPLoadProps")
        expected_records = surface_count + line_count + point_count
        actual_records = len(lpt_data) // PROPERTY_RECORD_SIZE
        if expected_records != actual_records:
            raise SystemExit(
                "RAM/LPT property totals disagree: "
                f"RAM={expected_records}, LPT={actual_records}"
            )
        if line_count != 0:
            raise SystemExit(
                f"This guarded workflow requires zero existing line properties; found {line_count}"
            )

        surface_end = surface_count * PROPERTY_RECORD_SIZE
        point_data = lpt_data[surface_end:]
        line_data = b"".join(
            make_record(load, ordinal)
            for ordinal, load in enumerate(loads, start=1)
        )
        updated_lpt = lpt_data[:surface_end] + line_data + point_data
        updated_ram = put_ram_u32_field(ram_data, "NumLLoadProps", len(loads))

        original_payloads = {info.filename: archive.read(info) for info in infos}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w") as output:
            output.comment = archive.comment
            for info in infos:
                if info.filename == lpt_info.filename:
                    payload = updated_lpt
                elif info.filename == ram_info.filename:
                    payload = updated_ram
                else:
                    payload = original_payloads[info.filename]
                original_external_attr = info.external_attr
                output.writestr(info, payload)
                info.external_attr = original_external_attr

        source_comment = archive.comment
        source_names = [info.filename for info in infos]

    if sha256(args.source) != source_hash_before:
        raise SystemExit("Source RSS changed during the operation")

    with zipfile.ZipFile(args.output, "r") as output:
        bad_member = output.testzip()
        if bad_member is not None:
            raise SystemExit(f"Output ZIP CRC failure: {bad_member}")
        if output.comment != source_comment:
            raise SystemExit("Archive comment was not preserved")
        if output.namelist() != source_names:
            raise SystemExit("Archive member order or names changed")
        output_lpt = output.read(lpt_info.filename)
        output_ram = output.read(ram_info.filename)
        if ram_u32_field(output_ram, "NumSLoadProps") != surface_count:
            raise SystemExit("Surface-property count changed unexpectedly")
        if ram_u32_field(output_ram, "NumLLoadProps") != len(loads):
            raise SystemExit("Line-property count validation failed")
        if ram_u32_field(output_ram, "NumPLoadProps") != point_count:
            raise SystemExit("Point-property count changed unexpectedly")
        if output_lpt[:surface_end] != lpt_data[:surface_end]:
            raise SystemExit("Existing surface properties changed")
        if output_lpt[surface_end + len(line_data) :] != point_data:
            raise SystemExit("Existing point properties changed")
        for info in infos:
            if info.filename not in {lpt_info.filename, ram_info.filename}:
                if output.read(info.filename) != original_payloads[info.filename]:
                    raise SystemExit(f"Unexpected payload change: {info.filename}")

        for ordinal, expected in enumerate(loads, start=1):
            start = surface_end + (ordinal - 1) * PROPERTY_RECORD_SIZE
            actual = decode_record(output_lpt[start : start + PROPERTY_RECORD_SIZE])
            expected_uid = ordinal * 1000 + LINE_UID_SUFFIX
            if actual[0] != expected.label:
                raise SystemExit(f"Label validation failed for {expected.label}")
            if not math.isclose(actual[1], expected.dead_klf, abs_tol=1e-5):
                raise SystemExit(f"Dead-load validation failed for {expected.label}")
            if not math.isclose(actual[2], expected.live_klf, abs_tol=1e-5):
                raise SystemExit(f"Live-load validation failed for {expected.label}")
            if actual[3] != UNREDUCIBLE_LIVE_TYPE or actual[4] != expected_uid:
                raise SystemExit(f"Metadata validation failed for {expected.label}")

    print(f"Created: {args.output}")
    print(f"Source SHA256: {source_hash_before}")
    print(f"Output SHA256: {sha256(args.output)}")
    print(f"Added {len(loads)} unassigned line-load properties")
    print("Changed archive members: .lpt and .ram only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
