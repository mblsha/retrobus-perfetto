"""Format and reconstruction tests for compact traces."""

from __future__ import annotations

import json
from pathlib import Path
import struct
import zlib

import pytest

from retrobus_perfetto import (
    CompactSchema,
    CompactSchemaError,
    CompactTraceError,
    compact_trace_to_builder,
    read_compact_trace,
    render_c_schema_header,
    resolve_interned_trace,
)
from retrobus_perfetto.proto import perfetto_pb2


def _schema_mapping() -> dict[str, object]:
    return {
        "format": "retrobus-compact-schema-v1",
        "producer": {"id": 42, "name": "test-target"},
        "version": 1,
        "process": "Compact test target",
        "tracks": [
            {"id": 0, "name": "main", "kind": "thread"},
            {"id": 1, "name": "bytes", "kind": "counter", "unit": "bytes"},
        ],
        "events": [
            {
                "id": 1,
                "name": "work",
                "category": "runtime",
                "kind": "slice",
                "id_argument": "entry",
                "constant_arguments": [
                    {"name": "abi", "type": "uint", "value": 5}
                ],
                "arguments": [{"name": "amount", "type": "uint"}],
            },
            {
                "id": 2,
                "name": "fault",
                "category": "runtime",
                "kind": "instant",
                "arguments": [{"name": "error", "type": "sint"}],
            },
            {
                "id": 3,
                "name": "bytes",
                "category": "storage",
                "kind": "counter",
                "arguments": [{"name": "value", "type": "uint"}],
            },
            {
                "id": 4,
                "name": "request",
                "category": "io",
                "kind": "flow_start",
                "correlation_argument": "id",
                "arguments": [{"name": "id", "type": "uint"}],
            },
            {
                "id": 5,
                "name": "request",
                "category": "io",
                "kind": "flow_end",
                "correlation_argument": "id",
                "arguments": [{"name": "id", "type": "uint"}],
            },
            {
                "id": 6,
                "name": "transfer",
                "category": "io",
                "kind": "async_begin",
                "correlation_argument": "id",
                "arguments": [
                    {"name": "id", "type": "uint"},
                    {"name": "amount", "type": "uint"},
                ],
            },
            {
                "id": 7,
                "name": "transfer",
                "category": "io",
                "kind": "async_end",
                "correlation_argument": "id",
                "arguments": [
                    {"name": "id", "type": "uint"},
                    {"name": "status", "type": "sint"},
                ],
            },
            {
                "id": 300,
                "name": "address",
                "category": "runtime",
                "kind": "instant",
                "arguments": [{"name": "address", "type": "fixed64"}],
            },
        ],
    }


@pytest.fixture
def schema() -> CompactSchema:
    return CompactSchema.from_mapping(_schema_mapping())


def _uleb(value: int) -> bytes:
    result = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        result.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(result)


def _zigzag(value: int) -> int:
    return (value << 1) ^ (value >> 63)


def _rbct_image(schema: CompactSchema) -> bytes:
    payload = bytearray()
    payload += bytes([0xFD])
    payload += _uleb(7) + _uleb(100) + _uleb(102)
    payload += _uleb(1_000_000) + _uleb(300)
    payload += bytes([1]) + _uleb(50) + _uleb(40) + _uleb(42)
    payload += bytes([2]) + _uleb(10) + _uleb(_zigzag(-7))
    payload += bytes([0xFE]) + _uleb(1)
    payload += bytes([3]) + _uleb(10) + _uleb(99)
    payload += bytes([0xFE]) + _uleb(0)
    payload += bytes([4]) + _uleb(10) + _uleb(123)
    payload += bytes([5]) + _uleb(10) + _uleb(123)
    payload += bytes([6]) + _uleb(10) + _uleb(8) + _uleb(1024)
    payload += bytes([7]) + _uleb(20) + _uleb(8) + _uleb(_zigzag(0))
    payload += bytes([0xFF]) + _uleb(300) + _uleb(10)
    payload += struct.pack("<Q", 0xDEAD_BEEF_1234_5678)

    chunk = bytearray(4096)
    chunk[:4] = b"RBCK"
    struct.pack_into("<QQIIHHIHHI", chunk, 4, 0, 100, 7, 0,
                     len(payload), 8, 9, 1, 0, zlib.crc32(payload) & 0xFFFF_FFFF)
    chunk[48 : 48 + len(payload)] = payload

    header = bytearray(160)
    header[:8] = b"RBCTRC1\0"
    struct.pack_into("<HHHHIQQHHII", header, 8, 1, 160, 48, 0, 4096,
                     1_000_000, 1, 32, 1, schema.producer_id, schema.version)
    header[48:80] = schema.sha256
    header[80:96] = bytes(range(16))
    struct.pack_into("<QQQQQQII", header, 96, 8, 0, 0, 9, 0, 4256, 7, 0)
    struct.pack_into("<I", header, 152, 0)
    struct.pack_into("<I", header, 152, zlib.crc32(header) & 0xFFFF_FFFF)
    return bytes(header + chunk)


