"""Tests for streaming oracle indexing and verification."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tracemalloc
from pathlib import Path
from typing import BinaryIO

import pytest

from retrobus_perfetto import PerfettoTraceBuilder
from retrobus_perfetto.oracle_index import build_trace_index, verify_trace_index
from retrobus_perfetto.proto import perfetto_pb2


def _write_builder_trace(path: Path, builder: PerfettoTraceBuilder) -> None:
    path.write_bytes(builder.serialize())


def _exit_event(
    builder: PerfettoTraceBuilder,
    track: int,
    name: str,
    timestamp: int,
    **annotations: int,
) -> None:
    event = builder.add_instant_event(track, f"{name}#exit", timestamp)
    event.add_annotations(annotations)


def _rows(db_path: Path, query: str) -> list[sqlite3.Row]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return list(conn.execute(query))


def _encode_varint(value: int) -> bytes:
    encoded = bytearray()
    while value >= 0x80:
        encoded.append((value & 0x7F) | 0x80)
        value >>= 7
    encoded.append(value)
    return bytes(encoded)


def _write_packet(handle: BinaryIO, packet: object) -> None:
    payload = packet.SerializeToString()  # type: ignore[attr-defined]
    handle.write(b"\x0a")
    handle.write(_encode_varint(len(payload)))
    handle.write(payload)


def _add_int_annotation(event: object, name: str, value: int) -> None:
    annotation = event.debug_annotations.add()  # type: ignore[attr-defined]
    annotation.name = name
    annotation.uint_value = value


def test_oracle_index_pairs_nested_recursion(tmp_path: Path) -> None:
    trace_path = tmp_path / "nested.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Function execution")
    vsync = builder.add_thread("VSync")

    boundary = builder.add_instant_event(vsync, "vsync", 5)
    boundary.add_annotations({"frame_counter": 7})

    outer = builder.begin_slice(functions, "fn_outer", 10)
    outer.add_annotations(
        {
            "entry_eip": 0x1000,
            "source_eip": 0x2000,
            "idx": 1,
            "eax": 0xAA,
        }
    )
    inner = builder.begin_slice(functions, "fn_outer", 20)
    inner.add_annotations(
        {
            "entry_eip": 0x1000,
            "source_eip": 0x2010,
            "idx": 2,
            "eax": 0xBB,
        }
    )
    _exit_event(
        builder,
        functions,
        "fn_outer",
        30,
        idx=3,
        return_eip=0x3000,
        eip=0x3000,
        eax=0x11,
        eflags=0x202,
    )
    builder.end_slice(functions, 31)
    _exit_event(
        builder,
        functions,
        "fn_outer",
        40,
        idx=4,
        return_eip=0x3010,
        eip=0x3010,
        eax=0x22,
        eflags=0x246,
    )
    builder.end_slice(functions, 41)
    _write_builder_trace(trace_path, builder)

    index_path = tmp_path / "nested.sqlite"
    build_trace_index([trace_path], index_path)
    stats = verify_trace_index(index_path)

    assert stats.issue_count == 0
    rows = _rows(
        index_path,
        """
        SELECT function_name, callsite_address, vsync_counter, entry_sequence,
               exit_sequence, synthetic_close_count, terminal_close_kind,
               entry_registers_json, exit_registers_json, exit_eflags, exit_eip
        FROM oracle_invocations
        ORDER BY entry_global_packet_ordinal
        """,
    )
    assert len(rows) == 2
    assert [row["callsite_address"] for row in rows] == [0x2000, 0x2010]
    assert [row["vsync_counter"] for row in rows] == [7, 7]
    assert [row["entry_sequence"] for row in rows] == [1, 2]
    assert [row["exit_sequence"] for row in rows] == [4, 3]
    assert [row["synthetic_close_count"] for row in rows] == [0, 0]
    assert [row["terminal_close_kind"] for row in rows] == ["real_exit", "real_exit"]
    assert rows[0]["exit_eflags"] == 0x246
    assert rows[1]["exit_eip"] == 0x3000


def test_oracle_index_ignores_duration_slices_on_non_call_tracks(tmp_path: Path) -> None:
    trace_path = tmp_path / "mixed.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    files = builder.add_thread("Files")
    functions = builder.add_thread("Function execution")

    builder.begin_slice(files, "read asset", 5)
    builder.end_slice(files, 6)
    entry = builder.begin_slice(functions, "fn", 10)
    entry.add_annotations({"event_kind": "call_enter", "idx": 1})
    _exit_event(builder, functions, "fn", 20, idx=2, eip=3, return_eip=3)
    builder.end_slice(functions, 21)
    _write_builder_trace(trace_path, builder)

    index_path = tmp_path / "mixed.sqlite"
    build_trace_index([trace_path], index_path)
    stats = verify_trace_index(index_path)

    assert stats.issue_count == 0
    assert stats.invocation_count == 1
    assert _rows(index_path, "SELECT function_name FROM oracle_invocations")[0][
        "function_name"
    ] == "fn"


def test_oracle_index_stitches_synthetic_chunk_reopens(tmp_path: Path) -> None:
    chunk_a = tmp_path / "chunk-a.perfetto-trace"
    chunk_b = tmp_path / "chunk-b.perfetto-trace"

    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Function execution")
    outer = builder.begin_slice(functions, "fn_outer", 10)
    outer.add_annotations(
        {"entry_eip": 0x1000, "source_eip": 0x2000, "idx": 1, "call_id": 10}
    )
    inner = builder.begin_slice(functions, "fn_inner", 20)
    inner.add_annotations(
        {"entry_eip": 0x1100, "source_eip": 0x2100, "idx": 2, "call_id": 11}
    )
    builder.end_slice(functions, 30)
    builder.end_slice(functions, 31)
    _write_builder_trace(chunk_a, builder)

    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Function execution")
    outer = builder.begin_slice(functions, "fn_outer", 40)
    outer.add_annotations(
        {"event_kind": "synthetic_chunk_reopen", "idx": 3, "call_id": 10}
    )
    inner = builder.begin_slice(functions, "fn_inner", 41)
    inner.add_annotations(
        {"event_kind": "synthetic_chunk_reopen", "idx": 4, "call_id": 11}
    )
    _exit_event(
        builder,
        functions,
        "fn_inner",
        50,
        idx=5,
        call_id=11,
        return_eip=0x3100,
        eip=0x3100,
        eax=0x55,
        eflags=0x246,
    )
    builder.end_slice(functions, 51)
    _exit_event(
        builder,
        functions,
        "fn_outer",
        60,
        idx=6,
        call_id=10,
        return_eip=0x3000,
        eip=0x3000,
        eax=0x66,
        eflags=0x202,
    )
    builder.end_slice(functions, 61)
    _write_builder_trace(chunk_b, builder)

    index_path = tmp_path / "chunks.sqlite"
    build_trace_index([chunk_a, chunk_b], index_path)
    stats = verify_trace_index(index_path)

    assert stats.issue_count == 0
    rows = _rows(
        index_path,
        """
        SELECT function_name, synthetic_close_count, synthetic_reopen_count,
               terminal_close_kind, provenance_json
        FROM oracle_invocations
        ORDER BY entry_global_packet_ordinal
        """,
    )
    assert len(rows) == 2
    assert [row["function_name"] for row in rows] == ["fn_outer", "fn_inner"]
    assert [row["synthetic_close_count"] for row in rows] == [1, 1]
    assert [row["synthetic_reopen_count"] for row in rows] == [1, 1]
    assert [row["terminal_close_kind"] for row in rows] == ["real_exit", "real_exit"]


def test_oracle_index_reports_missing_exit_and_inflight(tmp_path: Path) -> None:
    trace_path = tmp_path / "broken.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Function execution")

    missing = builder.begin_slice(functions, "fn_missing", 10)
    missing.add_annotations({"entry_eip": 0x1000, "idx": 1})
    builder.end_slice(functions, 20)

    inflight = builder.begin_slice(functions, "fn_inflight", 30)
    inflight.add_annotations({"entry_eip": 0x1010, "idx": 2})
    _write_builder_trace(trace_path, builder)

    index_path = tmp_path / "broken.sqlite"
    build_trace_index([trace_path], index_path)
    stats = verify_trace_index(index_path)

    assert stats.issue_count == 2
    assert stats.missing_exit_count == 1
    assert stats.in_flight_count == 1
    invocations = _rows(
        index_path,
        "SELECT function_name, terminal_close_kind FROM oracle_invocations ORDER BY invocation_id",
    )
    assert [tuple(row) for row in invocations] == [
        ("fn_missing", "missing_exit"),
        ("fn_inflight", "in_flight"),
    ]
    issues = _rows(
        index_path,
        "SELECT code FROM verification_issues ORDER BY issue_id",
    )
    assert [row["code"] for row in issues] == [
        "missing_exit_probe",
        "final_in_flight_call",
    ]


def test_oracle_index_validates_frame_boundaries(tmp_path: Path) -> None:
    trace_path = tmp_path / "frames.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    vsync = builder.add_thread("VSync")
    builder.add_frame_timeline_expected_surface_start(
        10,
        cookie=1,
        token=10,
        display_frame_token=20,
    )
    boundary = builder.add_instant_event(vsync, "vsync", 15)
    boundary.add_annotations({"frame_counter": 5})
    boundary = builder.add_instant_event(vsync, "vsync", 16)
    boundary.add_annotations({"frame_counter": 4})
    _write_builder_trace(trace_path, builder)

    index_path = tmp_path / "frames.sqlite"
    build_trace_index([trace_path], index_path)
    stats = verify_trace_index(index_path)

    assert stats.issue_count == 2
    issues = _rows(
        index_path,
        "SELECT code FROM verification_issues ORDER BY issue_id",
    )
    assert [row["code"] for row in issues] == [
        "boundary_non_monotonic",
        "frame_start_without_end",
    ]


def test_oracle_index_reports_packet_loss_and_unresolved_interning(tmp_path: Path) -> None:
    trace_path = tmp_path / "interning-loss.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    diagnostics = builder.add_thread("Diagnostics")
    event = builder.add_instant_event(diagnostics, "heartbeat", 10)
    event.add_annotations({"state": "running"})
    packet = builder.trace.packet[-1]
    packet.previous_packet_dropped = True
    packet.ClearField("interned_data")
    _write_builder_trace(trace_path, builder)

    index_path = tmp_path / "interning-loss.sqlite"
    build_trace_index([trace_path], index_path)
    stats = verify_trace_index(index_path)

    assert stats.issue_count == 2
    assert [
        row["code"]
        for row in _rows(index_path, "SELECT code FROM verification_issues ORDER BY issue_id")
    ] == ["packet_loss", "unresolved_interning"]


def test_oracle_index_streams_without_trace_parse_from_string(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_path = tmp_path / "large.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Function execution")
    for idx in range(2000):
        event = builder.begin_slice(functions, f"fn_{idx}", idx * 3 + 10)
        event.add_annotations({"entry_eip": 0x1000 + idx, "idx": idx})
        _exit_event(
            builder,
            functions,
            f"fn_{idx}",
            idx * 3 + 11,
            idx=idx,
            return_eip=0x2000 + idx,
            eip=0x2000 + idx,
            eflags=0x202,
        )
        builder.end_slice(functions, idx * 3 + 12)
    _write_builder_trace(trace_path, builder)

    def fail_parse(self, data):  # type: ignore[no-untyped-def]
        raise AssertionError("Trace.ParseFromString should not be used by the stream indexer")

    monkeypatch.setattr(perfetto_pb2.Trace, "ParseFromString", fail_parse)

    index_path = tmp_path / "large.sqlite"
    build_trace_index([trace_path], index_path)
    stats = verify_trace_index(index_path)

    assert stats.issue_count == 0
    rows = _rows(
        index_path,
        "SELECT COUNT(*) AS count FROM oracle_invocations",
    )
    assert rows[0]["count"] == 2000


def test_oracle_index_preserves_producer_contract_and_provenance(tmp_path: Path) -> None:
    trace_path = tmp_path / "producer.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Function execution")
    metadata = builder.add_thread("Trace metadata")

    provenance = builder.add_instant_event(metadata, "trace_provenance", 5)
    provenance.add_annotations(
        {
            "event_kind": "trace_provenance",
            "manifest_identity": "intro-full-entry",
            "executable_sha256": "0123456789abcdef",
            "dosbox_build_git_hash": "producer-revision",
        }
    )

    entry = builder.begin_slice(functions, "fn_contract", 10)
    entry.add_annotations(
        {
            "event_kind": "call_enter",
            "temporal_seq": 10,
            "call_id": 7,
            "enter_idx": 3,
            "function_name": "fn_contract",
            "function_addr": 0x100,
            "entry_eip": 0x170100,
            "callsite": 0x200,
            "frame": 5,
            "vsync": 20,
            "side_effect_memory": "0x400..0x40f",
            "eax": 1,
        }
    )
    _exit_event(
        builder,
        functions,
        "fn_contract",
        20,
        temporal_seq=11,
        call_id=7,
        enter_idx=3,
        function_addr=0x100,
        return_eip=0x300,
        eip=0x301,
        frame=5,
        vsync=20,
        eax=2,
        eflags=0x202,
    )
    builder.end_slice(functions, 21)
    _write_builder_trace(trace_path, builder)

    index_path = tmp_path / "producer.sqlite"
    build_trace_index([trace_path], index_path)
    stats = verify_trace_index(index_path)

    assert stats.issue_count == 1
    assert _rows(index_path, "SELECT code FROM verification_issues")[0]["code"] == (
        "exit_eip_mismatch"
    )
    row = _rows(
        index_path,
        """
        SELECT function_address, callsite_address, call_id, enter_index,
               entry_sequence, exit_sequence, frame_index, vsync_counter,
               return_address, exit_eip, side_effects_json, provenance_json
        FROM oracle_invocations
        """,
    )[0]
    assert row["function_address"] == 0x100
    assert row["callsite_address"] == 0x200
    assert row["call_id"] == "7"
    assert row["enter_index"] == "3"
    assert (row["entry_sequence"], row["exit_sequence"]) == (10, 11)
    assert (row["frame_index"], row["vsync_counter"]) == (5, 20)
    assert (row["return_address"], row["exit_eip"]) == (0x300, 0x301)
    assert '"side_effect_memory":"0x400..0x40f"' in row["side_effects_json"]
    assert '"function_address_key":"function_addr"' in row["provenance_json"]
    assert '"entry_sequence_key":"temporal_seq"' in row["provenance_json"]
    run_provenance = json.loads(row["provenance_json"])["trace_provenance"]
    assert run_provenance["manifest_identity"] == "intro-full-entry"
    assert run_provenance["executable_sha256"] == "0123456789abcdef"
    assert run_provenance["dosbox_build_git_hash"] == "producer-revision"


def test_oracle_index_rejects_malformed_exit_lifecycle(tmp_path: Path) -> None:
    trace_path = tmp_path / "malformed.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Function execution")

    entry = builder.begin_slice(functions, "fn_duplicate", 10)
    entry.add_annotations({"idx": 1, "call_id": 1})
    _exit_event(builder, functions, "fn_duplicate", 20, idx=2, call_id=1, eip=3, return_eip=3)
    _exit_event(builder, functions, "fn_duplicate", 21, idx=3, call_id=1, eip=3, return_eip=3)
    builder.end_slice(functions, 22)

    entry = builder.begin_slice(functions, "fn_missing_close", 30)
    entry.add_annotations({"idx": 4, "call_id": 2})
    _exit_event(
        builder,
        functions,
        "fn_missing_close",
        40,
        idx=5,
        call_id=2,
        eip=4,
        return_eip=4,
    )
    _write_builder_trace(trace_path, builder)

    index_path = tmp_path / "malformed.sqlite"
    build_trace_index([trace_path], index_path)
    stats = verify_trace_index(index_path)

    assert stats.in_flight_count == 0
    assert [
        row["code"]
        for row in _rows(index_path, "SELECT code FROM verification_issues ORDER BY issue_id")
    ] == ["duplicate_exit_probe", "missing_slice_end"]
    rows = _rows(
        index_path,
        "SELECT function_name, terminal_close_kind FROM oracle_invocations ORDER BY invocation_id",
    )
    assert [tuple(row) for row in rows] == [
        ("fn_duplicate", "real_exit"),
        ("fn_missing_close", "missing_slice_end"),
    ]


def test_synthetic_reopen_requires_a_source_chunk_boundary(tmp_path: Path) -> None:
    trace_path = tmp_path / "same-source.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Function execution")
    entry = builder.begin_slice(functions, "fn", 10)
    entry.add_annotations({"idx": 1, "call_id": 1})
    builder.end_slice(functions, 20)
    reopen = builder.begin_slice(functions, "fn", 30)
    reopen.add_annotations(
        {"idx": 2, "call_id": 1, "event_kind": "synthetic_chunk_reopen"}
    )
    _exit_event(builder, functions, "fn", 40, idx=3, call_id=1, eip=4, return_eip=4)
    builder.end_slice(functions, 41)
    _write_builder_trace(trace_path, builder)

    index_path = tmp_path / "same-source.sqlite"
    build_trace_index([trace_path], index_path)
    verify_trace_index(index_path)
    codes = {
        row["code"] for row in _rows(index_path, "SELECT code FROM verification_issues")
    }
    assert "missing_exit_probe" in codes
    assert "unexpected_synthetic_reopen" in codes


def test_index_path_cannot_overwrite_a_trace_source(tmp_path: Path) -> None:
    trace_path = tmp_path / "source.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess")
    _write_builder_trace(trace_path, builder)
    original = trace_path.read_bytes()

    with pytest.raises(ValueError, match="must not overwrite"):
        build_trace_index([trace_path], trace_path)

    assert trace_path.read_bytes() == original


def test_failed_reindex_preserves_the_existing_index(tmp_path: Path) -> None:
    valid_trace = tmp_path / "valid.perfetto-trace"
    _write_builder_trace(valid_trace, PerfettoTraceBuilder("TestProcess"))
    index_path = tmp_path / "trace.sqlite"
    build_trace_index([valid_trace], index_path)

    malformed_trace = tmp_path / "malformed.perfetto-trace"
    malformed_trace.write_bytes(b"not a trace")
    with pytest.raises(ValueError):
        build_trace_index([malformed_trace], index_path)

    row = _rows(index_path, "SELECT value FROM metadata WHERE key = 'format'")[0]
    assert row["value"] == "retrobus-perfetto-oracle-index-v2"


def test_oracle_index_accepts_full_uint64_track_uuid(tmp_path: Path) -> None:
    trace_path = tmp_path / "uint64.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
    functions = builder.add_thread("Function execution")
    large_uuid = 1 << 63
    for packet in builder.trace.packet:
        if packet.HasField("track_descriptor") and packet.track_descriptor.uuid == functions:
            packet.track_descriptor.uuid = large_uuid
        if packet.HasField("track_event") and packet.track_event.track_uuid == functions:
            packet.track_event.track_uuid = large_uuid
    _write_builder_trace(trace_path, builder)

    index_path = tmp_path / "uint64.sqlite"
    build_trace_index([trace_path], index_path)
    row = _rows(index_path, "SELECT track_uuid FROM tracks WHERE name = 'Function execution'")[0]
    assert row["track_uuid"] == str(large_uuid)


def test_oracle_cli_indexes_and_verifies(tmp_path: Path) -> None:
    trace_path = tmp_path / "cli.perfetto-trace"
    builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
    functions = builder.add_thread("Function execution")
    entry = builder.begin_slice(functions, "fn", 10)
    entry.add_annotations({"idx": 1})
    _exit_event(builder, functions, "fn", 20, idx=2, eip=3, return_eip=3)
    builder.end_slice(functions, 21)
    _write_builder_trace(trace_path, builder)
    index_path = tmp_path / "cli.sqlite"
    tool = Path(__file__).parents[2] / "tools" / "perfetto_trace_oracle.py"

    result = subprocess.run(
        [
            sys.executable,
            str(tool),
            "index",
            str(trace_path),
            "--index",
            str(index_path),
            "--verify",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert f"into {index_path}" in result.stdout
    assert "verified 1 invocations with 0 issue(s)" in result.stdout


def test_large_trace_is_generated_and_indexed_as_a_wire_stream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_path = tmp_path / "large-wire.perfetto-trace"
    invocation_count = 10_000
    with trace_path.open("wb") as handle:
        descriptor = perfetto_pb2.TracePacket()
        descriptor.track_descriptor.uuid = 1
        descriptor.track_descriptor.name = "Function execution"
        _write_packet(handle, descriptor)
        for idx in range(invocation_count):
            begin = perfetto_pb2.TracePacket(timestamp=idx * 3 + 1)
            begin.track_event.type = perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN
            begin.track_event.track_uuid = 1
            begin.track_event.name = "fn"
            _add_int_annotation(begin.track_event, "idx", idx * 2)
            _write_packet(handle, begin)

            exit_packet = perfetto_pb2.TracePacket(timestamp=idx * 3 + 2)
            exit_packet.track_event.type = perfetto_pb2.TrackEvent.TYPE_INSTANT
            exit_packet.track_event.track_uuid = 1
            exit_packet.track_event.name = "fn#exit"
            _add_int_annotation(exit_packet.track_event, "idx", idx * 2 + 1)
            _add_int_annotation(exit_packet.track_event, "return_eip", 0x1000)
            _add_int_annotation(exit_packet.track_event, "eip", 0x1000)
            _write_packet(handle, exit_packet)

            end = perfetto_pb2.TracePacket(timestamp=idx * 3 + 3)
            end.track_event.type = perfetto_pb2.TrackEvent.TYPE_SLICE_END
            end.track_event.track_uuid = 1
            _write_packet(handle, end)

    def fail_parse(self, data):  # type: ignore[no-untyped-def]
        raise AssertionError("Trace.ParseFromString must not be used")

    monkeypatch.setattr(perfetto_pb2.Trace, "ParseFromString", fail_parse)
    index_path = tmp_path / "large-wire.sqlite"
    tracemalloc.start()
    build_trace_index([trace_path], index_path)
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    stats = verify_trace_index(index_path)

    assert stats.issue_count == 0
    assert stats.invocation_count == invocation_count
    assert peak_bytes < 16 * 1024 * 1024
