#!/usr/bin/env python3
"""Generate target-side compact trace constants from a producer schema."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPOSITORY_ROOT / "py"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from retrobus_perfetto.compact_schema import (  # noqa: E402
    CompactSchema,
    render_c_schema_header,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--prefix")
    args = parser.parse_args()

    schema = CompactSchema.load(args.schema)
    rendered = render_c_schema_header(schema, args.prefix)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f"{args.output.name}.partial.{os.getpid()}")
    try:
        temporary.write_text(rendered, encoding="utf-8")
        os.replace(temporary, args.output)
    finally:
        temporary.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
