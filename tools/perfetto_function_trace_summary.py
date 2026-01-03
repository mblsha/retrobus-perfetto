#!/usr/bin/env python3
"""Summarize Perfetto function-trace slices into a compact YAML call graph."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from retrobus_perfetto.function_trace_summary import (
    load_name_map,
    summarize_trace_to_yaml,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize function slice traces into a YAML call graph."
    )
    parser.add_argument("trace", type=Path, help="Path to Perfetto trace file")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output YAML path (default: <trace>.functions.yaml)",
    )
    parser.add_argument(
        "--track",
        action="append",
        required=True,
        help="Track name(s) that contain function slices. Can be repeated.",
    )
    parser.add_argument(
        "--exclude-track",
        action="append",
        default=None,
        help="Exclude specific track name(s). Can be repeated.",
    )
    parser.add_argument(
        "--ignore-key",
        action="append",
        default=[],
        help="Debug-annotation key to drop before deduplication.",
    )
    parser.add_argument(
        "--int-format",
        choices=("hex", "dec"),
        default="hex",
        help="Format for integer debug annotations.",
    )
    parser.add_argument(
        "--name-map",
        type=Path,
        default=None,
        help="Optional JSON mapping (e.g., bnida.json) for function name resolution.",
    )
    parser.add_argument(
        "--name-format",
        choices=("name@addr", "name"),
        default="name@addr",
        help="How to emit resolved names when a map is provided.",
    )
    args = parser.parse_args()

    if not args.trace.exists():
        raise SystemExit(f"Trace not found: {args.trace}")

    out_path = args.out or args.trace.with_suffix(args.trace.suffix + ".functions.yaml")

    name_map: Optional[dict[int, str]] = None
    if args.name_map:
        name_map = load_name_map(args.name_map)

    content = summarize_trace_to_yaml(
        args.trace,
        ignore_keys=args.ignore_key,
        include_tracks=args.track,
        exclude_tracks=args.exclude_track,
        name_map=name_map,
        name_format=args.name_format,
        int_format=args.int_format,
    )
    out_path.write_text(content, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
