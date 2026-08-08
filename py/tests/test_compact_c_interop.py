"""Compile the C producer and decode its exact output with the Python host."""

from pathlib import Path
import shutil
import subprocess

import pytest

from retrobus_perfetto import (
    CompactSchema,
    read_compact_trace,
    render_c_schema_header,
)


def test_c_writer_python_decoder_interoperability(tmp_path: Path) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required for the cross-language fixture")
    repository = Path(__file__).resolve().parents[2]
    compact = repository / "compact"
    schema = CompactSchema.load(compact / "tests" / "interop-schema.json")
    generated = tmp_path / "interop_schema.h"
    generated.write_text(render_c_schema_header(schema, "interop"), encoding="utf-8")
    executable = tmp_path / "write_interop_trace"
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
            str(compact / "tests" / "write_interop_trace.c"),
            "-o",
            str(executable),
        ],
        check=True,
    )
    capture = tmp_path / "interop.rbct"
    subprocess.run([executable, capture], check=True)

    trace = read_compact_trace(capture, schema)
    assert trace.header.total_records == 4
    assert trace.header.total_events == 5
    assert [record.event.id for record in trace.records] == [2, 1, 3, 300]
    assert trace.records[0].arguments == (-7,)
    assert trace.records[1].duration_ticks == 40
    assert trace.records[2].track_id == 1
    assert trace.records[3].arguments == (0xDEAD_BEEF_1234_5678,)
