"""Compile the C producer and decode its exact output with the Python host."""

from pathlib import Path
import shutil
import struct
import subprocess

import pytest

from retrobus_perfetto import (
    CompactSchema,
    read_compact_trace,
    render_c_schema_header,
)
from retrobus_perfetto.compact import FLAG_CHUNK_HEADER_CRC


def _compile_producer(
    compiler: str,
    repository: Path,
    tmp_path: Path,
    source_name: str,
) -> tuple[CompactSchema, Path]:
    compact = repository / "compact"
    schema = CompactSchema.load(compact / "tests" / "interop-schema.json")
    generated = tmp_path / "interop_schema.h"
    generated.write_text(render_c_schema_header(schema, "interop"), encoding="utf-8")
    executable = tmp_path / Path(source_name).stem
    subprocess.run(
        [
            compiler,
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{compact / 'include'}",
            f"-I{tmp_path}",
            str(compact / "src" / "compact_trace.c"),
            str(compact / "tests" / source_name),
            "-o",
            str(executable),
        ],
        check=True,
    )
    return schema, executable


def test_c_writer_python_decoder_interoperability(tmp_path: Path) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required for the cross-language fixture")
    repository = Path(__file__).resolve().parents[2]
    schema, executable = _compile_producer(
        compiler, repository, tmp_path, "write_interop_trace.c"
    )
    capture = tmp_path / "interop.rbct"
    subprocess.run([executable, capture], check=True)

    trace = read_compact_trace(capture, schema)
    assert trace.header.flags & FLAG_CHUNK_HEADER_CRC
    assert trace.header.total_records == 4
    assert trace.header.total_events == 5
    assert trace.header.dropped_records == 3
    assert [record.event.id for record in trace.records] == [2, 1, 3, 300]
    assert trace.records[0].arguments == (-7,)
    assert trace.records[1].duration_ticks == 40
    assert trace.records[2].track_id == 1
    assert trace.records[3].arguments == (0xDEAD_BEEF_1234_5678,)


def test_wrapped_c_writer_remains_decodable_after_anchor_loss(
    tmp_path: Path,
) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required for the cross-language fixture")
    repository = Path(__file__).resolve().parents[2]
    schema, executable = _compile_producer(
        compiler, repository, tmp_path, "write_ring_interop_trace.c"
    )
    capture = tmp_path / "wrapped.rbct"

    subprocess.run([executable, capture], check=True)
    trace = read_compact_trace(capture, schema)

    assert trace.header.ring_wrapped
    assert trace.header.total_records == 500
    assert trace.header.overwritten_records == 252
    assert len(trace.records) == 248
    assert {record.generation for record in trace.records} == {7}
    assert {sync.generation for sync in trace.clock_syncs} == {8}
    assert trace.uncorrelated_generations == (7,)
    assert trace.timestamp_ns(7, trace.records[-1].extended_tick) == 2000
    assert trace.timestamp_ns(8, trace.clock_syncs[0].extended_tick) == 2000


def test_live_wrapped_c_writer_recovers_after_anchor_loss(tmp_path: Path) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required for the cross-language fixture")
    repository = Path(__file__).resolve().parents[2]
    schema, executable = _compile_producer(
        compiler, repository, tmp_path, "write_ring_interop_trace.c"
    )
    capture = tmp_path / "live-wrapped.rbct"

    subprocess.run([executable, capture, "live"], check=True)
    trace = read_compact_trace(capture, schema, allow_unfinalized=True)

    assert not trace.header.finalized
    assert trace.header.ring_wrapped
    assert len(trace.records) == 248
    assert trace.uncorrelated_generations == (7,)

    legacy_image = bytearray(capture.read_bytes())
    struct.pack_into("<H", legacy_image, 38, 0)
    legacy_capture = tmp_path / "live-wrapped-without-flag.rbct"
    legacy_capture.write_bytes(legacy_image)
    inferred = read_compact_trace(
        legacy_capture, schema, allow_unfinalized=True
    )
    assert inferred.header.ring_wrapped
    assert inferred.uncorrelated_generations == (7,)


def test_wrapped_c_writer_can_retain_later_clock_generations(
    tmp_path: Path,
) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required for the cross-language fixture")
    repository = Path(__file__).resolve().parents[2]
    schema, executable = _compile_producer(
        compiler, repository, tmp_path, "write_generation_ring_interop_trace.c"
    )
    capture = tmp_path / "later-generations.rbct"

    subprocess.run([executable, capture], check=True)
    trace = read_compact_trace(capture, schema)

    assert trace.header.ring_wrapped
    assert [sync.generation for sync in trace.clock_syncs] == [9, 10]
