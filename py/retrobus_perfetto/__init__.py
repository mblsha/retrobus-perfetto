"""
retrobus-perfetto: A minimal Perfetto trace generation library for retrocomputer emulators.

This package provides a clean API for generating Perfetto traces from emulator execution data.
It's designed to be CPU-independent and reusable across different retrocomputer projects.

Note: This package currently uses direct protobuf generation. Future versions may migrate
to the official Perfetto Python SDK for better compatibility and features.
"""

from .builder import PerfettoTraceBuilder
from .annotations import DebugAnnotationBuilder, TrackEventWrapper

__version__ = "0.1.0"
__all__ = ["PerfettoTraceBuilder", "DebugAnnotationBuilder", "TrackEventWrapper"]
