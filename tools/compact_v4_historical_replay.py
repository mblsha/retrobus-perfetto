#!/usr/bin/env python3
"""Reproduce the historical Redux v3/v4 diagnostic density audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any
import zlib


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPOSITORY_ROOT / "py"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from retrobus_perfetto.compact import (  # noqa: E402
    CompactRecord,
    CompactTrace,
    CompactTraceHeader,
)
from retrobus_perfetto.compact_codec import (  # noqa: E402
    CompactCodecProfile,
    CompactCodecProfileError,
)
from retrobus_perfetto.compact_profile import model_compact_trace  # noqa: E402
from retrobus_perfetto.compact_schema import (  # noqa: E402
    CompactSchema,
    CompactSchemaError,
)


RDX_HEADER_BYTES = 96
RDX_CHUNK_BYTES = 4096
RDX_CHUNK_HEADER_BYTES = 32
RDX_PAYLOAD_BYTES = RDX_CHUNK_BYTES - RDX_CHUNK_HEADER_BYTES
RBCT_CHUNK_BYTES = 4096
RBCT_CHUNK_HEADER_BYTES = 48
RBCT_PAYLOAD_BYTES = RBCT_CHUNK_BYTES - RBCT_CHUNK_HEADER_BYTES


class HistoricalReplayError(ValueError):
    """A historical audit input or preserved result is inconsistent."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_uleb(data: bytes, offset: int, limit: int) -> tuple[int, int]:
    value = 0
    for index in range(10):
        if offset >= limit:
            raise HistoricalReplayError("historical RDX record is truncated")
        byte = data[offset]
        offset += 1
        if index == 9 and byte > 1:
            raise HistoricalReplayError("historical RDX ULEB128 exceeds uint64")
        value |= (byte & 0x7F) << (index * 7)
        if byte & 0x80 == 0:
            if index and byte == 0:
                raise HistoricalReplayError(
                    "historical RDX ULEB128 is not canonical"
                )
            return value, offset
    raise HistoricalReplayError("historical RDX ULEB128 is oversized")


