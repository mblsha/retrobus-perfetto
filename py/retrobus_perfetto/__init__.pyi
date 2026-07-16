from pathlib import Path
from typing import Iterator, Sequence

from . import proto as proto
from .annotations import DebugAnnotationBuilder as DebugAnnotationBuilder
from .annotations import TrackEventWrapper as TrackEventWrapper
from .builder import PerfettoTraceBuilder as PerfettoTraceBuilder
from .oracle_index import IndexStats as IndexStats
from .oracle_index import TracePacketRecord as TracePacketRecord
from .oracle_index import VerifyStats as VerifyStats

__version__: str


def build_trace_index(
    trace_paths: Sequence[Path | str],
    index_path: Path | str,
    *,
    replace: bool = True,
) -> IndexStats: ...


def iter_trace_packets(
    trace_paths: Sequence[Path | str],
) -> Iterator[TracePacketRecord]: ...


def verify_trace_index(index_path: Path | str) -> VerifyStats: ...
