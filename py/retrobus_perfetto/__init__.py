"""
retrobus-perfetto: A minimal Perfetto trace generation library for retrocomputer emulators.

This package provides a clean API for generating Perfetto traces from emulator execution data.
It's designed to be CPU-independent and reusable across different retrocomputer projects.

Note: This package currently uses direct protobuf generation. Future versions may migrate
to the official Perfetto Python SDK for better compatibility and features.
"""

from .builder import PerfettoTraceBuilder
from .compact import (
    CompactClockSync,
    CompactRecord,
    CompactTrace,
    CompactTraceError,
    CompactTraceReader,
    compact_trace_to_builder,
    convert_compact_trace,
    read_compact_trace,
)
from .compact_schema import (
    CompactArgumentSchema,
    CompactEventSchema,
    CompactSchema,
    CompactSchemaError,
    CompactTrackSchema,
    render_c_schema_header,
)
from .annotations import DebugAnnotationBuilder, TrackEventWrapper
from .oracle_index import (
    IndexStats,
    TracePacketRecord,
    VerifyStats,
    build_trace_index,
    iter_trace_packets,
    verify_trace_index,
)
from .reader import resolve_interned_trace
from .merge import merge_perfetto_traces

# Make proto module available for direct import
from . import proto

__version__ = "0.4.0"
__all__ = [
    "PerfettoTraceBuilder",
    "CompactArgumentSchema",
    "CompactClockSync",
    "CompactEventSchema",
    "CompactRecord",
    "CompactSchema",
    "CompactSchemaError",
    "CompactTrace",
    "CompactTraceError",
    "CompactTraceReader",
    "CompactTrackSchema",
    "DebugAnnotationBuilder",
    "IndexStats",
    "TracePacketRecord",
    "TrackEventWrapper",
    "VerifyStats",
    "build_trace_index",
    "compact_trace_to_builder",
    "convert_compact_trace",
    "iter_trace_packets",
    "merge_perfetto_traces",
    "resolve_interned_trace",
    "read_compact_trace",
    "render_c_schema_header",
    "verify_trace_index",
    "proto",
]
