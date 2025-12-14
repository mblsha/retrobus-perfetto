"""Helpers for reading traces that use Perfetto string interning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .interning import SEQ_INCREMENTAL_STATE_CLEARED, SEQ_NEEDS_INCREMENTAL_STATE


@dataclass
class _SequenceTables:
    event_names: Dict[int, str] = field(default_factory=dict)
    debug_annotation_names: Dict[int, str] = field(default_factory=dict)
    debug_annotation_string_values: Dict[int, bytes] = field(default_factory=dict)
    valid: bool = False


def _resolve_debug_annotation(
    annotation,
    tables: _SequenceTables,
    *,
    encoding: str,
    errors: str,
) -> None:
    if annotation.HasField("name_iid") and not annotation.HasField("name"):
        annotation.name = tables.debug_annotation_names.get(
            annotation.name_iid, f"<missing DebugAnnotationName iid={annotation.name_iid}>"
        )

    if annotation.HasField("string_value_iid") and not annotation.HasField("string_value"):
        raw = tables.debug_annotation_string_values.get(annotation.string_value_iid)
        if raw is None:
            annotation.string_value = (
                f"<missing DebugAnnotationStringValue iid={annotation.string_value_iid}>"
            )
        else:
            annotation.string_value = raw.decode(encoding, errors=errors)

    for entry in annotation.dict_entries:
        _resolve_debug_annotation(entry, tables, encoding=encoding, errors=errors)
    for entry in annotation.array_values:
        _resolve_debug_annotation(entry, tables, encoding=encoding, errors=errors)


def resolve_interned_trace(
    trace: Any,
    *,
    inplace: bool = False,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> Any:
    """Resolve interned IDs to strings.

    This is intended for debugging/diff tooling: it rewrites *_iid oneofs
    (TrackEvent.name_iid, DebugAnnotation.name_iid, DebugAnnotation.string_value_iid)
    into their string counterparts so existing code that expects inline strings
    keeps working.
    """
    if not inplace:
        resolved = trace.__class__()
        resolved.CopyFrom(trace)
        trace = resolved

    tables_by_sequence: Dict[int, _SequenceTables] = {}

    for packet in trace.packet:
        seq_id = packet.trusted_packet_sequence_id if packet.HasField("trusted_packet_sequence_id") else 0
        tables = tables_by_sequence.setdefault(seq_id, _SequenceTables())

        if packet.previous_packet_dropped:
            tables.valid = False
            tables.event_names.clear()
            tables.debug_annotation_names.clear()
            tables.debug_annotation_string_values.clear()

        flags = packet.sequence_flags if packet.HasField("sequence_flags") else 0
        if flags & SEQ_INCREMENTAL_STATE_CLEARED:
            tables.valid = True
            tables.event_names.clear()
            tables.debug_annotation_names.clear()
            tables.debug_annotation_string_values.clear()

        if packet.HasField("interned_data"):
            for entry in packet.interned_data.event_names:
                tables.event_names[entry.iid] = entry.name
            for entry in packet.interned_data.debug_annotation_names:
                tables.debug_annotation_names[entry.iid] = entry.name
            for entry in packet.interned_data.debug_annotation_string_values:
                tables.debug_annotation_string_values[entry.iid] = entry.str

        if not packet.HasField("track_event"):
            continue

        event = packet.track_event
        needs_state = bool(flags & SEQ_NEEDS_INCREMENTAL_STATE)
        if needs_state and not tables.valid:
            continue

        if event.HasField("name_iid") and not event.HasField("name"):
            event.name = tables.event_names.get(event.name_iid, f"<missing EventName iid={event.name_iid}>")

        for ann in event.debug_annotations:
            _resolve_debug_annotation(ann, tables, encoding=encoding, errors=errors)

    return trace
