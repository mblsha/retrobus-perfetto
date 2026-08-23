"""Helpers for reading traces that use Perfetto incremental interning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional, Tuple

from .interning import SEQ_INCREMENTAL_STATE_CLEARED, SEQ_NEEDS_INCREMENTAL_STATE
from .models import SourceLocation


@dataclass
class _SequenceTables:
    event_categories: Dict[int, str] = field(default_factory=dict)
    event_names: Dict[int, str] = field(default_factory=dict)
    debug_annotation_names: Dict[int, str] = field(default_factory=dict)
    debug_annotation_string_values: Dict[int, bytes] = field(default_factory=dict)
    debug_annotation_value_type_names: Dict[int, str] = field(default_factory=dict)
    source_locations: Dict[int, Any] = field(default_factory=dict)
    build_ids: Dict[int, bytes] = field(default_factory=dict)
    mapping_paths: Dict[int, bytes] = field(default_factory=dict)
    source_paths: Dict[int, bytes] = field(default_factory=dict)
    function_names: Dict[int, bytes] = field(default_factory=dict)
    mappings: Dict[int, Any] = field(default_factory=dict)
    frames: Dict[int, Any] = field(default_factory=dict)
    callstacks: Dict[int, Any] = field(default_factory=dict)
    valid: bool = False

    def clear(self, *, valid: bool) -> None:
        for table in (
            self.event_categories,
            self.event_names,
            self.debug_annotation_names,
            self.debug_annotation_string_values,
            self.debug_annotation_value_type_names,
            self.source_locations,
            self.build_ids,
            self.mapping_paths,
            self.source_paths,
            self.function_names,
            self.mappings,
            self.frames,
            self.callstacks,
        ):
            table.clear()
        self.valid = valid


@dataclass(frozen=True)
class ResolvedMapping:
    """Losslessly resolved executable mapping for a native frame."""

    iid: int
    build_id: Optional[bytes]
    path: Tuple[str, ...]
    exact_offset: Optional[int]
    start_offset: Optional[int]
    start: Optional[int]
    end: Optional[int]
    load_bias: Optional[int]
    complete: bool


@dataclass(frozen=True)
class ResolvedFrame:
    """A resolved frame from an inline or interned TrackEvent callstack."""

    iid: Optional[int]
    function_name: Optional[str]
    mapping: Optional[ResolvedMapping]
    rel_pc: Optional[int]
    source_path: Optional[str]
    line_number: Optional[int]
    kind: Optional[Any]
    complete: bool


@dataclass(frozen=True)
class ResolvedCallstack:
    """A bottom-to-top TrackEvent callstack with all interned references read."""

    iid: Optional[int]
    frames: Tuple[ResolvedFrame, ...]
    complete: bool


@dataclass(frozen=True)
class ResolvedTrackEvent:
    """A TrackEvent plus resolved categories, source location and callstack."""

    packet: Any
    event: Any
    name: Optional[str]
    categories: Tuple[str, ...]
    source_location: Optional[SourceLocation]
    callstack: Optional[ResolvedCallstack]
    incremental_state_valid: bool


def _decode(raw: bytes, encoding: str, errors: str) -> str:
    return raw.decode(encoding, errors=errors)


def _update_tables(packet: Any, tables: _SequenceTables) -> int:
    if packet.previous_packet_dropped:
        tables.clear(valid=False)
    flags = packet.sequence_flags if packet.HasField("sequence_flags") else 0
    if flags & SEQ_INCREMENTAL_STATE_CLEARED:
        tables.clear(valid=True)
    if not packet.HasField("interned_data"):
        return flags

    interned = packet.interned_data
    for entry in interned.event_categories:
        tables.event_categories[entry.iid] = entry.name
    for entry in interned.event_names:
        tables.event_names[entry.iid] = entry.name
    for entry in interned.debug_annotation_names:
        tables.debug_annotation_names[entry.iid] = entry.name
    for entry in interned.debug_annotation_string_values:
        tables.debug_annotation_string_values[entry.iid] = entry.str
    for entry in interned.debug_annotation_value_type_names:
        tables.debug_annotation_value_type_names[entry.iid] = entry.name
    for entry in interned.source_locations:
        tables.source_locations[entry.iid] = entry
    for name in ("build_ids", "mapping_paths", "source_paths", "function_names"):
        table = getattr(tables, name)
        for entry in getattr(interned, name):
            table[entry.iid] = entry.str
    for name in ("mappings", "frames", "callstacks"):
        table = getattr(tables, name)
        for entry in getattr(interned, name):
            table[entry.iid] = entry
    return flags


def _resolve_debug_annotation(
    annotation: Any,
    tables: _SequenceTables,
    *,
    encoding: str,
    errors: str,
) -> None:
    if annotation.HasField("name_iid") and not annotation.HasField("name"):
        annotation.name = tables.debug_annotation_names.get(
            annotation.name_iid,
            f"<missing DebugAnnotationName iid={annotation.name_iid}>",
        )
    if annotation.HasField("string_value_iid") and not annotation.HasField(
        "string_value"
    ):
        raw = tables.debug_annotation_string_values.get(annotation.string_value_iid)
        if raw is None:
            annotation.string_value = (
                f"<missing DebugAnnotationStringValue iid={annotation.string_value_iid}>"
            )
        else:
            annotation.string_value = _decode(raw, encoding, errors)
    if annotation.HasField("proto_type_name_iid") and not annotation.HasField(
        "proto_type_name"
    ):
        annotation.proto_type_name = tables.debug_annotation_value_type_names.get(
            annotation.proto_type_name_iid,
            f"<missing DebugAnnotationValueTypeName iid={annotation.proto_type_name_iid}>",
        )
    for entry in annotation.dict_entries:
        _resolve_debug_annotation(entry, tables, encoding=encoding, errors=errors)
    for entry in annotation.array_values:
        _resolve_debug_annotation(entry, tables, encoding=encoding, errors=errors)


def _resolved_source_location(
    event: Any, tables: _SequenceTables
) -> Optional[SourceLocation]:
    if event.HasField("source_location"):
        location = event.source_location
    elif event.HasField("source_location_iid"):
        location = tables.source_locations.get(event.source_location_iid)
        if location is None:
            return None
    else:
        return None
    return SourceLocation(
        file_name=location.file_name if location.HasField("file_name") else "",
        function_name=(
            location.function_name if location.HasField("function_name") else ""
        ),
        line_number=location.line_number if location.HasField("line_number") else None,
    )


def _resolve_mapping(
    iid: int,
    tables: _SequenceTables,
    *,
    encoding: str,
    errors: str,
) -> Optional[ResolvedMapping]:
    mapping = tables.mappings.get(iid)
    if mapping is None:
        return None
    complete = True
    build_id = None
    if mapping.HasField("build_id"):
        build_id = tables.build_ids.get(mapping.build_id)
        complete = complete and build_id is not None
    path = []
    for path_iid in mapping.path_string_ids:
        raw = tables.mapping_paths.get(path_iid)
        if raw is None:
            complete = False
            path.append(f"<missing MappingPath iid={path_iid}>")
        else:
            path.append(_decode(raw, encoding, errors))

    def optional(name: str) -> Optional[int]:
        return getattr(mapping, name) if mapping.HasField(name) else None

    return ResolvedMapping(
        iid=iid,
        build_id=build_id,
        path=tuple(path),
        exact_offset=optional("exact_offset"),
        start_offset=optional("start_offset"),
        start=optional("start"),
        end=optional("end"),
        load_bias=optional("load_bias"),
        complete=complete,
    )


def _resolve_frame(
    iid: int,
    tables: _SequenceTables,
    *,
    encoding: str,
    errors: str,
) -> ResolvedFrame:
    frame = tables.frames.get(iid)
    if frame is None:
        return ResolvedFrame(iid, None, None, None, None, None, None, False)
    complete = True
    function_name = None
    if frame.HasField("function_name_id"):
        raw = tables.function_names.get(frame.function_name_id)
        complete = complete and raw is not None
        if raw is not None:
            function_name = _decode(raw, encoding, errors)
    mapping = None
    if frame.HasField("mapping_id"):
        mapping = _resolve_mapping(
            frame.mapping_id, tables, encoding=encoding, errors=errors
        )
        complete = complete and mapping is not None and mapping.complete
    source_path = None
    if frame.HasField("source_path_iid"):
        raw = tables.source_paths.get(frame.source_path_iid)
        complete = complete and raw is not None
        if raw is not None:
            source_path = _decode(raw, encoding, errors)
    kind = None
    if frame.HasField("kind"):
        kind = frame.kind
    elif frame.HasField("kind_str"):
        kind = frame.kind_str
    return ResolvedFrame(
        iid=iid,
        function_name=function_name,
        mapping=mapping,
        rel_pc=frame.rel_pc if frame.HasField("rel_pc") else None,
        source_path=source_path,
        line_number=frame.line_number if frame.HasField("line_number") else None,
        kind=kind,
        complete=complete,
    )


def _resolved_callstack(
    event: Any,
    tables: _SequenceTables,
    *,
    encoding: str,
    errors: str,
) -> Optional[ResolvedCallstack]:
    if event.HasField("callstack"):
        frames = tuple(
            ResolvedFrame(
                iid=None,
                function_name=(
                    frame.function_name if frame.HasField("function_name") else None
                ),
                mapping=None,
                rel_pc=None,
                source_path=(
                    frame.source_file if frame.HasField("source_file") else None
                ),
                line_number=(
                    frame.line_number if frame.HasField("line_number") else None
                ),
                kind=None,
                complete=True,
            )
            for frame in event.callstack.frames
        )
        return ResolvedCallstack(None, frames, True)
    if not event.HasField("callstack_iid"):
        return None
    callstack = tables.callstacks.get(event.callstack_iid)
    if callstack is None:
        return ResolvedCallstack(event.callstack_iid, (), False)
    frames = tuple(
        _resolve_frame(iid, tables, encoding=encoding, errors=errors)
        for iid in callstack.frame_ids
    )
    return ResolvedCallstack(
        event.callstack_iid,
        frames,
        all(frame.complete for frame in frames),
    )


def iter_resolved_track_events(
    trace: Any,
    *,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> Iterator[ResolvedTrackEvent]:
    """Yield TrackEvents with losslessly resolved sequence-scoped metadata."""
    tables_by_sequence: Dict[int, _SequenceTables] = {}
    for packet in trace.packet:
        sequence_id = (
            packet.trusted_packet_sequence_id
            if packet.HasField("trusted_packet_sequence_id")
            else 0
        )
        tables = tables_by_sequence.setdefault(sequence_id, _SequenceTables())
        flags = _update_tables(packet, tables)
        if not packet.HasField("track_event"):
            continue
        event = packet.track_event
        state_valid = not (flags & SEQ_NEEDS_INCREMENTAL_STATE) or tables.valid
        categories = list(event.categories)
        for iid in event.category_iids:
            categories.append(
                tables.event_categories.get(iid, f"<missing EventCategory iid={iid}>")
            )
        name = event.name if event.HasField("name") else None
        if name is None and event.HasField("name_iid") and state_valid:
            name = tables.event_names.get(
                event.name_iid, f"<missing EventName iid={event.name_iid}>"
            )
        yield ResolvedTrackEvent(
            packet=packet,
            event=event,
            name=name,
            categories=tuple(categories),
            source_location=(
                _resolved_source_location(event, tables) if state_valid else None
            ),
            callstack=(
                _resolved_callstack(event, tables, encoding=encoding, errors=errors)
                if state_valid
                else None
            ),
            incremental_state_valid=state_valid,
        )


def resolve_interned_trace(
    trace: Any,
    *,
    inplace: bool = False,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> Any:
    """Rewrite string-like IIDs to their inline counterparts.

    Native callstack_iid values intentionally remain interned because the
    inline callstack cannot represent mappings, build IDs, or relative PCs.
    Use iter_resolved_track_events for lossless callstack resolution.
    """
    if not inplace:
        resolved = trace.__class__()
        resolved.CopyFrom(trace)
        trace = resolved

    tables_by_sequence: Dict[int, _SequenceTables] = {}
    for packet in trace.packet:
        sequence_id = (
            packet.trusted_packet_sequence_id
            if packet.HasField("trusted_packet_sequence_id")
            else 0
        )
        tables = tables_by_sequence.setdefault(sequence_id, _SequenceTables())
        flags = _update_tables(packet, tables)
        if not packet.HasField("track_event"):
            continue
        event = packet.track_event
        if flags & SEQ_NEEDS_INCREMENTAL_STATE and not tables.valid:
            continue

        if event.HasField("name_iid") and not event.HasField("name"):
            event.name = tables.event_names.get(
                event.name_iid, f"<missing EventName iid={event.name_iid}>"
            )
        if event.category_iids:
            event.categories.extend(
                tables.event_categories.get(
                    iid, f"<missing EventCategory iid={iid}>"
                )
                for iid in event.category_iids
            )
            del event.category_iids[:]
        if event.HasField("source_location_iid"):
            location = tables.source_locations.get(event.source_location_iid)
            if location is not None:
                event.source_location.CopyFrom(location)
        for annotation in event.debug_annotations:
            _resolve_debug_annotation(
                annotation, tables, encoding=encoding, errors=errors
            )
    return trace
