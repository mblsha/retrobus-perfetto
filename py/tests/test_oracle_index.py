"""Tests for streaming oracle indexing and verification."""

from __future__ import annotations

import sqlite3
from pathlib import Path

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


def test_oracle_index_stitches_synthetic_chunk_reopens(tmp_path: Path) -> None:
    chunk_a = tmp_path / "chunk-a.perfetto-trace"
    chunk_b = tmp_path / "chunk-b.perfetto-trace"

    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Function execution")
    outer = builder.begin_slice(functions, "fn_outer", 10)
    outer.add_annotations({"entry_eip": 0x1000, "source_eip": 0x2000, "idx": 1})
    inner = builder.begin_slice(functions, "fn_inner", 20)
    inner.add_annotations({"entry_eip": 0x1100, "source_eip": 0x2100, "idx": 2})
    builder.end_slice(functions, 30)
    builder.end_slice(functions, 31)
    _write_builder_trace(chunk_a, builder)

    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Function execution")
    outer = builder.begin_slice(functions, "fn_outer", 40)
    outer.add_annotations({"event_kind": "synthetic_chunk_reopen", "idx": 3})
    inner = builder.begin_slice(functions, "fn_inner", 41)
    inner.add_annotations({"event_kind": "synthetic_chunk_reopen", "idx": 4})
    _exit_event(
        builder,
        functions,
        "fn_inner",
        50,
        idx=5,
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