def _event_rows(builder) -> list[tuple[int, int, str, tuple[tuple[str, object], ...]]]:
    trace = perfetto_pb2.Trace()
    trace.ParseFromString(builder.serialize())
    resolve_interned_trace(trace, inplace=True)
    rows = []
    for packet in trace.packet:
        if not packet.HasField("track_event"):
            continue
        event = packet.track_event
        if event.name == "clock sync":
            continue
        annotations = []
        for argument in event.debug_annotations:
            field = argument.WhichOneof("value")
            annotations.append((argument.name, getattr(argument, field)))
        rows.append((packet.timestamp, event.type, event.name, tuple(annotations)))
    return rows


def test_schema_hash_and_header_are_deterministic(schema: CompactSchema) -> None:
    reloaded = CompactSchema.from_mapping(
        json.loads(schema.canonical_json.decode("utf-8"))
    )
    assert reloaded.sha256 == schema.sha256
    header = render_c_schema_header(schema, "demo")
    assert "DEMO_TRACE_EVENT_WORK UINT32_C(1)" in header
    assert "DEMO_TRACE_EVENT_ADDRESS UINT32_C(300)" in header
    assert "DEMO_TRACE_EVENT_REQUEST_4 UINT32_C(4)" in header
    assert "DEMO_TRACE_EVENT_REQUEST_5 UINT32_C(5)" in header
    assert ", ".join(f"0x{byte:02x}" for byte in schema.sha256) in header


def test_schema_rejects_colliding_and_mistyped_derived_arguments() -> None:
    mapping = _schema_mapping()
    events = mapping["events"]
    assert isinstance(events, list)
    work = events[0]
    assert isinstance(work, dict)
    work["id_argument"] = "amount"
    with pytest.raises(CompactSchemaError, match="collides with a stored argument"):
        CompactSchema.from_mapping(mapping)

    mapping = _schema_mapping()
    events = mapping["events"]
    assert isinstance(events, list)
    work = events[0]
    assert isinstance(work, dict)
    constants = work["constant_arguments"]
    assert isinstance(constants, list)
    constant = constants[0]
    assert isinstance(constant, dict)
    constant["value"] = -1
    with pytest.raises(CompactSchemaError, match="outside unsigned 64-bit"):
        CompactSchema.from_mapping(mapping)


def test_read_and_reconstruct_all_generic_event_kinds(
    tmp_path: Path, schema: CompactSchema
) -> None:
    path = tmp_path / "capture.rbct"
    path.write_bytes(_rbct_image(schema))
    trace = read_compact_trace(path, schema)

    assert trace.header.finalized
    assert trace.header.retained_records == 8
    assert trace.header.retained_events == 9
    assert len(trace.clock_syncs) == 1
    assert trace.clock_syncs[0].extended_tick == 101
    assert trace.records[0].event.name == "work"
    assert trace.records[0].arguments == (42,)
    assert trace.records[1].arguments == (-7,)
    assert trace.records[2].track_id == 1
    assert trace.records[-1].event.id == 300
    assert trace.records[-1].arguments == (0xDEAD_BEEF_1234_5678,)
    assert trace.timestamp_ns(7, trace.records[0].extended_tick) == 1_049_000

    builder = compact_trace_to_builder(trace)
    rows = _event_rows(builder)
    names = [row[2] for row in rows]
    assert names.count("work") == 1
    assert "fault" in names
    assert names.count("request") == 2
    assert names.count("transfer") == 1
    assert "address" in names
    work = next(row for row in rows if row[2] == "work")
    assert work[3] == (("entry", 1), ("abi", 5), ("amount", 42))

    parsed = perfetto_pb2.Trace()
    parsed.ParseFromString(builder.serialize())
    flow_events = [
        packet.track_event
        for packet in parsed.packet
        if packet.HasField("track_event")
        and (packet.track_event.flow_ids or packet.track_event.terminating_flow_ids)
    ]
    assert flow_events[0].flow_ids == [123]
    assert flow_events[1].terminating_flow_ids == [123]
    counters = [
        packet.track_event.counter_value
        for packet in parsed.packet
        if packet.HasField("track_event")
        and packet.track_event.type == perfetto_pb2.TrackEvent.TYPE_COUNTER
    ]
    assert counters == [99]


def test_crc_corruption_is_rejected(tmp_path: Path, schema: CompactSchema) -> None:
    image = bytearray(_rbct_image(schema))
    image[160 + 48 + 3] ^= 0x80
    path = tmp_path / "corrupt.rbct"
    path.write_bytes(image)
    with pytest.raises(CompactTraceError, match="CRC mismatch"):
        read_compact_trace(path, schema)
