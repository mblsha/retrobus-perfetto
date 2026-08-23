"""Typed values used by the high-fidelity Perfetto builder APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Union


@dataclass(frozen=True)
class UInt:
    """An unsigned debug-annotation integer."""

    value: int

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 0xFFFF_FFFF_FFFF_FFFF:
            raise ValueError("UInt must fit in uint64")


@dataclass(frozen=True)
class Pointer:
    """A debug-annotation pointer, rendered separately from uint64 values."""

    value: int

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 0xFFFF_FFFF_FFFF_FFFF:
            raise ValueError("Pointer must fit in uint64")


@dataclass(frozen=True)
class SourceLocation:
    """A source location usable inline or through InternedData."""

    file_name: str = ""
    function_name: str = ""
    line_number: Optional[int] = None

    def __post_init__(self) -> None:
        if self.line_number is not None and not 0 <= self.line_number <= 0xFFFF_FFFF:
            raise ValueError("line_number must fit in uint32")


@dataclass(frozen=True)
class StackMapping:
    """An executable mapping referenced by native stack frames.

    ``path`` is stored as upstream Perfetto path components. ``build_id`` is
    raw build-ID bytes; a string is UTF-8 encoded for producers whose build ID
    is already a textual identifier (for example a Windows module GUID).
    """

    path: Sequence[str]
    build_id: Optional[Union[bytes, str]] = None
    exact_offset: Optional[int] = None
    start_offset: Optional[int] = None
    start: Optional[int] = None
    end: Optional[int] = None
    load_bias: Optional[int] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", tuple(self.path))
        if any(not isinstance(component, str) for component in self.path):
            raise TypeError("mapping path components must be strings")
        for name in (
            "exact_offset",
            "start_offset",
            "start",
            "end",
            "load_bias",
        ):
            value = getattr(self, name)
            if value is not None and not 0 <= value <= 0xFFFF_FFFF_FFFF_FFFF:
                raise ValueError(f"{name} must fit in uint64")


@dataclass(frozen=True)
class StackFrame:
    """A frame for an interned, flamegraph-capable native callstack."""

    function_name: Optional[str] = None
    mapping: Optional[StackMapping] = None
    rel_pc: Optional[int] = None
    source_path: Optional[str] = None
    line_number: Optional[int] = None
    kind: Optional[Union[int, str]] = None

    def __post_init__(self) -> None:
        if self.mapping is not None and self.rel_pc is None:
            raise ValueError("rel_pc is required when mapping is set")
        if self.rel_pc is not None and not 0 <= self.rel_pc <= 0xFFFF_FFFF_FFFF_FFFF:
            raise ValueError("rel_pc must fit in uint64")
        if self.line_number is not None and not 0 <= self.line_number <= 0xFFFF_FFFF:
            raise ValueError("line_number must fit in uint32")
        if isinstance(self.kind, int) and not 0 <= self.kind <= 6:
            raise ValueError("integer frame kind must be an official Frame.Kind value")
        if self.kind is not None and not isinstance(self.kind, (int, str)):
            raise TypeError("frame kind must be an integer enum or custom string")


@dataclass(frozen=True)
class InlineFrame:
    """A symbolized frame for TrackEvent.InlineCallstack."""

    function_name: str
    source_file: Optional[str] = None
    line_number: Optional[int] = None

    def __post_init__(self) -> None:
        if self.line_number is not None and not 0 <= self.line_number <= 0xFFFF_FFFF:
            raise ValueError("line_number must fit in uint32")


@dataclass(frozen=True)
class ClockReading:
    """One clock reading in a Perfetto ClockSnapshot."""

    clock_id: int
    timestamp: int
    is_incremental: Optional[bool] = None
    unit_multiplier_ns: Optional[int] = None

    def __post_init__(self) -> None:
        if not 0 <= self.clock_id <= 0xFFFF_FFFF:
            raise ValueError("clock_id must fit in uint32")
        if not 0 <= self.timestamp <= 0xFFFF_FFFF_FFFF_FFFF:
            raise ValueError("timestamp must fit in uint64")
        if self.unit_multiplier_ns is not None and not (
            0 < self.unit_multiplier_ns <= 0xFFFF_FFFF_FFFF_FFFF
        ):
            raise ValueError("unit_multiplier_ns must be a positive uint64")


@dataclass(frozen=True)
class LegacyEvent:
    """Lossless Chrome legacy-event payload for uncommon phase semantics."""

    phase: Union[int, str]
    duration_us: Optional[int] = None
    thread_duration_us: Optional[int] = None
    thread_instruction_delta: Optional[int] = None
    id: Optional[int] = None
    id_type: str = "unscoped"
    id_scope: Optional[str] = None
    use_async_tts: Optional[bool] = None
    bind_id: Optional[int] = None
    bind_to_enclosing: Optional[bool] = None
    flow_direction: Optional[int] = None
    instant_event_scope: Optional[int] = None
    pid_override: Optional[int] = None
    tid_override: Optional[int] = None

    def phase_value(self) -> int:
        """Return the official int32 representation of the Chrome phase byte."""
        if isinstance(self.phase, str):
            if len(self.phase) != 1:
                raise ValueError("legacy phase strings must contain exactly one character")
            return ord(self.phase)
        if not isinstance(self.phase, int):
            raise TypeError("legacy phase must be an integer or one-character string")
        if not -0x8000_0000 <= self.phase <= 0x7FFF_FFFF:
            raise ValueError("legacy phase must fit in int32")
        return self.phase

    def __post_init__(self) -> None:
        self.phase_value()
        if self.id_type not in {"unscoped", "local", "global"}:
            raise ValueError("id_type must be 'unscoped', 'local', or 'global'")
        for name in ("id", "bind_id"):
            value = getattr(self, name)
            if value is not None and not 0 <= value <= 0xFFFF_FFFF_FFFF_FFFF:
                raise ValueError(f"{name} must fit in uint64")
        for name in (
            "duration_us",
            "thread_duration_us",
            "thread_instruction_delta",
        ):
            value = getattr(self, name)
            if value is not None and not (
                -0x8000_0000_0000_0000 <= value <= 0x7FFF_FFFF_FFFF_FFFF
            ):
                raise ValueError(f"{name} must fit in int64")
        for name in ("pid_override", "tid_override"):
            value = getattr(self, name)
            if value is not None and not -0x8000_0000 <= value <= 0x7FFF_FFFF:
                raise ValueError(f"{name} must fit in int32")
        if self.flow_direction is not None and not 0 <= self.flow_direction <= 3:
            raise ValueError("flow_direction must be an official LegacyEvent value")
        if self.instant_event_scope is not None and not 0 <= self.instant_event_scope <= 3:
            raise ValueError("instant_event_scope must be an official LegacyEvent value")
