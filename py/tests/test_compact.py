"""Format and reconstruction tests for compact traces."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

import pytest
import retrobus_perfetto.compact as compact_module

from retrobus_perfetto import (
    CompactSchema,
    CompactSchemaError,
    CompactTraceError,
    compact_trace_to_builder,
    convert_compact_trace,
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
                "constant_arguments": [{"name": "abi", "type": "uint", "value": 5}],
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


def _frame(record: bytes) -> bytes:
    assert 0 < len(record) <= 0xFF
    return bytes([len(record)]) + record


def _refresh_header_checksums(image: bytearray) -> None:
    struct.pack_into("<I", image, 160 + 44, 0)
    struct.pack_into("<I", image, 160 + 44, zlib.crc32(image[160:208]) & 0xFFFF_FFFF)
    struct.pack_into("<I", image, 152, 0)
    struct.pack_into("<I", image, 152, zlib.crc32(image[:160]) & 0xFFFF_FFFF)


def _rbct_image(schema: CompactSchema, *, version: int = 2) -> bytes:
    legacy_records = [
        bytes([0xFD])
        + _uleb(7)
        + _uleb(100)
        + _uleb(102)
        + _uleb(1_000_000)
        + _uleb(300),
        bytes([1]) + _uleb(49) + _uleb(40) + _uleb(42),
        bytes([2]) + _uleb(10) + _uleb(_zigzag(-7)),
        bytes([0xFE]) + _uleb(1) + bytes([3]) + _uleb(10) + _uleb(99),
        bytes([0xFE]) + _uleb(0) + bytes([4]) + _uleb(10) + _uleb(123),
        bytes([5]) + _uleb(10) + _uleb(123),
        bytes([6]) + _uleb(10) + _uleb(8) + _uleb(1024),
        bytes([7]) + _uleb(20) + _uleb(8) + _uleb(_zigzag(0)),
        bytes([0xFF])
        + _uleb(300)
        + _uleb(10)
        + struct.pack("<Q", 0xDEAD_BEEF_1234_5678),
    ]
    v3_records = [
        bytes([0xFD])
        + _uleb(7)
        + _uleb(100)
        + _uleb(102)
        + _uleb(1_000_000)
        + _uleb(300),
        bytes([1]) + _uleb(49) + _uleb(40) + _uleb(42),
        bytes([2]) + _uleb(10) + _uleb(_zigzag(-7)),
        bytes([0xFE, 1, 3]) + _uleb(10) + _uleb(99),
        bytes([0xFE, 0, 4]) + _uleb(10) + _uleb(123),
        bytes([5]) + _uleb(10) + _uleb(123),
        bytes([6]) + _uleb(10) + _uleb(8) + _uleb(1024),
        bytes([7]) + _uleb(20) + _uleb(8) + _uleb(_zigzag(0)),
        bytes([8]) + _uleb(10) + struct.pack("<Q", 0xDEAD_BEEF_1234_5678),
    ]
    if version == 3:
        payload = bytearray(b"".join(v3_records))
    elif version == 2:
        payload = bytearray(b"".join(_frame(record) for record in legacy_records))
    else:
        legacy_records[1] = bytes([1]) + _uleb(50) + _uleb(40) + _uleb(42)
        payload = bytearray(b"".join(legacy_records))

    chunk = bytearray(4096)
    chunk[:4] = b"RBCK"
    struct.pack_into(
        "<QQIIHHIHHI",
        chunk,
        4,
        0,
        100,
        7,
        0,
        len(payload),
        8,
        9,
        1,
        0,
        zlib.crc32(payload) & 0xFFFF_FFFF,
    )
    chunk[48 : 48 + len(payload)] = payload
    if version >= 2:
        struct.pack_into("<I", chunk, 44, 0)
        struct.pack_into("<I", chunk, 44, zlib.crc32(chunk[:48]) & 0xFFFF_FFFF)

    header = bytearray(160)
    header[:8] = {1: b"RBCTRC1\0", 2: b"RBCTRC2\0", 3: b"RBCTRC3\0"}[version]
    flags = 5 if version >= 2 else 1
    struct.pack_into(
        "<HHHHIQQHHII",
        header,
        8,
        version,
        160,
        48,
        0,
        4096,
        1_000_000,
        1,
        32,
        flags,
        schema.producer_id,
        schema.version,
    )
    header[48:80] = schema.sha256
    header[80:96] = bytes(range(16))
    struct.pack_into("<QQQQQQII", header, 96, 8, 0, 0, 9, 0, 4256, 7, 0)
    struct.pack_into("<I", header, 152, 0)
    struct.pack_into("<I", header, 152, zlib.crc32(header) & 0xFFFF_FFFF)
    return bytes(header + chunk)


def _v3_payload_image(
    schema: CompactSchema,
    payload: bytes,
    *,
    records: int,
    events: int,
    syncs: int = 0,
    base_timestamp: int = 0,
    generation: int = 0,
    default_track: int = 0,
    finalized: bool = True,
    advertised_used: int | None = None,
) -> bytes:
    assert len(payload) <= 4096 - 48
    used = len(payload) if advertised_used is None else advertised_used
    chunk = bytearray(4096)
    chunk[:4] = b"RBCK"
    struct.pack_into(
        "<QQIIHHIHHI",
        chunk,
        4,
        0,
        base_timestamp,
        generation,
        default_track,
        used,
        records,
        events,
        syncs,
        0,
        zlib.crc32(payload) & 0xFFFF_FFFF if finalized else 0,
    )
    chunk[48 : 48 + len(payload)] = payload
    if finalized:
        struct.pack_into("<I", chunk, 44, zlib.crc32(chunk[:48]) & 0xFFFF_FFFF)

    header = bytearray(160)
    header[:8] = b"RBCTRC3\0"
    struct.pack_into(
        "<HHHHIQQHHII",
        header,
        8,
        3,
        160,
        48,
        0,
        4096,
        1_000_000,
        1,
        32,
        5 if finalized else 0,
        schema.producer_id,
        schema.version,
    )
    header[48:80] = schema.sha256
    struct.pack_into(
        "<QQQQQQII",
        header,
        96,
        records,
        0,
        0,
        events,
        0,
        4256,
        generation,
        default_track,
    )
    if finalized:
        struct.pack_into("<I", header, 152, zlib.crc32(header) & 0xFFFF_FFFF)
    return bytes(header + chunk)


def _append_lsb_bits(output: bytearray, bit_offset: int, value: int, width: int) -> int:
    for index in range(width):
        if value & (1 << index):
            output[(bit_offset + index) >> 3] |= 1 << ((bit_offset + index) & 7)
    return bit_offset + width


def _v4_literal_payload() -> tuple[bytes, int]:
    """Encode event 1 as a literal-only v4 slice at delta 0."""
    payload = bytearray(5)
    bit_offset = 0
    bit_offset = _append_lsb_bits(payload, bit_offset, 0, 1)  # escape
    bit_offset = _append_lsb_bits(payload, bit_offset, 0, 2)  # same-track event
    for value in (1, 0, 1, 42):  # opcode, delta, duration, argument
        bit_offset = _append_lsb_bits(payload, bit_offset, value, 8)
    return bytes(payload), bit_offset


def _v4_live_image(
    schema: CompactSchema,
    chunk_specs: list[tuple[int, int, bytes, int]],
) -> bytes:
    """Build an unfinalized literal-only v4 image for recovery tests."""
    chunks = bytearray()
    for sequence, base_timestamp, payload, committed_bits in chunk_specs:
        chunk = bytearray(compact_module.CHUNK_BYTES)
        chunk[:4] = b"RBCK"
        struct.pack_into(
            "<QQIIHHIHHI",
            chunk,
            4,
            sequence,
            base_timestamp,
            0,
            0,
            committed_bits,
            1,
            2,
            0,
            0,
            0,
        )
        chunk[48 : 48 + len(payload)] = payload
        chunks.extend(chunk)

    header = bytearray(compact_module.FILE_HEADER_BYTES)
    header[:8] = b"RBCTRC4\0"
    struct.pack_into(
        "<HHHHIQQHHII",
        header,
        8,
        4,
        compact_module.FILE_HEADER_BYTES,
        compact_module.CHUNK_HEADER_BYTES,
        0,
        compact_module.CHUNK_BYTES,
        1_000_000,
        1,
        32,
        0,
        schema.producer_id,
        schema.version,
    )
    header[48:80] = schema.sha256
    struct.pack_into(
        "<QQQQQQII",
        header,
        96,
        len(chunk_specs),
        0,
        0,
        2 * len(chunk_specs),
        0,
        len(header) + len(chunks),
        0,
        0,
    )
    return bytes(header + chunks)


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
    assert "DEMO_TRACE_OPCODE_WORK UINT8_C(1)" in header
    assert "DEMO_TRACE_OPCODE_ADDRESS UINT8_C(8)" in header
    assert "DEMO_TRACE_EVENT_REQUEST_4 UINT32_C(4)" in header
    assert "DEMO_TRACE_EVENT_REQUEST_5 UINT32_C(5)" in header
    assert "DEMO_TRACE_BEGIN_WORK(" in header
    assert "DEMO_TRACE_EMIT_FAULT(" in header
    assert ", ".join(f"0x{byte:02x}" for byte in schema.sha256) in header


def test_generated_symbols_remain_unique_after_normalization() -> None:
    mapping = _schema_mapping()
    events = mapping["events"]
    assert isinstance(events, list)
    events.append(
        {
            "id": 8,
            "name": "request_4",
            "category": "io",
            "kind": "instant",
            "arguments": [],
        }
    )
    header = render_c_schema_header(CompactSchema.from_mapping(mapping), "demo")

    assert header.count("#define DEMO_TRACE_EVENT_REQUEST_4 ") == 1
    assert "#define DEMO_TRACE_EVENT_REQUEST_4_8 UINT32_C(8)" in header


def test_schema_file_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"format":"retrobus-compact-schema-v1","format":"duplicate"}',
        encoding="utf-8",
    )

    with pytest.raises(CompactSchemaError, match="duplicate JSON key 'format'"):
        CompactSchema.load(path)

    path.write_text('{"format":NaN}', encoding="utf-8")
    with pytest.raises(CompactSchemaError, match="non-finite JSON number NaN"):
        CompactSchema.load(path)


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

    mapping = _schema_mapping()
    events = mapping["events"]
    assert isinstance(events, list)
    flow = events[3]
    assert isinstance(flow, dict)
    flow["arguments"] = []
    flow["id_argument"] = "id"
    with pytest.raises(CompactSchemaError, match="must name a stored argument"):
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
    categories = {
        event.name: list(event.categories)
        for packet in parsed.packet
        if packet.HasField("track_event")
        for event in (packet.track_event,)
        if event.name in {"work", "fault", "request", "transfer", "address"}
    }
    assert categories["work"] == ["runtime"]
    assert categories["fault"] == ["runtime"]
    assert categories["request"] == ["io"]
    assert categories["transfer"] == ["io"]
    assert categories["address"] == ["runtime"]
    typed_annotations = {
        event.name: [
            annotation.WhichOneof("value") for annotation in event.debug_annotations
        ]
        for packet in parsed.packet
        if packet.HasField("track_event")
        for event in (packet.track_event,)
        if event.name in {"work", "address"}
    }
    assert typed_annotations["work"] == ["uint_value", "uint_value", "uint_value"]
    assert typed_annotations["address"] == ["uint_value"]
    flow_events = [
        packet.track_event
        for packet in parsed.packet
        if packet.HasField("track_event")
        and (packet.track_event.flow_ids or packet.track_event.terminating_flow_ids)
    ]
    assert flow_events[0].flow_ids == [123]
    assert flow_events[1].terminating_flow_ids == [123]
    counters = [
        packet.track_event
        for packet in parsed.packet
        if packet.HasField("track_event")
        and packet.track_event.type == perfetto_pb2.TrackEvent.TYPE_COUNTER
    ]
    assert [counter.counter_value for counter in counters] == [99]
    assert counters[0].categories == ["storage"]
    assert counters[0].debug_annotations[0].name == "value"
    assert counters[0].debug_annotations[0].uint_value == 99


def test_v1_v2_v3_fixtures_reconstruct_identical_semantics(
    tmp_path: Path, schema: CompactSchema
) -> None:
    traces = []
    rows = []
    for version in (1, 2, 3):
        path = tmp_path / f"capture-v{version}.rbct"
        path.write_bytes(_rbct_image(schema, version=version))
        trace = read_compact_trace(path, schema)
        traces.append(trace)
        rows.append(_event_rows(compact_trace_to_builder(trace)))

    assert [trace.header.format_version for trace in traces] == [1, 2, 3]
    assert [
        (
            record.event.id,
            record.generation,
            record.track_id,
            record.raw_timestamp,
            record.duration_ticks,
            record.arguments,
        )
        for record in traces[0].records
    ] == [
        (
            record.event.id,
            record.generation,
            record.track_id,
            record.raw_timestamp,
            record.duration_ticks,
            record.arguments,
        )
        for record in traces[2].records
    ]
    assert rows[0] == rows[1] == rows[2]


def test_v3_schema_opcode_map_is_dense_and_assigns_inline_pairs() -> None:
    mapping = _schema_mapping()
    events = mapping["events"]
    assert isinstance(events, list)
    events.append(
        {
            "id": 229,
            "name": "screen mutation",
            "category": "display",
            "kind": "instant",
            "arguments": [],
        }
    )
    schema = CompactSchema.from_mapping(mapping)

    assert schema.v3_event_opcodes[1] == 1
    assert schema.v3_event_opcodes[229] == 8
    assert schema.v3_event_opcodes[300] == 9
    assert schema.v3_inline_opcodes[229] == (10, 11)


def test_crc_corruption_is_rejected(tmp_path: Path, schema: CompactSchema) -> None:
    image = bytearray(_rbct_image(schema))
    image[160 + 48 + 3] ^= 0x80
    path = tmp_path / "corrupt.rbct"
    path.write_bytes(image)
    with pytest.raises(CompactTraceError, match="CRC mismatch"):
        read_compact_trace(path, schema)


def test_chunk_header_corruption_is_rejected(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema))
    image[160 + 12] ^= 0x01
    path = tmp_path / "corrupt-header.rbct"
    path.write_bytes(image)
    for recover in (False, True):
        with pytest.raises(CompactTraceError, match="header CRC mismatch"):
            read_compact_trace(path, schema, allow_unfinalized=recover)


def test_finalized_v2_requires_chunk_header_crcs(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema))
    struct.pack_into("<H", image, 38, 1)
    struct.pack_into("<I", image, 160 + 44, 0)
    struct.pack_into("<I", image, 152, 0)
    struct.pack_into("<I", image, 152, zlib.crc32(image[:160]) & 0xFFFF_FFFF)
    path = tmp_path / "v2-without-header-crcs.rbct"
    path.write_bytes(image)

    for recover in (False, True):
        with pytest.raises(CompactTraceError, match="lacks chunk-header CRCs"):
            read_compact_trace(path, schema, allow_unfinalized=recover)


def test_version_1_rejects_version_2_chunk_header_crc_flag(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema, version=1))
    struct.pack_into("<H", image, 38, 5)
    struct.pack_into("<I", image, 152, 0)
    struct.pack_into("<I", image, 152, zlib.crc32(image[:160]) & 0xFFFF_FFFF)
    path = tmp_path / "v1-with-v2-flags.rbct"
    path.write_bytes(image)

    with pytest.raises(CompactTraceError, match="version 2 chunk-header CRCs"):
        read_compact_trace(path, schema)


def test_interrupted_finalize_skips_a_torn_chunk_header(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema))
    struct.pack_into("<I", image, 152, 0)
    image[160 + 44] ^= 1
    path = tmp_path / "torn-finalize.rbct"
    path.write_bytes(image)

    trace = read_compact_trace(path, schema, allow_unfinalized=True)

    assert not trace.header.finalized
    assert trace.header.retained_records == 0


def test_unfinalized_capture_ignores_stale_counts(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema))
    struct.pack_into("<H", image, 38, 0)
    struct.pack_into("<I", image, 152, 0)
    struct.pack_into("<H", image, 160 + 30, 7)
    struct.pack_into("<I", image, 160 + 44, 0)
    used = struct.unpack_from("<H", image, 160 + 28)[0]
    struct.pack_into("<H", image, 160 + 28, used + 1)
    path = tmp_path / "unfinalized.rbct"
    path.write_bytes(image)

    trace = read_compact_trace(path, schema, allow_unfinalized=True)

    assert not trace.header.finalized
    assert trace.header.total_records == 8
    assert trace.header.total_events == 9


def test_legacy_payload_only_crc_capture_remains_readable(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema, version=1))
    path = tmp_path / "legacy.rbct"
    path.write_bytes(image)

    assert read_compact_trace(path, schema).header.retained_records == 8


def test_unfinalized_read_recovers_an_interrupted_finalize(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema))
    struct.pack_into("<I", image, 152, 0)
    path = tmp_path / "interrupted-finalize.rbct"
    path.write_bytes(image)

    with pytest.raises(CompactTraceError, match="file-header CRC mismatch"):
        read_compact_trace(path, schema)
    trace = read_compact_trace(path, schema, allow_unfinalized=True)

    assert not trace.header.finalized
    assert trace.header.retained_records == 8


def test_v4_recovery_skips_single_chunk_with_out_of_range_bit_cursor(
    tmp_path: Path, schema: CompactSchema
) -> None:
    payload, _ = _v4_literal_payload()
    image = _v4_live_image(schema, [(0, 100, payload, 0xFFFF)])
    path = tmp_path / "v4-oversized-single-chunk.rbct"
    path.write_bytes(image)

    recovered = read_compact_trace(path, schema, allow_unfinalized=True)
    assert recovered.records == ()
    assert recovered.clock_syncs == ()


def test_v4_recovery_never_crosses_a_malformed_chunk_boundary(
    tmp_path: Path, schema: CompactSchema
) -> None:
    payload, committed_bits = _v4_literal_payload()
    image = _v4_live_image(
        schema,
        [
            (0, 100, payload, committed_bits),
            (1, 200, payload, 0xFFFF),
            (2, 300, payload, committed_bits),
        ],
    )
    path = tmp_path / "v4-oversized-middle-chunk.rbct"
    path.write_bytes(image)

    recovered = read_compact_trace(path, schema, allow_unfinalized=True)

    # Dropping sequence 1 creates a recovery gap, so sequence 2 cannot be
    # interpreted as a continuation. Most importantly, sequence 1's cursor
    # never turns the following physical chunk into payload bytes.
    assert [record.event.id for record in recovered.records] == [1]
    assert recovered.records[0].raw_timestamp == 100


def test_varints_are_canonical_unsigned_64_bit() -> None:
    for value in (0, 1, 127, 128, (1 << 63) - 1, 1 << 63, (1 << 64) - 1):
        encoded = _uleb(value)
        assert compact_module._read_varint(encoded, 0, len(encoded)) == (
            value,
            len(encoded),
        )
    with pytest.raises(CompactTraceError, match="exceeds unsigned 64-bit"):
        compact_module._read_varint(bytes([0x80] * 9 + [0x02]), 0, 10)
    with pytest.raises(CompactTraceError, match="not canonically encoded"):
        compact_module._read_varint(bytes([0x80, 0x00]), 0, 2)


def test_counter_extension_rejects_ambiguous_gaps_and_generation_reuse(
    tmp_path: Path, schema: CompactSchema
) -> None:
    path = tmp_path / "capture.rbct"
    path.write_bytes(_rbct_image(schema))
    header = read_compact_trace(path, schema).header
    event = schema.events[2]
    records = (
        compact_module.CompactRecord(event, 7, 0, 100, None, (-1,), 0),
        compact_module.CompactRecord(event, 7, 0, 99, None, (-1,), 1),
    )
    with pytest.raises(CompactTraceError, match="ambiguous counter gap"):
        compact_module._extend_items(header, records)

    reused = (
        compact_module.CompactRecord(event, 7, 0, 100, None, (-1,), 0),
        compact_module.CompactClockSync(8, 100, 100, 1_000, 0, 1),
        compact_module.CompactRecord(event, 7, 0, 101, None, (-1,), 2),
    )
    with pytest.raises(CompactTraceError, match="reappears after a transition"):
        compact_module._extend_items(header, reused)

    jumped = (
        compact_module.CompactRecord(event, 7, 0, 100, None, (-1,), 0),
        compact_module.CompactClockSync(9, 100, 100, 1_000, 0, 1),
    )
    with pytest.raises(CompactTraceError, match="generation jumps"):
        compact_module._extend_items(header, jumped)

    unsynchronized = (
        compact_module.CompactRecord(event, 7, 0, 100, None, (-1,), 0),
        compact_module.CompactRecord(event, 8, 0, 101, None, (-1,), 1),
    )
    with pytest.raises(CompactTraceError, match="synchronization record"):
        compact_module._extend_items(header, unsynchronized)

    late_first_sync = (
        compact_module.CompactRecord(event, 7, 0, 100, None, (-1,), 0),
        compact_module.CompactClockSync(7, 101, 101, 1_000, 0, 1),
    )
    with pytest.raises(CompactTraceError, match="first synchronizes after"):
        compact_module._extend_items(header, late_first_sync)

    wrapped_header = replace(
        header, flags=header.flags | compact_module.FLAG_RING_WRAPPED
    )
    wrapped_records, wrapped_syncs = compact_module._extend_items(
        wrapped_header, late_first_sync
    )
    assert len(wrapped_records) == 1
    assert len(wrapped_syncs) == 1


def test_v2_rejects_noncanonical_track_controls(schema: CompactSchema) -> None:
    chunk = compact_module._Chunk(0, 0, 100, 7, 0, 0, 0, 0, 0, 0)
    record = bytes([0xFE, 0, 2, 0, 0])

    with pytest.raises(CompactTraceError, match="non-canonical track selection"):
        compact_module._decode_one_record(
            record,
            0,
            len(record),
            chunk=chunk,
            schema=schema,
            clock_width_bits=32,
            timestamp=100,
            track_id=0,
            order=0,
            strict=True,
        )


def test_timestamp_interpolates_between_clock_anchors(
    tmp_path: Path, schema: CompactSchema
) -> None:
    path = tmp_path / "capture.rbct"
    path.write_bytes(_rbct_image(schema))
    original = read_compact_trace(path, schema)
    anchors = (
        compact_module.CompactClockSync(7, 100, 100, 1_000_000, 0, 0, 100),
        compact_module.CompactClockSync(7, 200, 200, 2_000_000, 0, 1, 200),
    )
    trace = compact_module.CompactTrace(original.header, schema, (), anchors)

    assert trace.timestamp_ns(7, 190) == 1_900_000

    invalid = anchors + (
        compact_module.CompactClockSync(7, 200, 200, 2_100_000, 0, 2, 200),
    )
    with pytest.raises(CompactTraceError, match="non-advancing anchors"):
        compact_module.CompactTrace(original.header, schema, (), invalid)


def test_v2_unfinalized_recovery_does_not_invent_event_zero(
    tmp_path: Path,
) -> None:
    mapping = _schema_mapping()
    events = mapping["events"]
    assert isinstance(events, list)
    events.append(
        {
            "id": 0,
            "name": "zero",
            "category": "audit",
            "kind": "instant",
            "arguments": [],
        }
    )
    schema = CompactSchema.from_mapping(mapping)
    image = bytearray(_rbct_image(schema))
    struct.pack_into("<H", image, 38, 0)
    struct.pack_into("<I", image, 152, 0)
    struct.pack_into("<I", image, 160 + 44, 0)
    used = struct.unpack_from("<H", image, 160 + 28)[0]
    struct.pack_into("<H", image, 160 + 28, used + 64)
    path = tmp_path / "torn-cursor.rbct"
    path.write_bytes(image)

    trace = read_compact_trace(path, schema, allow_unfinalized=True)

    assert len(trace.records) == 8
    assert all(record.event.id != 0 for record in trace.records)


def test_v2_unfinalized_recovery_stops_at_unpublished_marker(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema))
    struct.pack_into("<H", image, 38, 0)
    struct.pack_into("<I", image, 152, 0)
    struct.pack_into("<I", image, 160 + 44, 0)
    image[160 + 48] = 0
    path = tmp_path / "unpublished-record.rbct"
    path.write_bytes(image)

    trace = read_compact_trace(path, schema, allow_unfinalized=True)

    assert trace.records == ()
    assert trace.clock_syncs == ()


def test_v2_reserved_frame_marker_is_rejected(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema))
    image[160 + 48] = 0xFF
    used = struct.unpack_from("<H", image, 160 + 28)[0]
    payload = image[160 + 48 : 160 + 48 + used]
    struct.pack_into("<I", image, 160 + 40, zlib.crc32(payload) & 0xFFFF_FFFF)
    _refresh_header_checksums(image)
    path = tmp_path / "reserved-frame-marker.rbct"
    path.write_bytes(image)

    for recover in (False, True):
        with pytest.raises(CompactTraceError, match="invalid record frame"):
            read_compact_trace(path, schema, allow_unfinalized=recover)


@pytest.mark.parametrize(
    ("committed_opcode", "body"),
    [
        (2, bytes([2, 1, 42])),
        (0xFE, bytes([1, 4, 2, 99])),
    ],
)
def test_v3_recovery_is_exact_at_every_record_body_store(
    tmp_path: Path, committed_opcode: int, body: bytes
) -> None:
    mapping = _schema_mapping()
    events = mapping["events"]
    assert isinstance(events, list)
    events.append(
        {
            "id": 0,
            "name": "zero",
            "category": "audit",
            "kind": "instant",
            "arguments": [],
        }
    )
    schema = CompactSchema.from_mapping(mapping)
    inline_zero = schema.v3_inline_opcodes[0][0]

    for stored_body_bytes in range(len(body) + 1):
        payload = bytes([inline_zero, 0]) + body[:stored_body_bytes]
        path = tmp_path / f"interrupted-{committed_opcode}-{stored_body_bytes}.rbct"
        path.write_bytes(
            _v3_payload_image(
                schema,
                payload,
                records=1,
                events=1,
                finalized=False,
                advertised_used=1,
            )
        )
        trace = read_compact_trace(path, schema, allow_unfinalized=True)
        assert [record.event.id for record in trace.records] == [0]

    committed = bytes([inline_zero, committed_opcode]) + body
    path = tmp_path / f"committed-{committed_opcode}.rbct"
    path.write_bytes(
        _v3_payload_image(
            schema,
            committed,
            records=1,
            events=1,
            finalized=False,
            advertised_used=1,
        )
    )
    trace = read_compact_trace(path, schema, allow_unfinalized=True)
    assert len(trace.records) == 2


def test_v3_recovery_stops_globally_at_an_invalid_committed_opcode(
    tmp_path: Path,
) -> None:
    mapping = _schema_mapping()
    events = mapping["events"]
    assert isinstance(events, list)
    events.append(
        {
            "id": 0,
            "name": "zero",
            "category": "audit",
            "kind": "instant",
            "arguments": [],
        }
    )
    schema = CompactSchema.from_mapping(mapping)
    inline_zero = schema.v3_inline_opcodes[0][0]
    payload = bytes([inline_zero, 0xF0, inline_zero])
    path = tmp_path / "invalid-opcode.rbct"
    path.write_bytes(
        _v3_payload_image(
            schema, payload, records=3, events=3, finalized=False
        )
    )

    trace = read_compact_trace(path, schema, allow_unfinalized=True)

    assert [record.event.id for record in trace.records] == [0]


def test_v3_full_payload_needs_no_trailing_sentinel(tmp_path: Path) -> None:
    mapping = _schema_mapping()
    events = mapping["events"]
    assert isinstance(events, list)
    events.append(
        {
            "id": 0,
            "name": "minimal",
            "category": "density",
            "kind": "instant",
            "arguments": [],
        }
    )
    schema = CompactSchema.from_mapping(mapping)
    delta_zero = schema.v3_inline_opcodes[0][0]
    path = tmp_path / "full-v3-payload.rbct"
    path.write_bytes(
        _v3_payload_image(
            schema,
            bytes([delta_zero]) * (4096 - 48),
            records=4096 - 48,
            events=4096 - 48,
        )
    )

    trace = read_compact_trace(path, schema)

    assert len(trace.records) == 4048
    assert all(record.event.id == 0 for record in trace.records)


def test_v3_live_recovery_crosses_slack_in_an_older_chunk(
    tmp_path: Path,
) -> None:
    mapping = _schema_mapping()
    events = mapping["events"]
    assert isinstance(events, list)
    events.append(
        {
            "id": 0,
            "name": "minimal",
            "category": "density",
            "kind": "instant",
            "arguments": [],
        }
    )
    schema = CompactSchema.from_mapping(mapping)
    delta_zero = schema.v3_inline_opcodes[0][0]
    image = bytearray(
        _v3_payload_image(
            schema,
            bytes([delta_zero]),
            records=2,
            events=2,
            finalized=False,
        )
    )
    second = bytearray(4096)
    second[:4] = b"RBCK"
    struct.pack_into(
        "<QQIIHHIHHI",
        second,
        4,
        1,
        0,
        0,
        0,
        1,
        1,
        1,
        0,
        0,
        0,
    )
    second[48] = delta_zero
    image.extend(second)
    struct.pack_into("<Q", image, 136, len(image))
    path = tmp_path / "v3-live-two-chunks.rbct"
    path.write_bytes(image)

    trace = read_compact_trace(path, schema, allow_unfinalized=True)

    assert [record.event.id for record in trace.records] == [0, 0]


@pytest.mark.parametrize("advertised_used", [0, 1, 5, 0xFFFF])
def test_v3_recovery_ignores_every_torn_metadata_cursor_shape(
    tmp_path: Path, schema: CompactSchema, advertised_used: int
) -> None:
    event_opcode = schema.v3_event_opcodes[2]
    payload = (
        bytes([event_opcode, 0])
        + _uleb(_zigzag(1))
        + bytes([event_opcode, 1])
        + _uleb(_zigzag(2))
    )
    image = bytearray(
        _v3_payload_image(
            schema,
            payload,
            records=0,
            events=0,
            finalized=False,
            advertised_used=advertised_used,
        )
    )
    struct.pack_into("<H", image, 160 + 30, 0xFFFF)
    struct.pack_into("<I", image, 160 + 32, 0xFFFF_FFFF)
    struct.pack_into("<H", image, 160 + 36, 0xFFFF)
    path = tmp_path / f"torn-v3-metadata-{advertised_used}.rbct"
    path.write_bytes(image)

    trace = read_compact_trace(path, schema, allow_unfinalized=True)

    assert [record.arguments for record in trace.records] == [(1,), (2,)]
    assert trace.header.retained_records == 2
    assert trace.header.retained_events == 2


def test_v3_interrupted_finalization_retains_committed_prefix(
    tmp_path: Path, schema: CompactSchema
) -> None:
    finalized = bytearray(_rbct_image(schema, version=3))
    final_payload_crc = bytes(finalized[160 + 40 : 160 + 44])
    final_chunk_crc = bytes(finalized[160 + 44 : 160 + 48])
    final_header_crc = bytes(finalized[152:156])
    live = bytearray(finalized)
    struct.pack_into("<H", live, 38, 0)
    live[160 + 40 : 160 + 48] = b"\0" * 8
    live[152:156] = b"\0" * 4

    snapshots = []
    for written_crc_bytes in range(5):
        image = bytearray(live)
        image[160 + 40 : 160 + 40 + written_crc_bytes] = final_payload_crc[
            :written_crc_bytes
        ]
        snapshots.append((f"payload-crc-{written_crc_bytes}", image))
    for written_crc_bytes in range(5):
        image = bytearray(live)
        image[160 + 40 : 160 + 44] = final_payload_crc
        image[160 + 44 : 160 + 44 + written_crc_bytes] = final_chunk_crc[
            :written_crc_bytes
        ]
        snapshots.append((f"chunk-crc-{written_crc_bytes}", image))
    advertised = bytearray(finalized)
    struct.pack_into("<H", advertised, 38, 4)
    advertised[152:156] = b"\0" * 4
    for written_crc_bytes in range(5):
        image = bytearray(advertised)
        image[152 : 152 + written_crc_bytes] = final_header_crc[
            :written_crc_bytes
        ]
        snapshots.append((f"header-crc-{written_crc_bytes}", image))
    for written_crc_bytes in range(4):
        image = bytearray(advertised)
        image[152 : 152 + written_crc_bytes] = final_header_crc[
            :written_crc_bytes
        ]
        struct.pack_into("<H", image, 38, 5)
        snapshots.append((f"final-bit-{written_crc_bytes}", image))

    for name, image in snapshots:
        path = tmp_path / f"interrupted-finalize-{name}.rbct"
        path.write_bytes(image)
        trace = read_compact_trace(path, schema, allow_unfinalized=True)
        assert len(trace.records) == 8
        assert len(trace.clock_syncs) == 1

    complete = tmp_path / "complete-finalization.rbct"
    complete.write_bytes(finalized)
    assert read_compact_trace(complete, schema).header.finalized


def test_v3_finalized_corruption_is_detected_and_live_corruption_is_bounded(
    tmp_path: Path, schema: CompactSchema
) -> None:
    finalized = bytearray(_rbct_image(schema, version=3))
    finalized[160 + 48 + 3] ^= 0x80
    finalized_path = tmp_path / "v3-finalized-corrupt.rbct"
    finalized_path.write_bytes(finalized)
    with pytest.raises(CompactTraceError, match="CRC mismatch"):
        read_compact_trace(finalized_path, schema)

    live = bytearray(_rbct_image(schema, version=3))
    struct.pack_into("<H", live, 38, 0)
    struct.pack_into("<I", live, 152, 0)
    struct.pack_into("<I", live, 160 + 44, 0)
    live[160 + 48] = 0xF0
    live_path = tmp_path / "v3-live-corrupt.rbct"
    live_path.write_bytes(live)
    trace = read_compact_trace(live_path, schema, allow_unfinalized=True)
    assert trace.records == ()
    assert trace.clock_syncs == ()


def test_v2_explicit_small_delta_is_noncanonical(schema: CompactSchema) -> None:
    chunk = compact_module._Chunk(0, 0, 100, 7, 0, 0, 0, 0, 0, 0)
    record = bytes([2, 1]) + _uleb(_zigzag(-7))

    with pytest.raises(CompactTraceError, match="explicit timestamp delta"):
        compact_module._decode_one_record(
            record,
            0,
            len(record),
            chunk=chunk,
            schema=schema,
            clock_width_bits=32,
            timestamp=100,
            track_id=0,
            order=0,
            strict=True,
        )


def test_recovery_option_never_weakens_finalized_validation(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema))
    used = struct.unpack_from("<H", image, 160 + 28)[0]
    malformed = _frame(bytes([0]))
    image[160 + 48 + used : 160 + 48 + used + len(malformed)] = malformed
    struct.pack_into("<H", image, 160 + 28, used + len(malformed))
    payload = image[160 + 48 : 160 + 48 + used + len(malformed)]
    struct.pack_into("<I", image, 160 + 40, zlib.crc32(payload) & 0xFFFF_FFFF)
    struct.pack_into("<I", image, 160 + 44, 0)
    struct.pack_into("<I", image, 160 + 44, zlib.crc32(image[160:208]) & 0xFFFF_FFFF)
    struct.pack_into("<I", image, 152, 0)
    struct.pack_into("<I", image, 152, zlib.crc32(image[:160]) & 0xFFFF_FFFF)
    path = tmp_path / "finalized-malformed.rbct"
    path.write_bytes(image)

    for recover in (False, True):
        with pytest.raises(CompactTraceError, match="unknown compact event ID 0"):
            read_compact_trace(path, schema, allow_unfinalized=recover)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda image: struct.pack_into("<Q", image, 104, 1), "overwrite counts"),
        (
            lambda image: (
                struct.pack_into("<Q", image, 104, 1),
                struct.pack_into("<Q", image, 128, 3),
            ),
            "overwrite counts",
        ),
        (lambda image: struct.pack_into("<H", image, 38, 7), "wrapped compact ring"),
        (lambda image: struct.pack_into("<Q", image, 160 + 4, 1), "chunk layout"),
        (lambda image: struct.pack_into("<H", image, 160 + 28, 0), "empty payload"),
    ],
)
def test_finalized_ring_invariants_are_enforced(
    tmp_path: Path,
    schema: CompactSchema,
    mutate,
    message: str,
) -> None:
    image = bytearray(_rbct_image(schema))
    mutate(image)
    _refresh_header_checksums(image)
    path = tmp_path / f"invalid-ring-{message.replace(' ', '-')}.rbct"
    path.write_bytes(image)

    with pytest.raises(CompactTraceError, match=message):
        read_compact_trace(path, schema, allow_unfinalized=True)


def test_finalized_unused_chunks_must_be_completely_zero(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema)) + bytearray(compact_module.CHUNK_BYTES)
    struct.pack_into("<Q", image, 136, len(image))
    _refresh_header_checksums(image)
    clean = tmp_path / "clean-unused-chunk.rbct"
    clean.write_bytes(image)
    assert read_compact_trace(clean, schema).header.retained_records == 8

    image[
        compact_module.FILE_HEADER_BYTES
        + compact_module.CHUNK_BYTES
        + compact_module.CHUNK_HEADER_BYTES
    ] = 0xA5
    dirty = tmp_path / "dirty-unused-chunk.rbct"
    dirty.write_bytes(image)
    with pytest.raises(CompactTraceError, match="unused physical chunk 1 is nonzero"):
        read_compact_trace(dirty, schema)


def test_finalized_used_chunk_payload_slack_must_be_zero(
    tmp_path: Path, schema: CompactSchema
) -> None:
    image = bytearray(_rbct_image(schema))
    used = struct.unpack_from(
        "<H", image, compact_module.LEGACY_FILE_HEADER_BYTES + 28
    )[0]
    image[
        compact_module.LEGACY_FILE_HEADER_BYTES
        + compact_module.CHUNK_HEADER_BYTES
        + used
    ] = 0xA5
    path = tmp_path / "dirty-payload-slack.rbct"
    path.write_bytes(image)

    with pytest.raises(CompactTraceError, match="nonzero payload slack"):
        read_compact_trace(path, schema)


def test_legacy_v1_generation_jumps_remain_readable(
    tmp_path: Path, schema: CompactSchema
) -> None:
    path = tmp_path / "legacy.rbct"
    path.write_bytes(_rbct_image(schema, version=1))
    header = read_compact_trace(path, schema).header
    event = schema.events[2]
    records = (
        compact_module.CompactRecord(event, 7, 0, 100, None, (-1,), 0),
        compact_module.CompactRecord(event, 9, 0, 100, None, (-1,), 1),
    )

    extended, _ = compact_module._extend_items(header, records)

    assert [record.generation for record in extended] == [7, 9]

    anchors = (
        compact_module.CompactClockSync(7, 100, 100, 1_000, 0, 0, 100),
        compact_module.CompactClockSync(7, 100, 100, 500, 0, 1, 100),
    )
    legacy_trace = compact_module.CompactTrace(header, schema, (), anchors)
    assert legacy_trace.timestamp_ns(7, 110) == 11_000


def test_unanchored_slice_origin_includes_its_start(schema: CompactSchema) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        1,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        1,
        0,
        0,
        2,
        0,
        4256,
        7,
        0,
    )
    record = compact_module.CompactRecord(schema.events[1], 7, 0, 100, 40, (1,), 0, 100)
    trace = compact_module.CompactTrace(header, schema, (record,), ())

    assert trace.timestamp_ns(7, 60) == 0
    assert compact_trace_to_builder(trace).serialize()


def test_schema_semantics_are_immutable_and_generator_handles_unicode(
    tmp_path: Path,
) -> None:
    mapping = _schema_mapping()
    schema = CompactSchema.from_mapping(mapping)
    with pytest.raises(TypeError):
        schema.events[1] = schema.events[2]  # type: ignore[index]

    events = mapping["events"]
    assert isinstance(events, list)
    event = events[0]
    assert isinstance(event, dict)
    event["name"] = "事件"
    first_schema = CompactSchema.from_mapping(mapping)
    header = render_c_schema_header(first_schema, "演示")
    assert "PRODUCER_42_TRACE_EVENT_ID_1" in header

    second_mapping = json.loads(json.dumps(mapping))
    second_mapping["producer"] = {"id": 43, "name": "δοκιμή"}
    second_schema = CompactSchema.from_mapping(second_mapping)
    version_mapping = json.loads(json.dumps(mapping))
    version_mapping["version"] = 2
    version_schema = CompactSchema.from_mapping(version_mapping)
    first_header = render_c_schema_header(first_schema)
    second_header = render_c_schema_header(second_schema)
    version_header = render_c_schema_header(version_schema)
    assert "TEST_TARGET_42_V1_COMPACT_TRACE_SCHEMA_H" in first_header
    assert "TEST_TARGET_42_V2_COMPACT_TRACE_SCHEMA_H" in version_header
    assert "PRODUCER_43_V1_COMPACT_TRACE_SCHEMA_H" in second_header

    compiler = shutil.which("cc")
    if compiler is not None:
        (tmp_path / "first.h").write_text(first_header, encoding="utf-8")
        (tmp_path / "second.h").write_text(second_header, encoding="utf-8")
        (tmp_path / "version.h").write_text(version_header, encoding="utf-8")
        source = tmp_path / "both.c"
        source.write_text(
            '#include "first.h"\n'
            '#include "second.h"\n'
            '#include "version.h"\n'
            "int main(void) {\n"
            "  return (TEST_TARGET_42_V1_TRACE_SCHEMA_VERSION == 1u &&\n"
            "          TEST_TARGET_42_V2_TRACE_SCHEMA_VERSION == 2u &&\n"
            "          PRODUCER_43_V1_TRACE_PRODUCER_ID == 43u) ? 0 : 1;\n"
            "}\n",
            encoding="utf-8",
        )
        repository = Path(__file__).resolve().parents[2]
        subprocess.run(
            [
                compiler,
                "-std=c99",
                "-Wall",
                "-Wextra",
                "-Werror",
                f"-I{repository / 'compact' / 'include'}",
                f"-I{tmp_path}",
                str(source),
                "-o",
                str(tmp_path / "both"),
            ],
            check=True,
        )

    mapping["typo"] = True
    with pytest.raises(CompactSchemaError, match="unsupported field 'typo'"):
        CompactSchema.from_mapping(mapping)


def test_async_ring_loss_is_rendered_as_a_truncated_instant(
    schema: CompactSchema,
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        3,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        2,
        1,
        0,
        1,
        0,
        4256,
        7,
        0,
    )
    record = compact_module.CompactRecord(
        schema.events[7], 7, 0, 100, None, (55, 0), 0, 100
    )
    trace = compact_module.CompactTrace(header, schema, (record,), ())
    parsed = perfetto_pb2.Trace()
    parsed.ParseFromString(compact_trace_to_builder(trace).serialize())
    events = [
        packet.track_event for packet in parsed.packet if packet.HasField("track_event")
    ]

    assert [event.type for event in events] == [perfetto_pb2.TrackEvent.TYPE_INSTANT]
    assert events[0].debug_annotations[-1].bool_value


def test_unmatched_async_begin_closes_at_the_last_retained_time(
    schema: CompactSchema,
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        1,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        1,
        0,
        0,
        1,
        0,
        4256,
        7,
        0,
    )
    record = compact_module.CompactRecord(
        schema.events[6], 7, 0, 0, None, (55, 1), 0, 0
    )
    anchor = compact_module.CompactClockSync(7, 100, 100, 0, 0, 1, 100, synthetic=True)
    trace = compact_module.CompactTrace(header, schema, (record,), (anchor,))
    parsed = perfetto_pb2.Trace()
    parsed.ParseFromString(
        compact_trace_to_builder(trace, normalize_start=True).serialize()
    )
    events = [
        (packet.timestamp, packet.track_event.type)
        for packet in parsed.packet
        if packet.HasField("track_event")
    ]

    assert events == [
        (0, perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN),
        (0, perfetto_pb2.TrackEvent.TYPE_SLICE_END),
    ]


def test_same_timestamp_async_reopen_closes_before_reopening(
    schema: CompactSchema,
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        1,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        2,
        0,
        0,
        2,
        0,
        4256,
        7,
        0,
    )
    records = (
        compact_module.CompactRecord(
            schema.events[6], 7, 0, 100, None, (55, 111), 0, 100
        ),
        compact_module.CompactRecord(
            schema.events[6], 7, 0, 100, None, (55, 222), 1, 100
        ),
    )
    trace = compact_module.CompactTrace(header, schema, records, ())

    rows = _event_rows(compact_trace_to_builder(trace, normalize_start=True))

    assert [row[1] for row in rows] == [
        perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN,
        perfetto_pb2.TrackEvent.TYPE_SLICE_END,
        perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN,
        perfetto_pb2.TrackEvent.TYPE_SLICE_END,
    ]
    assert [dict(row[3])["amount"] for row in rows] == [111, 111, 222, 222]


@pytest.mark.parametrize("duration_ticks", [0, 100])
def test_identical_nested_slices_preserve_stack_order(
    schema: CompactSchema, duration_ticks: int
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        1,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        2,
        0,
        0,
        4,
        0,
        4256,
        7,
        0,
    )
    records = (
        compact_module.CompactRecord(
            schema.events[1], 7, 0, 200, duration_ticks, (1,), 0, 200
        ),
        compact_module.CompactRecord(
            schema.events[1], 7, 0, 200, duration_ticks, (2,), 1, 200
        ),
    )
    trace = compact_module.CompactTrace(header, schema, records, ())

    rows = _event_rows(compact_trace_to_builder(trace))
    begins = [row for row in rows if row[1] == perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN]

    assert [row[1] for row in rows] == [
        perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN,
        perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN,
        perfetto_pb2.TrackEvent.TYPE_SLICE_END,
        perfetto_pb2.TrackEvent.TYPE_SLICE_END,
    ]
    assert [dict(row[3])["amount"] for row in begins] == [2, 1]


def test_slice_end_preserves_same_tick_record_order(
    schema: CompactSchema,
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        1,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        3,
        0,
        0,
        4,
        0,
        4256,
        7,
        0,
    )
    records = (
        compact_module.CompactRecord(schema.events[2], 7, 0, 200, None, (-1,), 0, 200),
        compact_module.CompactRecord(schema.events[1], 7, 0, 200, 100, (1,), 1, 200),
        compact_module.CompactRecord(schema.events[2], 7, 0, 200, None, (-2,), 2, 200),
    )
    trace = compact_module.CompactTrace(header, schema, records, ())

    all_rows = _event_rows(compact_trace_to_builder(trace))
    end_timestamp = max(row[0] for row in all_rows)
    rows = [row for row in all_rows if row[0] == end_timestamp]

    assert [row[1] for row in rows] == [
        perfetto_pb2.TrackEvent.TYPE_INSTANT,
        perfetto_pb2.TrackEvent.TYPE_SLICE_END,
        perfetto_pb2.TrackEvent.TYPE_INSTANT,
    ]
    assert [dict(row[3]).get("error") for row in rows] == [-1, None, -2]


def test_zero_duration_slice_stays_at_its_record_position(
    schema: CompactSchema,
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        1,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        3,
        0,
        0,
        4,
        0,
        4256,
        7,
        0,
    )
    records = (
        compact_module.CompactRecord(schema.events[2], 7, 0, 200, None, (-1,), 0, 200),
        compact_module.CompactRecord(schema.events[1], 7, 0, 200, 0, (1,), 1, 200),
        compact_module.CompactRecord(schema.events[2], 7, 0, 200, None, (-2,), 2, 200),
    )
    trace = compact_module.CompactTrace(header, schema, records, ())

    rows = _event_rows(compact_trace_to_builder(trace))

    assert [row[1] for row in rows] == [
        perfetto_pb2.TrackEvent.TYPE_INSTANT,
        perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN,
        perfetto_pb2.TrackEvent.TYPE_SLICE_END,
        perfetto_pb2.TrackEvent.TYPE_INSTANT,
    ]


def test_zero_duration_slices_do_not_nest_across_clock_generations(
    schema: CompactSchema,
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        1,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        2,
        0,
        0,
        4,
        0,
        4256,
        7,
        0,
    )
    records = (
        compact_module.CompactRecord(schema.events[1], 7, 0, 0, 0, (1,), 1, 0),
        compact_module.CompactRecord(schema.events[1], 8, 0, 0, 0, (2,), 3, 0),
    )
    syncs = (
        compact_module.CompactClockSync(7, 0, 0, 100, 0, 0, 0),
        compact_module.CompactClockSync(8, 0, 0, 100, 0, 2, 0),
    )
    trace = compact_module.CompactTrace(header, schema, records, syncs)

    rows = _event_rows(compact_trace_to_builder(trace))

    assert [row[1] for row in rows] == [
        perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN,
        perfetto_pb2.TrackEvent.TYPE_SLICE_END,
        perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN,
        perfetto_pb2.TrackEvent.TYPE_SLICE_END,
    ]
    assert [
        dict(row[3])["amount"]
        for row in rows
        if row[1] == perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN
    ] == [1, 2]


def test_sub_nanosecond_sequential_slices_do_not_become_nested(
    schema: CompactSchema,
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        1,
        1_000_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        2,
        0,
        0,
        4,
        0,
        4256,
        7,
        0,
    )
    records = (
        compact_module.CompactRecord(schema.events[1], 7, 0, 1, 1, (1,), 0, 1),
        compact_module.CompactRecord(schema.events[1], 7, 0, 2, 1, (2,), 1, 2),
    )
    trace = compact_module.CompactTrace(header, schema, records, ())

    rows = _event_rows(compact_trace_to_builder(trace))

    assert [row[1] for row in rows] == [
        perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN,
        perfetto_pb2.TrackEvent.TYPE_SLICE_END,
        perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN,
        perfetto_pb2.TrackEvent.TYPE_SLICE_END,
    ]
    assert [
        dict(row[3])["amount"]
        for row in rows
        if row[1] == perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN
    ] == [1, 2]


def test_wrapped_unanchored_prefix_is_placed_before_next_anchor(
    schema: CompactSchema,
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        7,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        2,
        1,
        0,
        2,
        1,
        8352,
        7,
        0,
    )
    records = (
        compact_module.CompactRecord(schema.events[2], 7, 0, 100, None, (-1,), 0, 100),
        compact_module.CompactRecord(schema.events[2], 7, 0, 200, None, (-1,), 1, 200),
    )
    sync = compact_module.CompactClockSync(8, 0, 0, 1_000, 0, 2, 0)

    trace = compact_module.CompactTrace(header, schema, records, (sync,))

    assert trace.uncorrelated_generations == (7,)
    assert [trace.timestamp_ns(7, tick) for tick in (100, 200)] == [900, 1_000]
    assert trace.timestamp_ns(8, 0) == 1_000


def test_v2_rejects_backwards_references_and_crossing_slices(
    schema: CompactSchema,
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        1,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        2,
        0,
        0,
        4,
        0,
        4256,
        7,
        0,
    )
    syncs = (
        compact_module.CompactClockSync(7, 10, 10, 1000, 0, 0, 10),
        compact_module.CompactClockSync(8, 10, 10, 999, 0, 1, 10),
    )
    with pytest.raises(CompactTraceError, match="reference time moves backwards"):
        compact_module.CompactTrace(header, schema, (), syncs)

    records = (
        compact_module.CompactRecord(schema.events[1], 7, 0, 10, 10, (1,), 0, 10),
        compact_module.CompactRecord(schema.events[1], 7, 0, 15, 10, (2,), 1, 15),
    )
    trace = compact_module.CompactTrace(header, schema, records, ())
    with pytest.raises(CompactTraceError, match="slice intervals cross"):
        compact_trace_to_builder(trace)

    mapped_backwards = (
        compact_module.CompactClockSync(7, 100, 100, 1_000, 0, 0, 100),
        compact_module.CompactClockSync(8, 100, 100, 1_050, 0, 2, 100),
    )
    prior_record = compact_module.CompactRecord(
        schema.events[2], 7, 0, 200, None, (-1,), 1, 200
    )
    with pytest.raises(CompactTraceError, match="mapped clock time moves backwards"):
        compact_module.CompactTrace(header, schema, (prior_record,), mapped_backwards)

    unanchored_record = compact_module.CompactRecord(
        schema.events[2], 8, 0, 100, None, (-1,), 1, 100
    )
    with pytest.raises(CompactTraceError, match="has no correlation anchor"):
        compact_module.CompactTrace(
            header, schema, (unanchored_record,), (mapped_backwards[0],)
        )


def test_unmatched_flow_start_is_marked_truncated(schema: CompactSchema) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        3,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        1,
        0,
        0,
        1,
        0,
        4256,
        7,
        0,
    )
    record = compact_module.CompactRecord(
        schema.events[4], 7, 0, 100, None, (55,), 0, 100
    )
    trace = compact_module.CompactTrace(header, schema, (record,), ())
    parsed = perfetto_pb2.Trace()
    parsed.ParseFromString(compact_trace_to_builder(trace).serialize())
    flow = next(
        packet.track_event
        for packet in parsed.packet
        if packet.HasField("track_event") and packet.track_event.flow_ids
    )

    assert flow.debug_annotations[-1].name == "retrobus.truncated_end"
    assert flow.debug_annotations[-1].bool_value


def test_orphan_flow_end_does_not_create_a_flow_source(
    schema: CompactSchema,
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        3,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        1,
        0,
        0,
        3,
        0,
        4256,
        7,
        0,
    )
    records = (
        compact_module.CompactRecord(schema.events[5], 7, 0, 100, None, (55,), 0, 100),
        compact_module.CompactRecord(schema.events[4], 7, 0, 200, None, (55,), 1, 200),
        compact_module.CompactRecord(schema.events[5], 7, 0, 300, None, (55,), 2, 300),
    )
    trace = compact_module.CompactTrace(header, schema, records, ())
    parsed = perfetto_pb2.Trace()
    parsed.ParseFromString(compact_trace_to_builder(trace).serialize())
    events = [
        packet.track_event for packet in parsed.packet if packet.HasField("track_event")
    ]

    assert events[0].name == "request (truncated begin)"
    assert not events[0].flow_ids
    assert not events[0].terminating_flow_ids
    assert events[0].debug_annotations[-1].name == "retrobus.truncated_begin"
    assert events[1].flow_ids
    assert events[2].terminating_flow_ids == events[1].flow_ids


def test_repeated_flow_start_gets_a_new_lifecycle_id(
    schema: CompactSchema,
) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        3,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        1,
        0,
        0,
        3,
        0,
        4256,
        7,
        0,
    )
    records = (
        compact_module.CompactRecord(schema.events[4], 7, 0, 100, None, (55,), 0, 100),
        compact_module.CompactRecord(schema.events[4], 7, 0, 200, None, (55,), 1, 200),
        compact_module.CompactRecord(schema.events[5], 7, 0, 300, None, (55,), 2, 300),
    )
    trace = compact_module.CompactTrace(header, schema, records, ())
    parsed = perfetto_pb2.Trace()
    parsed.ParseFromString(compact_trace_to_builder(trace).serialize())
    events = [
        packet.track_event for packet in parsed.packet if packet.HasField("track_event")
    ]

    assert events[0].flow_ids
    assert events[1].flow_ids
    assert events[0].flow_ids != events[1].flow_ids
    assert events[0].debug_annotations[-1].name == "retrobus.truncated_end"
    assert events[2].terminating_flow_ids == events[1].flow_ids


def test_orphan_flow_step_starts_a_truncated_retained_lifecycle() -> None:
    mapping = _schema_mapping()
    events = mapping["events"]
    assert isinstance(events, list)
    events.append(
        {
            "id": 8,
            "name": "request",
            "category": "io",
            "kind": "flow_step",
            "correlation_argument": "id",
            "arguments": [{"name": "id", "type": "uint"}],
        }
    )
    schema = CompactSchema.from_mapping(mapping)
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        3,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        1,
        0,
        0,
        2,
        0,
        4256,
        7,
        0,
    )
    records = (
        compact_module.CompactRecord(schema.events[8], 7, 0, 100, None, (55,), 0, 100),
        compact_module.CompactRecord(schema.events[5], 7, 0, 200, None, (55,), 1, 200),
    )
    trace = compact_module.CompactTrace(header, schema, records, ())
    parsed = perfetto_pb2.Trace()
    parsed.ParseFromString(compact_trace_to_builder(trace).serialize())
    retained = [
        packet.track_event for packet in parsed.packet if packet.HasField("track_event")
    ]

    assert retained[0].flow_ids
    assert retained[0].debug_annotations[-1].name == "retrobus.truncated_begin"
    assert retained[1].terminating_flow_ids == retained[0].flow_ids


def test_timestamp_range_error_is_protocol_specific(schema: CompactSchema) -> None:
    header = compact_module.CompactTraceHeader(
        "retrobus-compact-v2",
        1,
        1_000_000_000,
        1,
        32,
        schema.producer_id,
        schema.version,
        schema.sha256,
        b"0" * 16,
        1,
        0,
        0,
        1,
        0,
        4256,
        7,
        0,
    )
    record = compact_module.CompactRecord(schema.events[2], 7, 0, 0, None, (-1,), 0, 0)
    sync = compact_module.CompactClockSync(7, 100, 100, 0, 0, 1, 100)
    trace = compact_module.CompactTrace(header, schema, (record,), (sync,))

    with pytest.raises(CompactTraceError, match="outside Perfetto's uint64 range"):
        compact_trace_to_builder(trace)
    assert compact_trace_to_builder(trace, normalize_start=True).serialize()


def test_conversion_never_replaces_inputs_or_existing_output_on_error(
    tmp_path: Path, schema: CompactSchema
) -> None:
    capture = tmp_path / "capture.rbct"
    capture.write_bytes(_rbct_image(schema))
    with pytest.raises(CompactTraceError, match="must not replace its input"):
        convert_compact_trace(capture, schema, capture)

    schema_path = tmp_path / "schema.json"
    schema_path.write_bytes(schema.canonical_json)
    with pytest.raises(CompactTraceError, match="must not replace its schema"):
        convert_compact_trace(capture, schema_path, schema_path)

    output = tmp_path / "existing.perfetto-trace"
    output.write_bytes(b"preserve me")
    corrupt = bytearray(_rbct_image(schema))
    corrupt[160 + 48 + 3] ^= 1
    capture.write_bytes(corrupt)
    with pytest.raises(CompactTraceError):
        convert_compact_trace(capture, schema, output)
    assert output.read_bytes() == b"preserve me"
    assert not list(tmp_path.glob(".existing.perfetto-trace.partial.*"))
