"""Writer-side state for Perfetto string interning.

Perfetto interning is incremental and scoped per trusted packet sequence ID.
This helper keeps small per-table string -> IID maps and emits new dictionary
entries into TracePacket.interned_data as strings are first encountered.
"""

from __future__ import annotations

from typing import Dict

# Keep these values in sync with TracePacket.SequenceFlags in proto/perfetto.proto.
SEQ_INCREMENTAL_STATE_CLEARED = 1
SEQ_NEEDS_INCREMENTAL_STATE = 2


class InterningState:
    """Maps strings to IIDs and emits interned dictionary entries."""

    def __init__(self) -> None:
        self._event_names: Dict[str, int] = {}
        self._debug_annotation_names: Dict[str, int] = {}
        self._debug_annotation_string_values: Dict[str, int] = {}

        self._next_event_name_iid = 1
        self._next_debug_annotation_name_iid = 1
        self._next_debug_annotation_string_value_iid = 1

        self._emitted_incremental_state_cleared = False

    def reset(self) -> None:
        """Clear all tables and start a new incremental-state generation.

        IID counters are intentionally not reset to avoid reusing IIDs for
        different values.
        """
        self._event_names.clear()
        self._debug_annotation_names.clear()
        self._debug_annotation_string_values.clear()
        self._emitted_incremental_state_cleared = False

    def _mark_incremental_state_needed(self, packet) -> None:
        existing_flags = getattr(packet, "sequence_flags", 0)
        flags = existing_flags | SEQ_NEEDS_INCREMENTAL_STATE
        if not self._emitted_incremental_state_cleared:
            flags |= SEQ_INCREMENTAL_STATE_CLEARED
            self._emitted_incremental_state_cleared = True
        packet.sequence_flags = flags

    def intern_event_name(self, name: str, packet) -> int:
        """Intern a TrackEvent name into InternedData.event_names."""
        self._mark_incremental_state_needed(packet)
        existing = self._event_names.get(name)
        if existing is not None:
            return existing

        iid = self._next_event_name_iid
        self._next_event_name_iid += 1
        self._event_names[name] = iid

        entry = packet.interned_data.event_names.add()
        entry.iid = iid
        entry.name = name
        return iid

    def intern_debug_annotation_name(self, name: str, packet) -> int:
        """Intern a DebugAnnotation name into InternedData.debug_annotation_names."""
        self._mark_incremental_state_needed(packet)
        existing = self._debug_annotation_names.get(name)
        if existing is not None:
            return existing

        iid = self._next_debug_annotation_name_iid
        self._next_debug_annotation_name_iid += 1
        self._debug_annotation_names[name] = iid

        entry = packet.interned_data.debug_annotation_names.add()
        entry.iid = iid
        entry.name = name
        return iid

    def intern_debug_annotation_string_value(
        self, value: str, packet, *, encoding: str = "utf-8"
    ) -> int:
        """Intern a DebugAnnotation string value into InternedData.debug_annotation_string_values."""
        self._mark_incremental_state_needed(packet)
        existing = self._debug_annotation_string_values.get(value)
        if existing is not None:
            return existing

        iid = self._next_debug_annotation_string_value_iid
        self._next_debug_annotation_string_value_iid += 1
        self._debug_annotation_string_values[value] = iid

        entry = packet.interned_data.debug_annotation_string_values.add()
        entry.iid = iid
        entry.str = value.encode(encoding, errors="replace")
        return iid
