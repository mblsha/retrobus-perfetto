#!/usr/bin/env python3
"""Profile compact trace density by replaying v1, v2, and v3 encodings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPOSITORY_ROOT / "py"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from retrobus_perfetto.compact import CompactTraceError  # noqa: E402
from retrobus_perfetto.compact_profile import (  # noqa: E402
    aggregate_density_reports,
    profile_compact_trace,
)
from retrobus_perfetto.compact_schema import (  # noqa: E402
    CompactSchema,
    CompactSchemaError,
)


def _manifest_inputs(path: Path) -> tuple[Path, list[tuple[Path, dict[str, Any]]]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("schema"), str):
        raise ValueError("corpus manifest must contain a schema path")
    raw_captures = value.get("captures")
    if not isinstance(raw_captures, list) or not raw_captures:
        raise ValueError("corpus manifest must contain a non-empty captures array")
    schema = (path.parent / value["schema"]).resolve()
    captures = []
    for index, raw_capture in enumerate(raw_captures):
        if not isinstance(raw_capture, dict) or not isinstance(
            raw_capture.get("path"), str
        ):
            raise ValueError(f"captures[{index}] must contain a path")
        capture_path = (path.parent / raw_capture["path"]).resolve()
        provenance = {key: item for key, item in raw_capture.items() if key != "path"}
        captures.append((capture_path, provenance))
    return schema, captures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="*", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-unfinalized", action="store_true")
    parser.add_argument(
        "--fail-on-v2-mismatch",
        action="store_true",
        help="fail if an eligible actual v2 capture does not match the v2 replay",
    )
    args = parser.parse_args()
    if args.manifest is not None:
        if args.schema is not None or args.captures:
            parser.error("--manifest cannot be combined with captures or --schema")
        try:
            schema_path, captures = _manifest_inputs(args.manifest)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            parser.error(str(error))
    else:
        if args.schema is None or not args.captures:
            parser.error("captures and --schema are required without --manifest")
        schema_path = args.schema
        captures = [(path, {}) for path in args.captures]

    try:
        schema = CompactSchema.load(schema_path)
        reports = []
        for capture, provenance in captures:
            report = dict(
                profile_compact_trace(
                    capture,
                    schema,
                    allow_unfinalized=args.allow_unfinalized,
                )
            )
            report["provenance"] = provenance
            reports.append(report)
    except (CompactSchemaError, CompactTraceError, OSError) as error:
        parser.error(str(error))

    result = {
        "format": "retrobus-compact-density-profile-v1",
        "schema_path": str(schema_path),
        "captures": reports,
        "aggregate": aggregate_density_reports(reports),
    }
    if args.fail_on_v2_mismatch and result["aggregate"][
        "v2_predictions_all_match"
    ] is False:
        parser.error("v2 replay does not match actual chunk used lengths")
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
