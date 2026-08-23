"""Writer-side state for Perfetto string interning.

Perfetto interning is incremental and scoped per trusted packet sequence ID.
This helper keeps small per-table string -> IID maps and emits new dictionary
entries into TracePacket.interned_data as strings are first encountered.
"""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

from .models import SourceLocation, StackFrame, StackMapping

# Keep these values in sync with TracePacket.SequenceFlags in proto/perfetto.proto.
SEQ_INCREMENTAL_STATE_CLEARED = 1
SEQ_NEEDS_INCREMENTAL_STATE = 2


class InterningState:
    """Maps strings to IIDs and emits interned dictionary entries."""

    def __init__(self) -> None:
        self._event_categories: Dict[str, int] = {}
        self._event_names: Dict[str, int] = {}
        self._debug_annotation_names: Dict[str, int] = {}
        self._debug_annotation_string_values: Dict[str, int] = {}
        self._debug_annotation_value_type_names: Dict[str, int] = {}
        self._source_locations: Dict[SourceLocation, int] = {}
        self._build_ids: Dict[bytes, int] = {}
        self._mapping_paths: Dict[bytes, int] = {}
        self._source_paths: Dict[bytes, int] = {}
        self._function_names: Dict[bytes, int] = {}
        self._mappings: Dict[StackMapping, int] = {}
        self._frames: Dict[StackFrame, int] = {}
        self._callstacks: Dict[Tuple[int, ...], int] = {}

        self._next_event_category_iid = 1
        self._next_event_name_iid = 1
        self._next_debug_annotation_name_iid = 1
        self._next_debug_annotation_string_value_iid = 1
        self._next_debug_annotation_value_type_name_iid = 1
        self._next_source_location_iid = 1
        self._next_build_id_iid = 1
        self._next_mapping_path_iid = 1
        self._next_source_path_iid = 1
        self._next_function_name_iid = 1
        self._next_mapping_iid = 1
        self._next_frame_iid = 1
        self._next_callstack_iid = 1

        self._emitted_incremental_state_cleared = False

    def reset(self) -> None:
        """Clear all tables and start a new incremental-state generation.

        IID counters are intentionally not reset to avoid reusing IIDs for
        different values.
        """
        for table in (
            self._event_categories,
            self._event_names,
            self._debug_annotation_names,
            self._debug_annotation_string_values,
            self._debug_annotation_value_type_names,
            self._source_locations,
            self._build_ids,
            self._mapping_paths,
            self._source_paths,
            self._function_names,
            self._mappings,
            self._frames,
            self._callstacks,
        ):
            table.clear()
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

    def intern_event_category(self, name: str, packet) -> int:
        """Intern a TrackEvent category into InternedData.event_categories."""
        self._mark_incremental_state_needed(packet)
        existing = self._event_categories.get(name)
        if existing is not None:
            return existing

        iid = self._next_event_category_iid
        self._next_event_category_iid += 1
        self._event_categories[name] = iid

        entry = packet.interned_data.event_categories.add()
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

    def intern_debug_annotation_value_type_name(self, name: str, packet) -> int:
        """Intern the full name of an embedded DebugAnnotation proto."""
        self._mark_incremental_state_needed(packet)
        existing = self._debug_annotation_value_type_names.get(name)
        if existing is not None:
            return existing

        iid = self._next_debug_annotation_value_type_name_iid
        self._next_debug_annotation_value_type_name_iid += 1
        self._debug_annotation_value_type_names[name] = iid
        entry = packet.interned_data.debug_annotation_value_type_names.add()
        entry.iid = iid
        entry.name = name
        return iid

    def intern_source_location(self, location: SourceLocation, packet) -> int:
        """Intern a TrackEvent source location."""
        self._mark_incremental_state_needed(packet)
        existing = self._source_locations.get(location)
        if existing is not None:
            return existing

        iid = self._next_source_location_iid
        self._next_source_location_iid += 1
        self._source_locations[location] = iid
        entry = packet.interned_data.source_locations.add()
        entry.iid = iid
        if location.file_name:
            entry.file_name = location.file_name
        if location.function_name:
            entry.function_name = location.function_name
        if location.line_number is not None:
            entry.line_number = location.line_number
        return iid

    def _intern_bytes(
        self,
        value: bytes,
        packet,
        *,
        table: Dict[bytes, int],
        counter_name: str,
        repeated_name: str,
    ) -> int:
        self._mark_incremental_state_needed(packet)
        existing = table.get(value)
        if existing is not None:
            return existing
        iid = getattr(self, counter_name)
        setattr(self, counter_name, iid + 1)
        table[value] = iid
        entry = getattr(packet.interned_data, repeated_name).add()
        entry.iid = iid
        entry.str = value
        return iid

    def intern_build_id(self, value: bytes, packet) -> int:
        """Intern raw executable build-ID bytes."""
        return self._intern_bytes(
            value,
            packet,
            table=self._build_ids,
            counter_name="_next_build_id_iid",
            repeated_name="build_ids",
        )

    def intern_mapping_path(self, value: str, packet) -> int:
        """Intern one executable path component."""
        return self._intern_bytes(
            value.encode("utf-8"),
            packet,
            table=self._mapping_paths,
            counter_name="_next_mapping_path_iid",
            repeated_name="mapping_paths",
        )

    def intern_source_path(self, value: str, packet) -> int:
        """Intern a source file path."""
        return self._intern_bytes(
            value.encode("utf-8"),
            packet,
            table=self._source_paths,
            counter_name="_next_source_path_iid",
            repeated_name="source_paths",
        )

    def intern_function_name(self, value: str, packet) -> int:
        """Intern a symbolized function name."""
        return self._intern_bytes(
            value.encode("utf-8"),
            packet,
            table=self._function_names,
            counter_name="_next_function_name_iid",
            repeated_name="function_names",
        )

    def intern_mapping(self, mapping: StackMapping, packet) -> int:
        """Intern an executable mapping and its strings."""
        self._mark_incremental_state_needed(packet)
        existing = self._mappings.get(mapping)
        if existing is not None:
            return existing

        iid = self._next_mapping_iid
        self._next_mapping_iid += 1
        self._mappings[mapping] = iid
        entry = packet.interned_data.mappings.add()
        entry.iid = iid
        if mapping.build_id is not None:
            build_id = (
                mapping.build_id.encode("utf-8")
                if isinstance(mapping.build_id, str)
                else mapping.build_id
            )
            entry.build_id = self.intern_build_id(build_id, packet)
        for component in mapping.path:
            entry.path_string_ids.append(self.intern_mapping_path(component, packet))
        for name in (
            "exact_offset",
            "start_offset",
            "start",
            "end",
            "load_bias",
        ):
            value = getattr(mapping, name)
            if value is not None:
                setattr(entry, name, value)
        return iid

    def intern_frame(self, frame: StackFrame, packet) -> int:
        """Intern one native stack frame and all of its dependencies."""
        self._mark_incremental_state_needed(packet)
        existing = self._frames.get(frame)
        if existing is not None:
            return existing

        iid = self._next_frame_iid
        self._next_frame_iid += 1
        self._frames[frame] = iid
        entry = packet.interned_data.frames.add()
        entry.iid = iid
        if frame.function_name is not None:
            entry.function_name_id = self.intern_function_name(
                frame.function_name, packet
            )
        if frame.mapping is not None:
            entry.mapping_id = self.intern_mapping(frame.mapping, packet)
        if frame.rel_pc is not None:
            entry.rel_pc = frame.rel_pc
        if frame.source_path is not None:
            entry.source_path_iid = self.intern_source_path(frame.source_path, packet)
        if frame.line_number is not None:
            entry.line_number = frame.line_number
        if isinstance(frame.kind, str):
            entry.kind_str = frame.kind
        elif frame.kind is not None:
            entry.kind = frame.kind
        return iid

    def intern_callstack(self, frames: Sequence[StackFrame], packet) -> int:
        """Intern a bottom-to-top native callstack."""
        frame_iids = tuple(self.intern_frame(frame, packet) for frame in frames)
        self._mark_incremental_state_needed(packet)
        existing = self._callstacks.get(frame_iids)
        if existing is not None:
            return existing

        iid = self._next_callstack_iid
        self._next_callstack_iid += 1
        self._callstacks[frame_iids] = iid
        entry = packet.interned_data.callstacks.add()
        entry.iid = iid
        entry.frame_ids.extend(frame_iids)
        return iid
