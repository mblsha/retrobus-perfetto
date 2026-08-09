#!/usr/bin/env python3
"""Train and render a static compact v4 codec profile from trace corpora."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPOSITORY_ROOT / "py"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from retrobus_perfetto.compact import CompactTraceError, read_compact_trace  # noqa: E402
from retrobus_perfetto.compact_codec import (  # noqa: E402
    CompactCodecProfile,
    CompactCodecProfileError,
    render_c_codec_profile,
)
from retrobus_perfetto.compact_schema import (  # noqa: E402
    CompactSchema,
    CompactSchemaError,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--input-codec-profile",
        type=Path,
        help="profile needed to decode profiled RBCTRC4 training captures",
    )
    parser.add_argument("--c-header", type=Path)
    parser.add_argument("--c-prefix", default="RBCT_CODEC")
    parser.add_argument("--entry-limit", type=int, choices=(128, 247), default=247)
    parser.add_argument("--state-events", type=int, nargs=2, metavar=("A", "B"))
    parser.add_argument("--allow-unfinalized", action="store_true")
    args = parser.parse_args()
    try:
        schema = CompactSchema.load(args.schema)
        input_profile = (
            CompactCodecProfile.load(args.input_codec_profile, schema)
            if args.input_codec_profile is not None
            else None
        )
        traces = [
            read_compact_trace(
                capture,
                schema,
                allow_unfinalized=args.allow_unfinalized,
                codec_profile=input_profile,
            )
            for capture in args.captures
        ]
        profile = CompactCodecProfile.train(
            traces,
            schema,
            entry_limit=args.entry_limit,
            state_events=(tuple(args.state_events) if args.state_events else None),
        )
        args.output.write_bytes(profile.canonical_json + b"\n")
        if args.c_header is not None:
            args.c_header.write_text(
                render_c_codec_profile(profile, args.c_prefix), encoding="utf-8"
            )
    except (
        CompactTraceError,
        CompactCodecProfileError,
        CompactSchemaError,
        OSError,
    ) as error:
        parser.error(str(error))
    print(
        f"profile={profile.sha256.hex()} entries={len(profile.entries)} "
        f"limit={profile.entry_limit} state_events={profile.state_events[0]},"
        f"{profile.state_events[1]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
