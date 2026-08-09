from pathlib import Path
from typing import Iterator, Sequence

from . import proto as proto
from .annotations import DebugAnnotationBuilder as DebugAnnotationBuilder
from .annotations import TrackEventWrapper as TrackEventWrapper
from .builder import PerfettoTraceBuilder as PerfettoTraceBuilder
from .compact import CompactClockSync as CompactClockSync
from .compact import CompactRecord as CompactRecord
from .compact import CompactTrace as CompactTrace
from .compact import CompactTraceError as CompactTraceError
from .compact import CompactTraceReader as CompactTraceReader
from .compact import compact_trace_to_builder as compact_trace_to_builder
from .compact import convert_compact_trace as convert_compact_trace
from .compact import read_compact_trace as read_compact_trace
from .compact_schema import CompactArgumentSchema as CompactArgumentSchema
from .compact_schema import CompactEventSchema as CompactEventSchema
from .compact_schema import CompactSchema as CompactSchema
from .compact_schema import CompactSchemaError as CompactSchemaError
from .compact_schema import CompactTrackSchema as CompactTrackSchema
from .compact_schema import render_c_schema_header as render_c_schema_header
from .compact_profile import aggregate_density_reports as aggregate_density_reports
from .compact_profile import model_compact_trace as model_compact_trace
from .compact_profile import profile_compact_corpus as profile_compact_corpus
from .compact_profile import profile_compact_trace as profile_compact_trace
from .oracle_index import IndexStats as IndexStats
from .oracle_index import TracePacketRecord as TracePacketRecord
from .oracle_index import VerifyStats as VerifyStats
from .merge import merge_perfetto_traces as merge_perfetto_traces

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
