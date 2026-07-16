#!/usr/bin/env python3
"""Normalize a Perfetto trace and add a full-duration render anchor."""

from __future__ import annotations

import argparse
from pathlib import Path

from retrobus_perfetto.proto import perfetto_pb2
from retrobus_perfetto.trace_prepare import prepare_trace_for_render


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--normalize-start",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="subtract the first real event timestamp so the render starts at 0",
    )
    parser.add_argument(
        "--synthetic-span",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="add a full-duration synthetic slice on its own track",
    )
    args = parser.parse_args()

    trace = perfetto_pb2.Trace()
    trace.ParseFromString(args.trace.read_bytes())
    bounds = prepare_trace_for_render(
        trace,
        perfetto_pb2,
        normalize_start=args.normalize_start,
        synthetic_span=args.synthetic_span,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(trace.SerializeToString())
    print(f"wrote {args.out}")
    print(f"source_start_ns={bounds.source_start_ns}")
    print(f"render_duration_ns={bounds.duration_ns}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
