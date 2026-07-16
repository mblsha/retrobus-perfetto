from pathlib import Path
from typing import Iterator, Sequence

from .oracle_index import IndexStats, VerifyStats


def build_trace_index(
    trace_paths: Sequence[Path | str],
    index_path: Path | str,
    *,
    replace: bool = True,
) -> IndexStats: ...


def iter_trace_packets(trace_paths: Sequence[Path]) -> Iterator[object]: ...


def verify_trace_index(index_path: Path | str) -> VerifyStats: ...
