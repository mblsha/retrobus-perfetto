#!/usr/bin/env python3
"""Build and verify a streaming SQLite oracle index for Perfetto traces."""

from __future__ import annotations

import argparse
from pathlib import Path

from retrobus_perfetto.oracle_index import (
    build_trace_index,
    verify_trace_index,
)


def _index_command(args: argparse.Namespace) -> int:
    stats = build_trace_index(args.trace, args.index, replace=not args.no_replace)
    print(
        "indexed "
        f"{stats.packet_count} packets "
        f"({stats.track_event_count} track events, {stats.frame_event_count} frame events) "
        f"from {stats.source_count} trace source(s) into {stats.index}"
    )
    if args.verify:
        verify_stats = verify_trace_index(args.index)
        print(
            "verified "
            f"{verify_stats.invocation_count} invocations with "
            f"{verify_stats.issue_count} issue(s) "
            f"({verify_stats.missing_exit_count} missing exits, "
            f"{verify_stats.in_flight_count} in-flight)"
        )
        return 1 if verify_stats.issue_count else 0
    return 0


def _verify_command(args: argparse.Namespace) -> int:
    stats = verify_trace_index(args.index)
    print(
        "verified "
        f"{stats.invocation_count} invocations with "
        f"{stats.issue_count} issue(s) "
        f"({stats.missing_exit_count} missing exits, "
        f"{stats.in_flight_count} in-flight)"
    )
    return 1 if stats.issue_count else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a streaming SQLite index for one or more Perfetto trace files "
            "and materialize an invocation-oriented oracle export."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser(
        "index",
        help=(
            "Stream one or more trace files into a SQLite index. "
            "Use multiple inputs for split trace chunks in capture order."
        ),
    )
    index_parser.add_argument(
        "trace",
        nargs="+",
        type=Path,
        help="Perfetto trace path(s) to index in order.",
    )
    index_parser.add_argument(
        "--index",
        required=True,
        type=Path,
        help="SQLite output path.",
    )
    index_parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Fail if the SQLite output path already exists.",
    )
    index_parser.add_argument(
        "--verify",
        action="store_true",
        help=(
            "Run integrity verification after indexing. This also populates the "
            "`oracle_invocations` export table."
        ),
    )
    index_parser.set_defaults(func=_index_command)

    verify_parser = subparsers.add_parser(
        "verify",
        help=(
            "Verify a previously built SQLite index and refresh the "
            "`oracle_invocations` and `verification_issues` tables."
        ),
    )
    verify_parser.add_argument(
        "--index",
        required=True,
        type=Path,
        help="SQLite index path.",
    )
    verify_parser.set_defaults(func=_verify_command)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
