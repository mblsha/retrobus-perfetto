#!/usr/bin/env python3
"""Convert a producer-neutral `.rbct` image into native Perfetto."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPOSITORY_ROOT / "py"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from retrobus_perfetto.compact import (  # noqa: E402
    CompactTraceError,
    convert_compact_trace,
)
from retrobus_perfetto.compact_schema import CompactSchemaError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--normalize-start", action="store_true")
    parser.add_argument(
        "--allow-unfinalized",
        action="store_true",
        help="accept a crash image without finalized CRCs",
    )
    args = parser.parse_args()
    try:
        summary = convert_compact_trace(
            args.input,
            args.schema,
            args.output,
            normalize_start=args.normalize_start,
            allow_unfinalized=args.allow_unfinalized,
        )
    except (CompactTraceError, CompactSchemaError) as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