def _logical_digest(records: list[CompactRecord]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(
            struct.pack(
                "<IQB",
                record.event.id,
                record.raw_timestamp,
                record.duration_ticks is not None,
            )
        )
        if record.duration_ticks is not None:
            digest.update(struct.pack("<Q", record.duration_ticks))
        digest.update(struct.pack("<B", len(record.arguments)))
        for argument in record.arguments:
            digest.update(struct.pack("<Q", int(argument)))
    return digest.hexdigest()


def _read_historical_capture(
    path: Path, schema: CompactSchema
) -> tuple[CompactTrace, dict[str, Any]]:
    data = path.read_bytes()
    if (
        len(data) < RDX_HEADER_BYTES + RDX_CHUNK_BYTES
        or data[:8] != b"RDXTRC1\0"
        or struct.unpack_from("<HHHHI", data, 8)
        != (1, RDX_HEADER_BYTES, RDX_CHUNK_HEADER_BYTES, 1, RDX_CHUNK_BYTES)
        or (len(data) - RDX_HEADER_BYTES) % RDX_CHUNK_BYTES
    ):
        raise HistoricalReplayError(f"{path} is not the expected finalized RDXTRC1 layout")
    total_events, overwritten_events, total_records, overwritten_records = (
        struct.unpack_from("<QQQQ", data, 32)
    )
    retained_events, retained_records = struct.unpack_from("<QQ", data, 64)
    if overwritten_events or overwritten_records:
        raise HistoricalReplayError(f"{path} is not a complete non-wrapped corpus")
    if retained_events != total_events or retained_records != total_records:
        raise HistoricalReplayError(f"{path} has inconsistent retained counts")

    records: list[CompactRecord] = []
    source_payload_bytes = 0
    source_chunk_cursors: list[int] = []
    expanded_events = 0
    chunk_count = (len(data) - RDX_HEADER_BYTES) // RDX_CHUNK_BYTES
    for physical_index in range(chunk_count):
        chunk_offset = RDX_HEADER_BYTES + physical_index * RDX_CHUNK_BYTES
        chunk = data[chunk_offset : chunk_offset + RDX_CHUNK_BYTES]
        if chunk[:4] != b"RTCK":
            raise HistoricalReplayError(
                f"{path} chunk {physical_index} has invalid magic"
            )
        sequence = struct.unpack_from("<I", chunk, 4)[0]
        base_timestamp = struct.unpack_from("<Q", chunk, 8)[0]
        used, expected_records = struct.unpack_from("<HH", chunk, 16)
        expected_events, expected_crc, reserved = struct.unpack_from("<III", chunk, 20)
        if sequence != physical_index or used > RDX_PAYLOAD_BYTES or reserved:
            raise HistoricalReplayError(
                f"{path} chunk {physical_index} has invalid metadata"
            )
        payload = chunk[RDX_CHUNK_HEADER_BYTES : RDX_CHUNK_HEADER_BYTES + used]
        if zlib.crc32(payload) & 0xFFFF_FFFF != expected_crc:
            raise HistoricalReplayError(
                f"{path} chunk {physical_index} payload CRC mismatch"
            )
        offset = 0
        timestamp = base_timestamp
        decoded_records = 0
        decoded_events = 0
        while offset < len(payload):
            event_id = payload[offset]
            offset += 1
            event = schema.events.get(event_id)
            if event is None:
                raise HistoricalReplayError(
                    f"{path} chunk {physical_index} uses unknown event {event_id}"
                )
            delta, offset = _read_uleb(payload, offset, len(payload))
            timestamp += delta
            duration: int | None = None
            if event.kind == "slice":
                duration, offset = _read_uleb(payload, offset, len(payload))
            arguments: list[int] = []
            for argument in event.arguments:
                if argument.type != "uint":
                    raise HistoricalReplayError(
                        "historical RDX replay supports its original uint arguments only"
                    )
                value, offset = _read_uleb(payload, offset, len(payload))
                arguments.append(value)
            records.append(
                CompactRecord(
                    event,
                    0,
                    0,
                    timestamp,
                    duration,
                    tuple(arguments),
                    len(records),
                )
            )
            decoded_records += 1
            decoded_events += 2 if event.kind == "slice" else 1
        if decoded_records != expected_records or decoded_events != expected_events:
            raise HistoricalReplayError(
                f"{path} chunk {physical_index} decoded counts disagree with its header"
            )
        source_payload_bytes += used
        source_chunk_cursors.append(used)
        expanded_events += decoded_events
    if len(records) != total_records or expanded_events != total_events:
        raise HistoricalReplayError(f"{path} decoded totals disagree with its header")

    header = CompactTraceHeader(
        "retrobus-compact-v3",
        1,
        1_000_000,
        1,
        64,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"\0" * 16,
        len(records),
        0,
        0,
        expanded_events,
        0,
        160 + chunk_count * RBCT_CHUNK_BYTES,
        0,
        0,
    )
    source_slack = chunk_count * RDX_PAYLOAD_BYTES - source_payload_bytes
    source = {
        "format": "RDXTRC1",
        "container_bytes": len(data),
        "file_header_bytes": RDX_HEADER_BYTES,
        "chunks": chunk_count,
        "chunk_header_bytes": chunk_count * RDX_CHUNK_HEADER_BYTES,
        "payload_bytes": source_payload_bytes,
        "chunk_slack_bytes": source_slack,
        "chunk_used_lengths": source_chunk_cursors,
        "records": len(records),
        "expanded_events": expanded_events,
        "logical_records_sha256": _logical_digest(records),
    }
    return CompactTrace(header, schema, tuple(records), ()), source


def _model_summary(model: dict[str, Any], *, version: int) -> dict[str, Any]:
    chunks = int(model["chunks_started"])
    header_bytes = 192 if version == 4 else 160
    payload_bytes = int(model["payload_bytes"])
    chunk_slack = chunks * RBCT_PAYLOAD_BYTES - payload_bytes
    result: dict[str, Any] = {
        "payload_bytes": payload_bytes,
        "payload_bytes_per_record": payload_bytes / int(model["records"]),
        "chunks": chunks,
        "file_header_bytes": header_bytes,
        "chunk_header_bytes": chunks * RBCT_CHUNK_HEADER_BYTES,
        "chunk_slack_bytes": chunk_slack,
        "container_bytes": header_bytes + chunks * RBCT_CHUNK_BYTES,
        "chunk_used_lengths": model["chunk_used_lengths"],
    }
    if version == 4:
        hits = model["special_opcode_hits"]
        result.update(
            {
                "payload_bits": model["payload_bits"],
                "payload_bits_per_record": model["bits_per_record"],
                "chunk_used_bits": model["chunk_used_bits"],
                "profile_hits": hits.get("profile_hit", 0),
                "profile_misses": hits.get("profile_miss", 0),
                "bit_attribution": model["bit_attribution"],
            }
        )
    return result


def _load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("format") != "retrobus-compact-v4-audit-manifest-v1":
        raise HistoricalReplayError("unsupported historical audit manifest")
    return value


def _replay(
    manifest: dict[str, Any], corpus_root: Path, schema_path: Path
) -> tuple[dict[str, Any], dict[int, CompactCodecProfile]]:
    schema_bytes = schema_path.read_bytes()
    schema = CompactSchema.load(schema_path)
    expected_schema = manifest["schema"]
    if _sha256(schema_bytes) != expected_schema["file_sha256"]:
        raise HistoricalReplayError("schema file SHA-256 mismatch")
    if schema.sha256.hex() != expected_schema["canonical_sha256"]:
        raise HistoricalReplayError("canonical schema SHA-256 mismatch")

    traces: dict[str, CompactTrace] = {}
    capture_results: dict[str, Any] = {}
    for capture in manifest["captures"]:
        capture_path = corpus_root / capture["path"]
        capture_bytes = capture_path.read_bytes()
        if len(capture_bytes) != capture["bytes"]:
            raise HistoricalReplayError(f"{capture['id']} size mismatch")
        if _sha256(capture_bytes) != capture["sha256"]:
            raise HistoricalReplayError(f"{capture['id']} SHA-256 mismatch")
        trace, source = _read_historical_capture(capture_path, schema)
        traces[capture["id"]] = trace
        capture_results[capture["id"]] = {
            "provenance": {
                key: value
                for key, value in capture.items()
                if key not in {"path", "sha256", "bytes"}
            },
            "input": {
                "path": capture["path"],
                "sha256": capture["sha256"],
                "bytes": capture["bytes"],
                **source,
            },
        }

    training = manifest["training"]
    training_traces = [traces[capture_id] for capture_id in training["capture_ids"]]
    state_events = tuple(training["state_events"])
    profiles = {
        entry_limit: CompactCodecProfile.train(
            training_traces,
            schema,
            entry_limit=entry_limit,
            state_events=(state_events[0], state_events[1]),
        )
        for entry_limit in training["entry_limits"]
    }
    for capture_id, trace in traces.items():
        v3 = dict(model_compact_trace(trace, 3, chunk_count=len(trace.records)))
        capture_results[capture_id]["v3"] = _model_summary(v3, version=3)
        for entry_limit, profile in profiles.items():
            v4 = dict(
                model_compact_trace(
                    trace,
                    4,
                    chunk_count=len(trace.records),
                    codec_profile=profile,
                )
            )
            capture_results[capture_id][f"v4_profile_{entry_limit}"] = _model_summary(
                v4, version=4
            )

    results = {
        "format": "retrobus-compact-v4-historical-replay-v1",
        "methodology": manifest["methodology"],
        "schema": {
            "path": expected_schema["path"],
            "file_sha256": expected_schema["file_sha256"],
            "canonical_sha256": schema.sha256.hex(),
            "producer_id": schema.producer_id,
            "version": schema.version,
            "events": len(schema.events),
        },
        "training": training,
        "profiles": {
            str(entry_limit): {
                "path": manifest["outputs"]["profiles"][str(entry_limit)],
                "sha256": profile.sha256.hex(),
                "entries": len(profile.entries),
                "state_events": list(profile.state_events),
            }
            for entry_limit, profile in profiles.items()
        },
        "captures": capture_results,
    }
    return results, profiles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--corpus-root", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="regenerate preserved outputs")
    mode.add_argument("--verify", action="store_true", help="compare preserved outputs")
    args = parser.parse_args()
    try:
        manifest = _load_manifest(args.manifest)
        results, profiles = _replay(manifest, args.corpus_root, args.schema)
        output_root = args.manifest.parent
        generated: dict[Path, bytes] = {
            output_root / manifest["outputs"]["results"]: (
                json.dumps(results, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
        }
        for entry_limit, profile in profiles.items():
            generated[
                output_root / manifest["outputs"]["profiles"][str(entry_limit)]
            ] = profile.canonical_json + b"\n"
        if args.write:
            for path, data in generated.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        else:
            for path, expected in generated.items():
                if not path.exists() or path.read_bytes() != expected:
                    raise HistoricalReplayError(f"preserved output differs: {path}")
    except (
        CompactCodecProfileError,
        CompactSchemaError,
        HistoricalReplayError,
        OSError,
        ValueError,
    ) as error:
        parser.error(str(error))
    for entry_limit, profile in sorted(profiles.items()):
        print(
            f"profile-{entry_limit}={profile.sha256.hex()} "
            f"entries={len(profile.entries)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
