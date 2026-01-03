"""Tests for function trace summarization."""

from pathlib import Path

from retrobus_perfetto import PerfettoTraceBuilder
from retrobus_perfetto.function_trace_summary import (
    load_name_map,
    summarize_trace_to_yaml,
)


def _write_trace(path: Path) -> None:
    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Functions")
    opcodes = builder.add_thread("Opcodes")

    # Top-level function with nested repeated calls.
    top_evt = builder.begin_slice(functions, "fn@0x1000", 10)
    top_evt.add_annotations(
        {
            "from": 0x2000,
            "to": 0x1000,
            "depth": 1,
            "op_index": 1,
            "flag": True,
            "tag": "alpha",
        }
    )

    child_evt = builder.begin_slice(functions, "fn@0x1010", 20)
    child_evt.add_annotations(
        {
            "from": 0x1000,
            "to": 0x1010,
            "depth": 2,
            "op_index": 2,
        }
    )
    builder.end_slice(functions, 30)

    child_evt = builder.begin_slice(functions, "fn@0x1010", 40)
    child_evt.add_annotations(
        {
            "from": 0x1000,
            "to": 0x1010,
            "depth": 2,
            "op_index": 3,
        }
    )
    builder.end_slice(functions, 50)

    builder.end_slice(functions, 60)

    # Another top-level function.
    evt = builder.begin_slice(functions, "fn@0x2000", 70)
    evt.add_annotations({"from": 0x0, "to": 0x2000, "depth": 1, "op_index": 4})
    builder.end_slice(functions, 90)

    # Noise on a different track to ensure filtering works.
    evt = builder.begin_slice(opcodes, "NOP", 15)
    evt.add_annotations({"pc": 0xDEADBEEF})
    builder.end_slice(opcodes, 16)

    path.write_bytes(builder.serialize())


def test_function_trace_summary(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.perfetto-trace"
    _write_trace(trace_path)

    name_map_path = tmp_path / "names.json"
    name_map_path.write_text(
        '{"names": {"4096": "init", "4112": "worker", "8192": "handler"}}',
        encoding="utf-8",
    )
    name_map = load_name_map(name_map_path)

    summary = summarize_trace_to_yaml(
        trace_path,
        include_tracks=["Functions"],
        ignore_keys=["op_index"],
        name_map=name_map,
    )

    expected = """functions:
  'Functions::handler@0x002000':
    count: 1
    args:
      - count: 1
        from: 0x0
        to: 0x2000
  'Functions::init@0x001000':
    count: 1
    args:
      - count: 1
        flag: true
        from: 0x2000
        tag: alpha
        to: 0x1000
    children:
      'Functions::worker@0x001010':
        count: 2
        args:
          - count: 2
            from: 0x1000
            to: 0x1010
"""
    assert summary == expected
