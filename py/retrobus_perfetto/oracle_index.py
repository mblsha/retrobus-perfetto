"""Streaming Perfetto trace indexing and parity-oracle export helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Dict, Iterable, Iterator, Mapping, Sequence

from .proto import perfetto_pb2

perfetto: Any = perfetto_pb2


REGISTER_NAMES = (
    "eax",
    "ebx",
    "ecx",
    "edx",
    "esi",
    "edi",
    "ebp",
    "esp",
    "eip",
    "eflags",
    "cs",
    "ds",
    "es",
    "fs",
    "gs",
    "ss",
)
FUNCTION_ADDRESS_KEYS = (
    "function_addr",
    "bnida_symbol_addr",
    "function_address",
    "entry_eip",
    "function_eip",
    "function_linear",
    "probe_target",
    "target_eip",
    "address",
)
CALLSITE_ADDRESS_KEYS = (
    "callsite",
    "source_eip",
    "probe_callsite",
    "callsite_eip",
    "callsite_linear",
    "caller_eip",
)
RETURN_ADDRESS_KEYS = (
    "return_eip",
    "exit_eip",
    "eip",
)
TEMPORAL_SEQUENCE_KEYS = (
    "temporal_seq",
    "temporal_sequence",
    "sequence",
    "idx",
)
FRAME_INDEX_KEYS = (
    "frame_index",
    "frame",
)
VSYNC_KEYS = (
    "vsync_counter",
    "vsync",
    "frame_counter",
)
CALL_ID_KEYS = ("call_id",)
ENTER_INDEX_KEYS = ("enter_idx", "entry_index")
SIDE_EFFECT_KEYS = (
    "declared_side_effects",
    "side_effect_regions",
    "side_effects",
    "side_effect",
)
TRACK_EVENT_TYPE_NAMES = {
    perfetto.TrackEvent.TYPE_SLICE_BEGIN: "slice_begin",
    perfetto.TrackEvent.TYPE_SLICE_END: "slice_end",
    perfetto.TrackEvent.TYPE_INSTANT: "instant",
    perfetto.TrackEvent.TYPE_COUNTER: "counter",
}
CALL_EVENT_KINDS = frozenset(("call_enter", "call_exit", "synthetic_chunk_reopen"))
LEGACY_CALL_TRACK_NAMES = frozenset(("function execution",))
FRAME_EVENT_TYPE_NAMES = (
    ("expected_surface_frame_start", "expected_surface_frame_start"),
    ("actual_surface_frame_start", "actual_surface_frame_start"),
    ("expected_display_frame_start", "expected_display_frame_start"),
    ("actual_display_frame_start", "actual_display_frame_start"),
    ("frame_end", "frame_end"),
)


@dataclass(frozen=True)
class IndexStats:
    index_path: Path
    source_count: int
    packet_count: int
    track_event_count: int
    frame_event_count: int


@dataclass(frozen=True)
class VerifyStats:
    index_path: Path
    invocation_count: int
    issue_count: int
    missing_exit_count: int
    in_flight_count: int


@dataclass
class _SequenceTables:
    event_categories: Dict[int, str] = field(default_factory=dict)
    event_names: Dict[int, str] = field(default_factory=dict)
    debug_annotation_names: Dict[int, str] = field(default_factory=dict)
    debug_annotation_string_values: Dict[int, str] = field(default_factory=dict)
    source_locations: Dict[int, Any] = field(default_factory=dict)
    build_ids: Dict[int, bytes] = field(default_factory=dict)
    mapping_paths: Dict[int, str] = field(default_factory=dict)
    source_paths: Dict[int, str] = field(default_factory=dict)
    function_names: Dict[int, str] = field(default_factory=dict)
    mappings: Dict[int, Any] = field(default_factory=dict)
    frames: Dict[int, Any] = field(default_factory=dict)
    callstacks: Dict[int, Any] = field(default_factory=dict)
    valid: bool = False


@dataclass(frozen=True)
class TracePacketRecord:
    """A streamed TracePacket and its source-file provenance."""

    source_id: int
    source_path: Path
    source_packet_ordinal: int
    offset: int
    payload_size: int
    packet: Any


@dataclass
class _DerivedScalar:
    value: Any
    key: str | None


@dataclass
class _OpenInvocation:
    track_uuid: str
    track_name: str
    entry_source_id: int
    function_name: str
    function_base_name: str
    entry_event_id: int
    entry_packet_id: int
    entry_global_packet_ordinal: int
    entry_timestamp_ns: int | None
    entry_annotations: dict[str, Any]
    entry_annotations_provenance: Any
    entry_registers: dict[str, Any]
    function_address: _DerivedScalar
    callsite_address: _DerivedScalar
    entry_sequence: _DerivedScalar
    frame_index: _DerivedScalar
    seen_frame_counter: _DerivedScalar
    vsync_counter: _DerivedScalar
    side_effects: _DerivedScalar
    call_id: _DerivedScalar
    enter_index: _DerivedScalar
    function_name_key: str | None
    trace_provenance: dict[str, Any]
    is_real_entry: bool = True
    synthetic_close_event_ids: list[int] = field(default_factory=list)
    synthetic_reopen_event_ids: list[int] = field(default_factory=list)
    exit_event_id: int | None = None
    exit_source_id: int | None = None
    exit_packet_id: int | None = None
    exit_global_packet_ordinal: int | None = None
    exit_timestamp_ns: int | None = None
    exit_annotations: dict[str, Any] | None = None
    exit_annotations_provenance: Any = None
    exit_registers: dict[str, Any] | None = None
    exit_sequence: _DerivedScalar = field(default_factory=lambda: _DerivedScalar(None, None))
    return_address: _DerivedScalar = field(default_factory=lambda: _DerivedScalar(None, None))
    exit_eflags: _DerivedScalar = field(default_factory=lambda: _DerivedScalar(None, None))
    exit_eip: _DerivedScalar = field(default_factory=lambda: _DerivedScalar(None, None))
    terminal_close_event_id: int | None = None
    terminal_close_source_id: int | None = None
    terminal_close_packet_id: int | None = None
    terminal_close_timestamp_ns: int | None = None


def _json_dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _opaque_u64(value: int | None) -> str | None:
    if value is None:
        return None
    if value < 0 or value > 0xFFFF_FFFF_FFFF_FFFF:
        raise ValueError(f"value is outside uint64 range: {value}")
    return str(value)


def _parse_opaque_u64(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    raise ValueError(f"invalid uint64 database value: {value!r}")


def _sqlite_int64(value: int | None) -> int | None:
    """Store an unsigned 64-bit bit pattern in SQLite's signed INTEGER."""
    if value is None:
        return None
    if -(1 << 63) <= value < (1 << 63):
        return value
    if 0 <= value <= 0xFFFF_FFFF_FFFF_FFFF:
        return value - (1 << 64)
    raise ValueError(f"integer is outside SQLite/uint64 range: {value}")


def _unsigned_from_sqlite(value: int | None) -> int | None:
    if value is None or value >= 0:
        return value
    return value + (1 << 64)


def _connect_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE sources (
            source_id INTEGER PRIMARY KEY,
            ordinal INTEGER NOT NULL,
            path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL
        );

        CREATE TABLE packets (
            packet_id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            source_packet_ordinal INTEGER NOT NULL,
            global_packet_ordinal INTEGER NOT NULL,
            file_offset INTEGER NOT NULL,
            payload_size INTEGER NOT NULL,
            timestamp_ns INTEGER,
            sequence_id INTEGER,
            sequence_flags INTEGER NOT NULL,
            previous_packet_dropped INTEGER NOT NULL,
            first_packet_on_sequence INTEGER NOT NULL,
            incremental_state_valid INTEGER NOT NULL,
            packet_kind TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES sources(source_id)
        );
        CREATE INDEX idx_packets_global_packet_ordinal
            ON packets(global_packet_ordinal);

        CREATE TABLE tracks (
            track_uuid TEXT PRIMARY KEY,
            parent_uuid TEXT,
            name TEXT NOT NULL,
            descriptor_kind TEXT NOT NULL,
            descriptor_json TEXT NOT NULL,
            first_packet_id INTEGER NOT NULL,
            last_packet_id INTEGER NOT NULL
        );

        CREATE TABLE track_events (
            event_id INTEGER PRIMARY KEY,
            packet_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            global_packet_ordinal INTEGER NOT NULL,
            sequence_id INTEGER,
            track_uuid TEXT NOT NULL,
            track_name TEXT NOT NULL,
            event_type INTEGER NOT NULL,
            event_type_name TEXT NOT NULL,
            event_name TEXT NOT NULL,
            categories_json TEXT NOT NULL,
            function_base_name TEXT NOT NULL,
            timestamp_ns INTEGER,
            event_kind TEXT,
            is_synthetic_reopen INTEGER NOT NULL,
            is_exit_probe INTEGER NOT NULL,
            temporal_sequence INTEGER,
            frame_index INTEGER,
            seen_frame_counter INTEGER,
            vsync_counter INTEGER,
            function_address INTEGER,
            callsite_address INTEGER,
            return_address INTEGER,
            call_id TEXT,
            enter_index TEXT,
            annotations_json TEXT NOT NULL,
            annotations_provenance_json TEXT NOT NULL,
            derived_provenance_json TEXT NOT NULL,
            registers_json TEXT NOT NULL,
            side_effects_json TEXT,
            source_location_json TEXT,
            callstack_json TEXT,
            has_unresolved_interning INTEGER NOT NULL,
            FOREIGN KEY(packet_id) REFERENCES packets(packet_id),
            FOREIGN KEY(source_id) REFERENCES sources(source_id)
        );
        CREATE INDEX idx_track_events_global_packet_ordinal
            ON track_events(global_packet_ordinal);
        CREATE INDEX idx_track_events_track_uuid_ordinal
            ON track_events(track_uuid, global_packet_ordinal);

        CREATE TABLE frame_events (
            frame_event_id INTEGER PRIMARY KEY,
            packet_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            global_packet_ordinal INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            timestamp_ns INTEGER,
            cookie INTEGER,
            token INTEGER,
            display_frame_token INTEGER,
            pid INTEGER,
            layer_name TEXT,
            payload_json TEXT NOT NULL,
            FOREIGN KEY(packet_id) REFERENCES packets(packet_id),
            FOREIGN KEY(source_id) REFERENCES sources(source_id)
        );
        CREATE INDEX idx_frame_events_global_packet_ordinal
            ON frame_events(global_packet_ordinal);

        CREATE TABLE verification_issues (
            issue_id INTEGER PRIMARY KEY,
            severity TEXT NOT NULL,
            code TEXT NOT NULL,
            packet_id INTEGER,
            event_id INTEGER,
            invocation_id INTEGER,
            message TEXT NOT NULL,
            details_json TEXT NOT NULL
        );

        CREATE TABLE oracle_invocations (
            invocation_id INTEGER PRIMARY KEY,
            track_uuid TEXT NOT NULL,
            track_name TEXT NOT NULL,
            entry_source_id INTEGER NOT NULL,
            exit_source_id INTEGER,
            terminal_close_source_id INTEGER,
            entry_event_id INTEGER NOT NULL,
            exit_event_id INTEGER,
            terminal_close_event_id INTEGER,
            function_name TEXT NOT NULL,
            function_base_name TEXT NOT NULL,
            function_address INTEGER,
            callsite_address INTEGER,
            return_address INTEGER,
            call_id TEXT,
            enter_index TEXT,
            entry_timestamp_ns INTEGER,
            exit_timestamp_ns INTEGER,
            terminal_close_timestamp_ns INTEGER,
            entry_sequence INTEGER,
            exit_sequence INTEGER,
            entry_global_packet_ordinal INTEGER NOT NULL,
            exit_global_packet_ordinal INTEGER,
            frame_index INTEGER,
            seen_frame_counter INTEGER,
            vsync_counter INTEGER,
            synthetic_close_count INTEGER NOT NULL,
            synthetic_reopen_count INTEGER NOT NULL,
            terminal_close_kind TEXT NOT NULL,
            entry_registers_json TEXT NOT NULL,
            exit_registers_json TEXT,
            exit_eflags INTEGER,
            exit_eip INTEGER,
            side_effects_json TEXT,
            entry_annotations_json TEXT NOT NULL,
            entry_annotations_provenance_json TEXT NOT NULL,
            exit_annotations_json TEXT,
            exit_annotations_provenance_json TEXT,
            provenance_json TEXT NOT NULL
        );
        CREATE INDEX idx_oracle_invocations_entry_sequence
            ON oracle_invocations(entry_sequence);
        """
    )


def _read_varint(handle: Any) -> int | None:
    shift = 0
    value = 0
    while True:
        chunk = handle.read(1)
        if not chunk:
            if shift == 0:
                return None
            raise ValueError("truncated varint")
        byte = chunk[0]
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value
        shift += 7
        if shift > 63:
            raise ValueError("varint exceeds 64 bits")


def _require_lastrowid(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise ValueError("sqlite cursor did not expose lastrowid")
    return int(cursor.lastrowid)


def iter_trace_packets(trace_paths: Sequence[Path | str]) -> Iterator[TracePacketRecord]:
    """Yield TracePacket messages without parsing the whole Trace wrapper."""
    for source_id, trace_path_value in enumerate(trace_paths, start=1):
        trace_path = Path(trace_path_value)
        packet_ordinal = 0
        with trace_path.open("rb") as handle:
            trace_size = os.fstat(handle.fileno()).st_size
            while True:
                offset = handle.tell()
                tag = _read_varint(handle)
                if tag is None:
                    break
                if tag != 10:
                    raise ValueError(
                        f"{trace_path}: expected Trace.packet field tag 10 at byte {offset}, got {tag}"
                    )
                payload_size = _read_varint(handle)
                if payload_size is None:
                    raise ValueError(f"{trace_path}: truncated packet length at byte {offset}")
                remaining = trace_size - handle.tell()
                if payload_size > remaining:
                    raise ValueError(
                        f"{trace_path}: TracePacket at byte {offset} declares {payload_size} "
                        f"bytes with only {remaining} remaining"
                    )
                payload = handle.read(payload_size)
                if len(payload) != payload_size:
                    raise ValueError(
                        f"{trace_path}: truncated TracePacket payload at byte {offset}"
                    )
                packet = perfetto.TracePacket()
                packet.ParseFromString(payload)
                yield TracePacketRecord(
                    source_id=source_id,
                    source_path=trace_path,
                    source_packet_ordinal=packet_ordinal,
                    offset=offset,
                    payload_size=payload_size,
                    packet=packet,
                )
                packet_ordinal += 1


def _sequence_tables_for_packet(
    packet: Any,
    tables_by_sequence: dict[int, _SequenceTables],
) -> tuple[_SequenceTables, int, int]:
    sequence_id = packet.trusted_packet_sequence_id if packet.HasField("trusted_packet_sequence_id") else 0
    tables = tables_by_sequence.setdefault(sequence_id, _SequenceTables())
    flags = packet.sequence_flags if packet.HasField("sequence_flags") else 0

    if packet.previous_packet_dropped:
        tables.valid = False
        tables.event_categories.clear()
        tables.event_names.clear()
        tables.debug_annotation_names.clear()
        tables.debug_annotation_string_values.clear()
        tables.source_locations.clear()
        tables.build_ids.clear()
        tables.mapping_paths.clear()
        tables.source_paths.clear()
        tables.function_names.clear()
        tables.mappings.clear()
        tables.frames.clear()
        tables.callstacks.clear()

    if flags & perfetto.TracePacket.SEQ_INCREMENTAL_STATE_CLEARED:
        tables.valid = True
        tables.event_categories.clear()
        tables.event_names.clear()
        tables.debug_annotation_names.clear()
        tables.debug_annotation_string_values.clear()
        tables.source_locations.clear()
        tables.build_ids.clear()
        tables.mapping_paths.clear()
        tables.source_paths.clear()
        tables.function_names.clear()
        tables.mappings.clear()
        tables.frames.clear()
        tables.callstacks.clear()

    if packet.HasField("interned_data"):
        for entry in packet.interned_data.event_categories:
            tables.event_categories[entry.iid] = entry.name
        for entry in packet.interned_data.event_names:
            tables.event_names[entry.iid] = entry.name
        for entry in packet.interned_data.debug_annotation_names:
            tables.debug_annotation_names[entry.iid] = entry.name
        for entry in packet.interned_data.debug_annotation_string_values:
            tables.debug_annotation_string_values[entry.iid] = entry.str.decode(
                "utf-8", errors="replace"
            )
        for entry in packet.interned_data.source_locations:
            tables.source_locations[entry.iid] = entry
        for entry in packet.interned_data.build_ids:
            tables.build_ids[entry.iid] = entry.str
        for name in ("mapping_paths", "source_paths", "function_names"):
            table = getattr(tables, name)
            for entry in getattr(packet.interned_data, name):
                table[entry.iid] = entry.str.decode("utf-8", errors="replace")
        for name in ("mappings", "frames", "callstacks"):
            table = getattr(tables, name)
            for entry in getattr(packet.interned_data, name):
                table[entry.iid] = entry

    return tables, sequence_id, flags


def _annotation_name(annotation: Any, tables: _SequenceTables) -> tuple[str, dict[str, Any]]:
    if annotation.HasField("name"):
        return annotation.name, {"name_source": "inline"}
    if annotation.HasField("name_iid"):
        return (
            tables.debug_annotation_names.get(
                annotation.name_iid,
                f"<missing DebugAnnotationName iid={annotation.name_iid}>",
            ),
            {"name_source": "iid", "name_iid": annotation.name_iid},
        )
    return "", {"name_source": "missing"}


def _merge_annotation_value(target: dict[str, Any], key: str, value: Any) -> None:
    if key not in target:
        target[key] = value
        return
    current = target[key]
    if isinstance(current, list):
        current.append(value)
        return
    target[key] = [current, value]


def _annotation_value(annotation: Any, tables: _SequenceTables) -> tuple[Any, dict[str, Any]]:
    if annotation.dict_entries:
        obj: dict[str, Any] = {}
        provenance_entries: list[dict[str, Any]] = []
        for entry in annotation.dict_entries:
            name, name_provenance = _annotation_name(entry, tables)
            value, value_provenance = _annotation_value(entry, tables)
            _merge_annotation_value(obj, name, value)
            provenance_entries.append(
                {
                    "name": name,
                    **name_provenance,
                    **value_provenance,
                }
            )
        return obj, {"value_kind": "dict", "entries": provenance_entries}

    if annotation.array_values:
        values: list[Any] = []
        provenance_values: list[dict[str, Any]] = []
        for entry in annotation.array_values:
            value, value_provenance = _annotation_value(entry, tables)
            values.append(value)
            provenance_values.append(value_provenance)
        return values, {"value_kind": "array", "items": provenance_values}

    if annotation.HasField("bool_value"):
        return annotation.bool_value, {"value_kind": "bool", "value_source": "inline"}
    if annotation.HasField("uint_value"):
        return annotation.uint_value, {"value_kind": "uint", "value_source": "inline"}
    if annotation.HasField("int_value"):
        return annotation.int_value, {"value_kind": "int", "value_source": "inline"}
    if annotation.HasField("double_value"):
        return annotation.double_value, {"value_kind": "double", "value_source": "inline"}
    if annotation.HasField("pointer_value"):
        return annotation.pointer_value, {"value_kind": "pointer", "value_source": "inline"}
    if annotation.HasField("legacy_json_value"):
        return annotation.legacy_json_value, {
            "value_kind": "legacy_json",
            "value_source": "inline",
        }
    if annotation.HasField("string_value"):
        return annotation.string_value, {"value_kind": "string", "value_source": "inline"}
    if annotation.HasField("string_value_iid"):
        return (
            tables.debug_annotation_string_values.get(
                annotation.string_value_iid,
                f"<missing DebugAnnotationStringValue iid={annotation.string_value_iid}>",
            ),
            {
                "value_kind": "string",
                "value_source": "iid",
                "value_iid": annotation.string_value_iid,
            },
        )
    return None, {"value_kind": "none", "value_source": "missing"}


def _extract_annotations(event: Any, tables: _SequenceTables) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    values: dict[str, Any] = {}
    provenance: list[dict[str, Any]] = []
    for annotation in event.debug_annotations:
        name, name_provenance = _annotation_name(annotation, tables)
        value, value_provenance = _annotation_value(annotation, tables)
        _merge_annotation_value(values, name, value)
        provenance.append(
            {
                "name": name,
                **name_provenance,
                **value_provenance,
            }
        )
    return values, provenance


def _resolve_event_name(event: Any, tables: _SequenceTables, flags: int) -> str:
    needs_state = bool(flags & perfetto.TracePacket.SEQ_NEEDS_INCREMENTAL_STATE)
    if event.HasField("name"):
        return event.name
    if not event.HasField("name_iid"):
        return ""
    if needs_state and not tables.valid:
        return f"<missing EventName iid={event.name_iid}>"
    return tables.event_names.get(event.name_iid, f"<missing EventName iid={event.name_iid}>")


def _extract_categories(event: Any, tables: _SequenceTables) -> list[str]:
    categories = list(event.categories)
    categories.extend(
        tables.event_categories.get(iid, f"<missing EventCategory iid={iid}>")
        for iid in event.category_iids
    )
    return categories


def _extract_source_location(
    event: Any, tables: _SequenceTables
) -> dict[str, Any] | None:
    if event.HasField("source_location"):
        location = event.source_location
    elif event.HasField("source_location_iid"):
        location = tables.source_locations.get(event.source_location_iid)
        if location is None:
            return {
                "iid": event.source_location_iid,
                "error": (
                    f"<missing SourceLocation iid={event.source_location_iid}>"
                ),
            }
    else:
        return None
    return {
        "iid": location.iid,
        "file_name": location.file_name,
        "function_name": location.function_name,
        "line_number": location.line_number,
    }


def _extract_callstack(
    event: Any, tables: _SequenceTables
) -> dict[str, Any] | None:
    if event.HasField("callstack"):
        return {
            "source": "inline",
            "frames": [
                {
                    "function_name": frame.function_name,
                    "source_path": frame.source_file,
                    "line_number": frame.line_number,
                }
                for frame in event.callstack.frames
            ],
        }
    if not event.HasField("callstack_iid"):
        return None
    callstack = tables.callstacks.get(event.callstack_iid)
    if callstack is None:
        return {
            "source": "iid",
            "iid": event.callstack_iid,
            "error": f"<missing Callstack iid={event.callstack_iid}>",
        }

    frames: list[dict[str, Any]] = []
    for frame_iid in callstack.frame_ids:
        frame = tables.frames.get(frame_iid)
        if frame is None:
            frames.append(
                {"iid": frame_iid, "error": f"<missing Frame iid={frame_iid}>"}
            )
            continue
        frame_data: dict[str, Any] = {"iid": frame_iid}
        if frame.HasField("function_name_id"):
            frame_data["function_name"] = tables.function_names.get(
                frame.function_name_id,
                f"<missing FunctionName iid={frame.function_name_id}>",
            )
        if frame.HasField("rel_pc"):
            frame_data["rel_pc"] = frame.rel_pc
        if frame.HasField("source_path_iid"):
            frame_data["source_path"] = tables.source_paths.get(
                frame.source_path_iid,
                f"<missing SourcePath iid={frame.source_path_iid}>",
            )
        if frame.HasField("line_number"):
            frame_data["line_number"] = frame.line_number
        if frame.HasField("kind"):
            frame_data["kind"] = frame.kind
        elif frame.HasField("kind_str"):
            frame_data["kind"] = frame.kind_str
        if frame.HasField("mapping_id"):
            mapping = tables.mappings.get(frame.mapping_id)
            if mapping is None:
                frame_data["mapping"] = {
                    "iid": frame.mapping_id,
                    "error": f"<missing Mapping iid={frame.mapping_id}>",
                }
            else:
                mapping_data: dict[str, Any] = {
                    "iid": frame.mapping_id,
                    "path": [
                        tables.mapping_paths.get(
                            path_iid, f"<missing MappingPath iid={path_iid}>"
                        )
                        for path_iid in mapping.path_string_ids
                    ],
                }
                if mapping.HasField("build_id"):
                    build_id = tables.build_ids.get(mapping.build_id)
                    mapping_data["build_id"] = (
                        build_id.hex()
                        if build_id is not None
                        else f"<missing BuildId iid={mapping.build_id}>"
                    )
                for name in (
                    "exact_offset",
                    "start_offset",
                    "start",
                    "end",
                    "load_bias",
                ):
                    if mapping.HasField(name):
                        mapping_data[name] = getattr(mapping, name)
                frame_data["mapping"] = mapping_data
        frames.append(frame_data)
    return {"source": "iid", "iid": event.callstack_iid, "frames": frames}


def _track_descriptor_name(descriptor: Any) -> str:
    return (
        descriptor.thread.thread_name
        or descriptor.name
        or descriptor.process.process_name
        or f"track_{descriptor.uuid}"
    )


def _extract_scalar(mapping: Mapping[str, Any], keys: Iterable[str]) -> _DerivedScalar:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return _DerivedScalar(value, key)
    return _DerivedScalar(None, None)


def _extract_function_name(
    event_name: str,
    annotations: Mapping[str, Any],
) -> tuple[str, str | None]:
    for key in ("function_name", "bnida_symbol"):
        mapped = annotations.get(key)
        if isinstance(mapped, str) and mapped:
            return mapped, key
    if event_name.endswith("#exit"):
        return event_name[: -len("#exit")], None
    return event_name, None


def _extract_side_effects(annotations: Mapping[str, Any]) -> _DerivedScalar:
    for key in SIDE_EFFECT_KEYS:
        value = annotations.get(key)
        if value is not None:
            return _DerivedScalar(value, key)

    derived: dict[str, Any] = {}
    for key, value in annotations.items():
        if key.startswith("side_effect_"):
            derived[key] = value
    if derived:
        return _DerivedScalar(derived, "side_effect_*")
    return _DerivedScalar(None, None)


def _extract_registers(annotations: Mapping[str, Any]) -> dict[str, Any]:
    registers: dict[str, Any] = {}
    nested = annotations.get("registers")
    if isinstance(nested, Mapping):
        for name in REGISTER_NAMES:
            value = nested.get(name)
            if isinstance(value, (int, float, bool, str)):
                registers[name] = value
    for name in REGISTER_NAMES:
        value = annotations.get(name)
        if isinstance(value, (int, float, bool, str)):
            registers[name] = value
    return registers


def _frame_event_type(packet: Any) -> str | None:
    event = packet.frame_timeline_event
    for field_name, event_type in FRAME_EVENT_TYPE_NAMES:
        if event.HasField(field_name):
            return event_type
    return None


def _frame_event_payload(packet: Any, event_type: str) -> dict[str, Any]:
    payload = getattr(packet.frame_timeline_event, event_type)
    data: dict[str, Any] = {}
    for descriptor, value in payload.ListFields():
        if getattr(descriptor, "is_repeated", False):
            data[descriptor.name] = list(value)
            continue
        data[descriptor.name] = value
    return data


def build_trace_index(
    trace_paths: Sequence[Path | str],
    index_path: Path | str,
    *,
    replace: bool = True,
) -> IndexStats:
    """Stream packets into a SQLite index without parsing the whole trace."""
    normalized_paths = [Path(path) for path in trace_paths]
    if not normalized_paths:
        raise ValueError("trace_paths must not be empty")
    for path in normalized_paths:
        if not path.is_file():
            raise FileNotFoundError(f"trace source does not exist or is not a file: {path}")

    db_path = Path(index_path)
    resolved_index = db_path.resolve()
    for path in normalized_paths:
        same_path = path.resolve() == resolved_index
        if not same_path and db_path.exists():
            try:
                same_path = os.path.samefile(path, db_path)
            except OSError:
                same_path = False
        if same_path:
            raise ValueError(f"index path must not overwrite a trace source: {db_path}")

    if not replace and db_path.exists():
        raise FileExistsError(f"index already exists: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f".{db_path.name}.",
        suffix=".tmp",
        dir=db_path.parent,
    )
    os.close(temp_fd)
    temp_path = Path(temp_name)

    conn = _connect_db(temp_path)
    build_succeeded = False
    try:
        _create_schema(conn)
        conn.executemany(
            "INSERT INTO sources(source_id, ordinal, path, size_bytes) VALUES (?, ?, ?, ?)",
            [
                (ordinal, ordinal, str(path), path.stat().st_size)
                for ordinal, path in enumerate(normalized_paths, start=1)
            ],
        )
        conn.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            [
                ("format", "retrobus-perfetto-oracle-index-v2"),
                ("trace_source_count", str(len(normalized_paths))),
                ("uint64_identifier_encoding", "decimal-text"),
                ("uint64_integer_encoding", "twos-complement-signed-i64"),
            ],
        )

        tables_by_sequence: dict[int, _SequenceTables] = {}
        track_names: dict[int, str] = {}
        global_packet_ordinal = 0
        packet_count = 0
        track_event_count = 0
        frame_event_count = 0

        with conn:
            for record in iter_trace_packets(normalized_paths):
                packet = record.packet
                tables, sequence_id, flags = _sequence_tables_for_packet(packet, tables_by_sequence)
                timestamp_ns = packet.timestamp if packet.HasField("timestamp") else None
                packet_kind = "other"
                if packet.HasField("track_descriptor"):
                    packet_kind = "track_descriptor"
                elif packet.HasField("track_event"):
                    packet_kind = "track_event"
                elif packet.HasField("frame_timeline_event"):
                    packet_kind = "frame_timeline_event"

                cursor = conn.execute(
                    """
                    INSERT INTO packets(
                        source_id,
                        source_packet_ordinal,
                        global_packet_ordinal,
                        file_offset,
                        payload_size,
                        timestamp_ns,
                        sequence_id,
                        sequence_flags,
                        previous_packet_dropped,
                        first_packet_on_sequence,
                        incremental_state_valid,
                        packet_kind
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.source_id,
                        record.source_packet_ordinal,
                        global_packet_ordinal,
                        record.offset,
                        record.payload_size,
                        _sqlite_int64(timestamp_ns),
                        sequence_id if sequence_id != 0 else None,
                        flags,
                        int(bool(packet.previous_packet_dropped)),
                        int(bool(packet.first_packet_on_sequence)),
                        int(tables.valid),
                        packet_kind,
                    ),
                )
                packet_id = _require_lastrowid(cursor)
                packet_count += 1

                if packet.HasField("track_descriptor"):
                    descriptor = packet.track_descriptor
                    track_name = _track_descriptor_name(descriptor)
                    track_names[descriptor.uuid] = track_name
                    descriptor_kind = "thread" if descriptor.HasField("thread") else "named"
                    descriptor_json = {
                        "uuid": descriptor.uuid,
                        "parent_uuid": descriptor.parent_uuid if descriptor.parent_uuid else None,
                        "name": descriptor.name or None,
                        "thread_name": descriptor.thread.thread_name if descriptor.HasField("thread") else None,
                        "process_name": descriptor.process.process_name if descriptor.HasField("process") else None,
                    }
                    conn.execute(
                        """
                        INSERT INTO tracks(
                            track_uuid,
                            parent_uuid,
                            name,
                            descriptor_kind,
                            descriptor_json,
                            first_packet_id,
                            last_packet_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(track_uuid) DO UPDATE SET
                            parent_uuid = excluded.parent_uuid,
                            name = excluded.name,
                            descriptor_kind = excluded.descriptor_kind,
                            descriptor_json = excluded.descriptor_json,
                            last_packet_id = excluded.last_packet_id
                        """,
                        (
                            _opaque_u64(descriptor.uuid),
                            _opaque_u64(descriptor.parent_uuid)
                            if descriptor.parent_uuid
                            else None,
                            track_name,
                            descriptor_kind,
                            _json_dump(descriptor_json),
                            packet_id,
                            packet_id,
                        ),
                    )

                if packet.HasField("track_event"):
                    event = packet.track_event
                    annotations, provenance = _extract_annotations(event, tables)
                    event_name = _resolve_event_name(event, tables, flags)
                    categories = _extract_categories(event, tables)
                    function_base_name, function_name_key = _extract_function_name(
                        event_name,
                        annotations,
                    )
                    event_kind = annotations.get("event_kind")
                    if not isinstance(event_kind, str):
                        event_kind = None
                    derived_registers = _extract_registers(annotations)
                    function_address = _extract_scalar(annotations, FUNCTION_ADDRESS_KEYS)
                    callsite_address = _extract_scalar(annotations, CALLSITE_ADDRESS_KEYS)
                    return_address = _extract_scalar(annotations, RETURN_ADDRESS_KEYS)
                    temporal_sequence = _extract_scalar(annotations, TEMPORAL_SEQUENCE_KEYS)
                    frame_index = _extract_scalar(annotations, FRAME_INDEX_KEYS)
                    seen_frame_counter = _extract_scalar(annotations, ("seen_frame_counter",))
                    vsync_counter = _extract_scalar(annotations, VSYNC_KEYS)
                    call_id = _extract_scalar(annotations, CALL_ID_KEYS)
                    enter_index = _extract_scalar(annotations, ENTER_INDEX_KEYS)
                    track_uuid = event.track_uuid
                    track_uuid_text = _opaque_u64(track_uuid)
                    track_name = track_names.get(track_uuid, f"track_{track_uuid}")
                    source_location = _extract_source_location(event, tables)
                    callstack = _extract_callstack(event, tables)
                    side_effects = _extract_side_effects(annotations)
                    derived_provenance = {
                        "function_name_key": function_name_key,
                        "function_address_key": function_address.key,
                        "callsite_address_key": callsite_address.key,
                        "return_address_key": return_address.key,
                        "temporal_sequence_key": temporal_sequence.key,
                        "frame_index_key": frame_index.key,
                        "seen_frame_counter_key": seen_frame_counter.key,
                        "vsync_counter_key": vsync_counter.key,
                        "call_id_key": call_id.key,
                        "enter_index_key": enter_index.key,
                        "side_effects_key": side_effects.key,
                    }
                    annotations_text = _json_dump(annotations)
                    provenance_text = _json_dump(provenance)
                    categories_text = _json_dump(categories)
                    source_location_text = (
                        _json_dump(source_location) if source_location is not None else ""
                    )
                    callstack_text = (
                        _json_dump(callstack) if callstack is not None else ""
                    )
                    has_unresolved_interning = "<missing " in (
                        event_name
                        + annotations_text
                        + provenance_text
                        + categories_text
                        + source_location_text
                        + callstack_text
                    )
                    is_synthetic_reopen = (
                        event_kind == "synthetic_chunk_reopen"
                        or annotations.get("synthetic") is True
                        or annotations.get("synthetic_chunk_reopen") is True
                    )
                    is_exit_probe = event.type == perfetto.TrackEvent.TYPE_INSTANT and (
                        event_name.endswith("#exit") or event_kind == "call_exit"
                    )
                    conn.execute(
                        """
                        INSERT INTO track_events(
                            packet_id,
                            source_id,
                            global_packet_ordinal,
                            sequence_id,
                            track_uuid,
                            track_name,
                            event_type,
                            event_type_name,
                            event_name,
                            categories_json,
                            function_base_name,
                            timestamp_ns,
                            event_kind,
                            is_synthetic_reopen,
                            is_exit_probe,
                            temporal_sequence,
                            frame_index,
                            seen_frame_counter,
                            vsync_counter,
                            function_address,
                            callsite_address,
                            return_address,
                            call_id,
                            enter_index,
                            annotations_json,
                            annotations_provenance_json,
                            derived_provenance_json,
                            registers_json,
                            side_effects_json,
                            source_location_json,
                            callstack_json,
                            has_unresolved_interning
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            packet_id,
                            record.source_id,
                            global_packet_ordinal,
                            sequence_id if sequence_id != 0 else None,
                            track_uuid_text,
                            track_name,
                            event.type,
                            TRACK_EVENT_TYPE_NAMES.get(event.type, f"event_{event.type}"),
                            event_name,
                            categories_text,
                            function_base_name,
                            _sqlite_int64(timestamp_ns),
                            event_kind,
                            int(is_synthetic_reopen),
                            int(is_exit_probe),
                            _sqlite_int64(temporal_sequence.value),
                            _sqlite_int64(frame_index.value),
                            _sqlite_int64(seen_frame_counter.value),
                            _sqlite_int64(vsync_counter.value),
                            _sqlite_int64(function_address.value),
                            _sqlite_int64(callsite_address.value),
                            _sqlite_int64(return_address.value),
                            _opaque_u64(call_id.value),
                            _opaque_u64(enter_index.value),
                            annotations_text,
                            provenance_text,
                            _json_dump(derived_provenance),
                            _json_dump(derived_registers),
                            _json_dump(side_effects.value) if side_effects.value is not None else None,
                            _json_dump(source_location) if source_location is not None else None,
                            _json_dump(callstack) if callstack is not None else None,
                            int(has_unresolved_interning),
                        ),
                    )
                    track_event_count += 1

                if packet.HasField("frame_timeline_event"):
                    event_type = _frame_event_type(packet)
                    if event_type is None:
                        raise ValueError("frame_timeline_event packet did not contain a known payload")
                    payload = _frame_event_payload(packet, event_type)
                    conn.execute(
                        """
                        INSERT INTO frame_events(
                            packet_id,
                            source_id,
                            global_packet_ordinal,
                            event_type,
                            timestamp_ns,
                            cookie,
                            token,
                            display_frame_token,
                            pid,
                            layer_name,
                            payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            packet_id,
                            record.source_id,
                            global_packet_ordinal,
                            event_type,
                            _sqlite_int64(timestamp_ns),
                            payload.get("cookie"),
                            payload.get("token"),
                            payload.get("display_frame_token"),
                            payload.get("pid"),
                            payload.get("layer_name"),
                            _json_dump(payload),
                        ),
                    )
                    frame_event_count += 1

                global_packet_ordinal += 1
        with conn:
            conn.execute(
                """
                UPDATE track_events
                SET track_name = COALESCE(
                    (SELECT name FROM tracks WHERE tracks.track_uuid = track_events.track_uuid),
                    track_name
                )
                """
            )
        build_succeeded = True
    finally:
        conn.close()
        if not build_succeeded:
            for candidate in (temp_path, Path(f"{temp_path}-wal"), Path(f"{temp_path}-shm")):
                candidate.unlink(missing_ok=True)

    try:
        if replace:
            os.replace(temp_path, db_path)
        else:
            os.link(temp_path, db_path)
            temp_path.unlink()
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return IndexStats(
        index_path=db_path,
        source_count=len(normalized_paths),
        packet_count=packet_count,
        track_event_count=track_event_count,
        frame_event_count=frame_event_count,
    )


def _load_json(text: str | None) -> Any:
    if text is None:
        return None
    return json.loads(text)


def _record_issue(
    conn: sqlite3.Connection,
    *,
    severity: str,
    code: str,
    message: str,
    details: Mapping[str, Any],
    packet_id: int | None = None,
    event_id: int | None = None,
    invocation_id: int | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO verification_issues(
            severity,
            code,
            packet_id,
            event_id,
            invocation_id,
            message,
            details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            severity,
            code,
            packet_id,
            event_id,
            invocation_id,
            message,
            _json_dump(dict(details)),
        ),
    )


def _finalize_invocation(
    conn: sqlite3.Connection,
    invocation: _OpenInvocation,
    *,
    terminal_close_kind: str,
) -> int:
    if not invocation.is_real_entry:
        raise ValueError("synthetic orphan cannot be exported as a real invocation")
    provenance = {
        "function_name_key": invocation.function_name_key,
        "function_address_key": invocation.function_address.key,
        "callsite_address_key": invocation.callsite_address.key,
        "entry_sequence_key": invocation.entry_sequence.key,
        "exit_sequence_key": invocation.exit_sequence.key,
        "frame_index_key": invocation.frame_index.key,
        "seen_frame_counter_key": invocation.seen_frame_counter.key,
        "vsync_counter_key": invocation.vsync_counter.key,
        "side_effects_key": invocation.side_effects.key,
        "call_id_key": invocation.call_id.key,
        "enter_index_key": invocation.enter_index.key,
        "exit_eflags_key": invocation.exit_eflags.key,
        "exit_eip_key": invocation.exit_eip.key,
        "synthetic_close_event_ids": invocation.synthetic_close_event_ids,
        "synthetic_reopen_event_ids": invocation.synthetic_reopen_event_ids,
        "entry_packet_id": invocation.entry_packet_id,
        "exit_packet_id": invocation.exit_packet_id,
        "terminal_close_packet_id": invocation.terminal_close_packet_id,
        "trace_provenance": invocation.trace_provenance,
    }
    cursor = conn.execute(
        """
        INSERT INTO oracle_invocations(
            track_uuid,
            track_name,
            entry_source_id,
            exit_source_id,
            terminal_close_source_id,
            entry_event_id,
            exit_event_id,
            terminal_close_event_id,
            function_name,
            function_base_name,
            function_address,
            callsite_address,
            return_address,
            call_id,
            enter_index,
            entry_timestamp_ns,
            exit_timestamp_ns,
            terminal_close_timestamp_ns,
            entry_sequence,
            exit_sequence,
            entry_global_packet_ordinal,
            exit_global_packet_ordinal,
            frame_index,
            seen_frame_counter,
            vsync_counter,
            synthetic_close_count,
            synthetic_reopen_count,
            terminal_close_kind,
            entry_registers_json,
            exit_registers_json,
            exit_eflags,
            exit_eip,
            side_effects_json,
            entry_annotations_json,
            entry_annotations_provenance_json,
            exit_annotations_json,
            exit_annotations_provenance_json,
            provenance_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invocation.track_uuid,
            invocation.track_name,
            invocation.entry_source_id,
            invocation.exit_source_id,
            invocation.terminal_close_source_id,
            invocation.entry_event_id,
            invocation.exit_event_id,
            invocation.terminal_close_event_id,
            invocation.function_name,
            invocation.function_base_name,
            _sqlite_int64(invocation.function_address.value),
            _sqlite_int64(invocation.callsite_address.value),
            _sqlite_int64(invocation.return_address.value),
            _opaque_u64(invocation.call_id.value),
            _opaque_u64(invocation.enter_index.value),
            _sqlite_int64(invocation.entry_timestamp_ns),
            _sqlite_int64(invocation.exit_timestamp_ns),
            _sqlite_int64(invocation.terminal_close_timestamp_ns),
            _sqlite_int64(invocation.entry_sequence.value),
            _sqlite_int64(invocation.exit_sequence.value),
            invocation.entry_global_packet_ordinal,
            invocation.exit_global_packet_ordinal,
            _sqlite_int64(invocation.frame_index.value),
            _sqlite_int64(invocation.seen_frame_counter.value),
            _sqlite_int64(invocation.vsync_counter.value),
            len(invocation.synthetic_close_event_ids),
            len(invocation.synthetic_reopen_event_ids),
            terminal_close_kind,
            _json_dump(invocation.entry_registers),
            _json_dump(invocation.exit_registers) if invocation.exit_registers is not None else None,
            _sqlite_int64(invocation.exit_eflags.value),
            _sqlite_int64(invocation.exit_eip.value),
            _json_dump(invocation.side_effects.value) if invocation.side_effects.value is not None else None,
            _json_dump(invocation.entry_annotations),
            _json_dump(invocation.entry_annotations_provenance),
            _json_dump(invocation.exit_annotations) if invocation.exit_annotations is not None else None,
            _json_dump(invocation.exit_annotations_provenance)
            if invocation.exit_annotations_provenance is not None
            else None,
            _json_dump(provenance),
        ),
    )
    return _require_lastrowid(cursor)


def _invocation_matches(
    invocation: _OpenInvocation,
    *,
    function_base_name: str,
    call_id: int | None,
    enter_index: int | None,
) -> bool:
    invocation_call_id = invocation.call_id.value
    if invocation_call_id is not None and call_id is not None:
        return invocation_call_id == call_id
    invocation_enter_index = invocation.enter_index.value
    if invocation_enter_index is not None and enter_index is not None:
        return invocation_enter_index == enter_index
    return invocation.function_base_name == function_base_name


def _event_scalar(
    value: int | None,
    derived_provenance: Mapping[str, Any],
    provenance_key: str,
) -> _DerivedScalar:
    return _DerivedScalar(_unsigned_from_sqlite(value), derived_provenance.get(provenance_key))


def verify_trace_index(index_path: Path | str) -> VerifyStats:
    """Verify slice/exit integrity and populate the invocation export table."""
    db_path = Path(index_path)
    if not db_path.is_file():
        raise FileNotFoundError(f"oracle index does not exist: {db_path}")
    conn = _connect_db(db_path)
    try:
        format_row = conn.execute(
            "SELECT value FROM metadata WHERE key = 'format'"
        ).fetchone()
        if format_row is None or format_row[0] != "retrobus-perfetto-oracle-index-v2":
            raise ValueError(f"unsupported oracle index format in {db_path}")
        with conn:
            conn.execute("DELETE FROM verification_issues")
            conn.execute("DELETE FROM oracle_invocations")

            max_source_id = int(conn.execute("SELECT MAX(source_id) FROM sources").fetchone()[0])
            trailing_close_after = {
                (int(source_id), str(track_uuid)): (
                    int(last_non_end) if last_non_end is not None else -1
                )
                for source_id, track_uuid, last_non_end in conn.execute(
                    """
                    SELECT
                        source_id,
                        track_uuid,
                        MAX(CASE WHEN event_type != ? THEN global_packet_ordinal END)
                    FROM track_events
                    GROUP BY source_id, track_uuid
                    """,
                    (perfetto.TrackEvent.TYPE_SLICE_END,),
                )
            }

            for packet_id, source_id, sequence_id in conn.execute(
                """
                SELECT packet_id, source_id, sequence_id
                FROM packets
                WHERE previous_packet_dropped = 1
                ORDER BY global_packet_ordinal
                """
            ):
                _record_issue(
                    conn,
                    severity="error",
                    code="packet_loss",
                    packet_id=packet_id,
                    message="producer reported a dropped packet before this packet",
                    details={"source_id": source_id, "sequence_id": sequence_id},
                )

            for event_id, packet_id in conn.execute(
                """
                SELECT event_id, packet_id
                FROM track_events
                WHERE has_unresolved_interning = 1
                ORDER BY global_packet_ordinal, event_id
                """
            ):
                _record_issue(
                    conn,
                    severity="error",
                    code="unresolved_interning",
                    packet_id=packet_id,
                    event_id=event_id,
                    message="track event references unavailable interned data",
                    details={},
                )

            boundary_state = {
                "frame_index": _DerivedScalar(None, None),
                "seen_frame_counter": _DerivedScalar(None, None),
                "vsync_counter": _DerivedScalar(None, None),
            }
            last_boundary_values: dict[str, int] = {}
            last_temporal_sequences: dict[tuple[str, int | str], int] = {}
            last_track_timestamps: dict[str, int] = {}

            open_stacks: dict[str, list[_OpenInvocation]] = {}
            pending_reopens: dict[str, list[_OpenInvocation]] = {}
            call_tracks: set[tuple[int, str]] = set()
            current_source_id: int | None = None
            trace_provenance_by_source = {
                int(source_id): value
                for source_id, annotations_json in conn.execute(
                    """
                    SELECT source_id, annotations_json
                    FROM track_events
                    WHERE event_kind = 'trace_provenance'
                    ORDER BY global_packet_ordinal, event_id
                    """
                )
                if isinstance((value := _load_json(annotations_json)), dict)
            }

            for row in conn.execute(
                """
                SELECT
                    event_id,
                    packet_id,
                    source_id,
                    global_packet_ordinal,
                    sequence_id,
                    track_uuid,
                    track_name,
                    event_type,
                    event_name,
                    function_base_name,
                    timestamp_ns,
                    event_kind,
                    is_synthetic_reopen,
                    is_exit_probe,
                    temporal_sequence,
                    frame_index,
                    seen_frame_counter,
                    vsync_counter,
                    function_address,
                    callsite_address,
                    return_address,
                    call_id,
                    enter_index,
                    annotations_json,
                    annotations_provenance_json,
                    derived_provenance_json,
                    registers_json,
                    side_effects_json
                FROM track_events
                ORDER BY global_packet_ordinal, event_id
                """
            ):
                (
                    event_id,
                    packet_id,
                    source_id,
                    global_packet_ordinal,
                    sequence_id,
                    track_uuid,
                    track_name,
                    event_type,
                    event_name,
                    function_base_name,
                    timestamp_ns,
                    event_kind,
                    is_synthetic_reopen,
                    is_exit_probe,
                    temporal_sequence,
                    frame_index_value,
                    seen_frame_counter_value,
                    vsync_counter_value,
                    function_address_value,
                    callsite_address_value,
                    return_address_value,
                    call_id_text,
                    enter_index_text,
                    annotations_json,
                    annotations_provenance_json,
                    derived_provenance_json,
                    registers_json,
                    side_effects_json,
                ) = row

                annotations = _load_json(annotations_json)
                annotations_provenance = _load_json(annotations_provenance_json)
                derived_provenance = _load_json(derived_provenance_json)
                registers = _load_json(registers_json)
                side_effects_value = _load_json(side_effects_json)
                call_id_value = _parse_opaque_u64(call_id_text)
                enter_index_value = _parse_opaque_u64(enter_index_text)
                timestamp_ns = _unsigned_from_sqlite(timestamp_ns)
                temporal_sequence = _unsigned_from_sqlite(temporal_sequence)
                frame_index_value = _unsigned_from_sqlite(frame_index_value)
                seen_frame_counter_value = _unsigned_from_sqlite(seen_frame_counter_value)
                vsync_counter_value = _unsigned_from_sqlite(vsync_counter_value)

                if current_source_id is not None and source_id != current_source_id:
                    for active_track_uuid, active_stack in open_stacks.items():
                        while active_stack:
                            active = active_stack.pop()
                            if not active.is_real_entry:
                                continue
                            has_real_exit = active.exit_event_id is not None
                            close_kind = (
                                "missing_slice_end" if has_real_exit else "missing_chunk_close"
                            )
                            invocation_id = _finalize_invocation(
                                conn,
                                active,
                                terminal_close_kind=close_kind,
                            )
                            _record_issue(
                                conn,
                                severity="error",
                                code=close_kind,
                                packet_id=active.exit_packet_id or active.entry_packet_id,
                                event_id=active.exit_event_id or active.entry_event_id,
                                invocation_id=invocation_id,
                                message=(
                                    f"{active.function_name} crossed a source boundary without "
                                    "a structural slice close"
                                ),
                                details={"track_uuid": active_track_uuid},
                            )
                current_source_id = source_id

                if timestamp_ns is not None:
                    previous_timestamp = last_track_timestamps.get(track_uuid)
                    if previous_timestamp is not None and timestamp_ns < previous_timestamp:
                        _record_issue(
                            conn,
                            severity="error",
                            code="timestamp_non_monotonic",
                            packet_id=packet_id,
                            event_id=event_id,
                            message=(
                                f"track timestamp regressed from {previous_timestamp} "
                                f"to {timestamp_ns}"
                            ),
                            details={"track_uuid": track_uuid},
                        )
                    last_track_timestamps[track_uuid] = timestamp_ns

                for key, value in (
                    ("frame_index", frame_index_value),
                    ("seen_frame_counter", seen_frame_counter_value),
                    ("vsync_counter", vsync_counter_value),
                ):
                    if isinstance(value, int):
                        previous = last_boundary_values.get(key)
                        if previous is not None and value < previous:
                            _record_issue(
                                conn,
                                severity="error",
                                code="boundary_non_monotonic",
                                packet_id=packet_id,
                                event_id=event_id,
                                message=f"{key} regressed from {previous} to {value}",
                                details={"key": key, "previous": previous, "current": value},
                            )
                        last_boundary_values[key] = value
                        boundary_state[key] = _DerivedScalar(
                            value,
                            derived_provenance.get(f"{key}_key"),
                        )

                if isinstance(temporal_sequence, int):
                    temporal_key: tuple[str, int | str]
                    if sequence_id is not None:
                        temporal_key = ("sequence", int(sequence_id))
                    else:
                        temporal_key = ("track", track_uuid)
                    last_temporal_sequence = last_temporal_sequences.get(temporal_key)
                    if last_temporal_sequence is not None and temporal_sequence < last_temporal_sequence:
                        _record_issue(
                            conn,
                            severity="error",
                            code="temporal_sequence_non_monotonic",
                            packet_id=packet_id,
                            event_id=event_id,
                            message=(
                                f"temporal sequence regressed from {last_temporal_sequence} "
                                f"to {temporal_sequence}"
                            ),
                            details={
                                "previous": last_temporal_sequence,
                                "current": temporal_sequence,
                            },
                        )
                    last_temporal_sequences[temporal_key] = temporal_sequence

                is_explicit_call_event = event_kind in CALL_EVENT_KINDS
                is_legacy_call_track = (
                    track_name.casefold() in LEGACY_CALL_TRACK_NAMES
                )
                call_track = (source_id, track_uuid)
                if is_explicit_call_event or is_legacy_call_track:
                    call_tracks.add(call_track)
                if call_track not in call_tracks:
                    continue

                def new_invocation(*, is_real_entry: bool) -> _OpenInvocation:
                    return _OpenInvocation(
                        track_uuid=track_uuid,
                        track_name=track_name,
                        entry_source_id=source_id,
                        function_name=function_base_name,
                        function_base_name=function_base_name,
                        entry_event_id=event_id,
                        entry_packet_id=packet_id,
                        entry_global_packet_ordinal=global_packet_ordinal,
                        entry_timestamp_ns=timestamp_ns,
                        entry_annotations=annotations,
                        entry_annotations_provenance=annotations_provenance,
                        entry_registers=registers,
                        function_address=_event_scalar(
                            function_address_value,
                            derived_provenance,
                            "function_address_key",
                        ),
                        callsite_address=_event_scalar(
                            callsite_address_value,
                            derived_provenance,
                            "callsite_address_key",
                        ),
                        entry_sequence=_DerivedScalar(
                            temporal_sequence,
                            derived_provenance.get("temporal_sequence_key"),
                        ),
                        frame_index=(
                            _DerivedScalar(
                                frame_index_value,
                                derived_provenance.get("frame_index_key"),
                            )
                            if frame_index_value is not None
                            else boundary_state["frame_index"]
                        ),
                        seen_frame_counter=(
                            _DerivedScalar(
                                seen_frame_counter_value,
                                derived_provenance.get("seen_frame_counter_key"),
                            )
                            if seen_frame_counter_value is not None
                            else boundary_state["seen_frame_counter"]
                        ),
                        vsync_counter=(
                            _DerivedScalar(
                                vsync_counter_value,
                                derived_provenance.get("vsync_counter_key"),
                            )
                            if vsync_counter_value is not None
                            else boundary_state["vsync_counter"]
                        ),
                        side_effects=_DerivedScalar(
                            side_effects_value,
                            derived_provenance.get("side_effects_key"),
                        ),
                        call_id=_DerivedScalar(
                            call_id_value,
                            derived_provenance.get("call_id_key"),
                        ),
                        enter_index=_DerivedScalar(
                            enter_index_value,
                            derived_provenance.get("enter_index_key"),
                        ),
                        function_name_key=derived_provenance.get("function_name_key"),
                        trace_provenance=trace_provenance_by_source.get(source_id, {}),
                        is_real_entry=is_real_entry,
                    )

                stack = open_stacks.setdefault(track_uuid, [])
                pending = pending_reopens.setdefault(track_uuid, [])

                def flush_pending_missing() -> None:
                    while pending:
                        invocation = pending.pop()
                        invocation_id = _finalize_invocation(
                            conn,
                            invocation,
                            terminal_close_kind="missing_reopen",
                        )
                        _record_issue(
                            conn,
                            severity="error",
                            code="synthetic_close_without_reopen",
                            packet_id=invocation.terminal_close_packet_id,
                            event_id=invocation.terminal_close_event_id,
                            invocation_id=invocation_id,
                            message=(
                                f"{invocation.function_name} had a trailing synthetic close "
                                "but was not reopened in the next chunk"
                            ),
                            details={
                                "track_uuid": invocation.track_uuid,
                                "function_name": invocation.function_name,
                            },
                        )

                if event_type == perfetto.TrackEvent.TYPE_SLICE_BEGIN:
                    if is_synthetic_reopen:
                        if not pending:
                            _record_issue(
                                conn,
                                severity="error",
                                code="unexpected_synthetic_reopen",
                                packet_id=packet_id,
                                event_id=event_id,
                                message=(
                                    f"{event_name} was marked synthetic_chunk_reopen without "
                                    "a prior unmatched synthetic close"
                                ),
                                details={
                                    "track_uuid": track_uuid,
                                    "function_name": event_name,
                                },
                            )
                            invocation = new_invocation(is_real_entry=False)
                            stack.append(invocation)
                            continue

                        match_index = next(
                            (
                                index
                                for index in range(len(pending) - 1, -1, -1)
                                if _invocation_matches(
                                    pending[index],
                                    function_base_name=function_base_name,
                                    call_id=call_id_value,
                                    enter_index=enter_index_value,
                                )
                                and pending[index].terminal_close_source_id is not None
                                and pending[index].terminal_close_source_id < source_id
                            ),
                            None,
                        )
                        if match_index is None:
                            _record_issue(
                                conn,
                                severity="error",
                                code="synthetic_reopen_mismatch",
                                packet_id=packet_id,
                                event_id=event_id,
                                message=(
                                    f"synthetic reopen {function_base_name} did not match "
                                    "a trailing close from an earlier source"
                                ),
                                details={
                                    "actual": function_base_name,
                                    "track_uuid": track_uuid,
                                    "source_id": source_id,
                                },
                            )
                            stack.append(new_invocation(is_real_entry=False))
                            continue
                        if match_index != len(pending) - 1:
                            _record_issue(
                                conn,
                                severity="error",
                                code="synthetic_reopen_order_mismatch",
                                packet_id=packet_id,
                                event_id=event_id,
                                message="synthetic reopen did not preserve stack order",
                                details={"track_uuid": track_uuid},
                            )
                        invocation = pending.pop(match_index)
                        invocation.synthetic_reopen_event_ids.append(event_id)
                        invocation.terminal_close_event_id = None
                        invocation.terminal_close_source_id = None
                        invocation.terminal_close_packet_id = None
                        invocation.terminal_close_timestamp_ns = None
                        stack.append(invocation)
                        continue

                    flush_pending_missing()
                    stack.append(new_invocation(is_real_entry=True))
                    continue

                if is_exit_probe:
                    flush_pending_missing()
                    if not stack:
                        _record_issue(
                            conn,
                            severity="error",
                            code="unexpected_exit_probe",
                            packet_id=packet_id,
                            event_id=event_id,
                            message=f"{event_name} exit probe did not have a matching open slice",
                            details={"track_uuid": track_uuid, "function_name": event_name},
                        )
                        continue
                    match_index = next(
                        (
                            index
                            for index in range(len(stack) - 1, -1, -1)
                            if _invocation_matches(
                                stack[index],
                                function_base_name=function_base_name,
                                call_id=call_id_value,
                                enter_index=enter_index_value,
                            )
                        ),
                        None,
                    )
                    if match_index is None:
                        _record_issue(
                            conn,
                            severity="error",
                            code="exit_probe_mismatch",
                            packet_id=packet_id,
                            event_id=event_id,
                            message=(
                                f"{event_name} exit probe did not match an active invocation"
                            ),
                            details={
                                "probe": event_name,
                                "track_uuid": track_uuid,
                                "call_id": call_id_value,
                                "enter_index": enter_index_value,
                            },
                        )
                        continue
                    invocation = stack[match_index]
                    if match_index != len(stack) - 1:
                        _record_issue(
                            conn,
                            severity="error",
                            code="exit_probe_out_of_order",
                            packet_id=packet_id,
                            event_id=event_id,
                            message="exit probe did not target the innermost active invocation",
                            details={"track_uuid": track_uuid},
                        )
                    if invocation.exit_event_id is not None:
                        _record_issue(
                            conn,
                            severity="error",
                            code="duplicate_exit_probe",
                            packet_id=packet_id,
                            event_id=event_id,
                            message=f"{event_name} emitted more than one real exit probe",
                            details={"track_uuid": track_uuid},
                        )
                        continue
                    if not invocation.is_real_entry:
                        _record_issue(
                            conn,
                            severity="error",
                            code="orphan_synthetic_exit",
                            packet_id=packet_id,
                            event_id=event_id,
                            message="exit probe belongs to an unmatched synthetic reopen",
                            details={"track_uuid": track_uuid},
                        )
                    invocation.exit_event_id = event_id
                    invocation.exit_source_id = source_id
                    invocation.exit_packet_id = packet_id
                    invocation.exit_global_packet_ordinal = global_packet_ordinal
                    invocation.exit_timestamp_ns = timestamp_ns
                    invocation.exit_annotations = annotations
                    invocation.exit_annotations_provenance = annotations_provenance
                    invocation.exit_registers = registers
                    invocation.exit_sequence = _DerivedScalar(
                        temporal_sequence,
                        derived_provenance.get("temporal_sequence_key"),
                    )
                    if (
                        invocation.function_address.value is None
                        and function_address_value is not None
                    ):
                        invocation.function_address = _event_scalar(
                            function_address_value,
                            derived_provenance,
                            "function_address_key",
                        )
                    if (
                        invocation.callsite_address.value is None
                        and callsite_address_value is not None
                    ):
                        invocation.callsite_address = _event_scalar(
                            callsite_address_value,
                            derived_provenance,
                            "callsite_address_key",
                        )
                    invocation.return_address = _event_scalar(
                        return_address_value,
                        derived_provenance,
                        "return_address_key",
                    )
                    invocation.exit_eflags = _DerivedScalar(
                        annotations.get("eflags")
                        if isinstance(annotations.get("eflags"), int)
                        and not isinstance(annotations.get("eflags"), bool)
                        else None,
                        "eflags" if isinstance(annotations.get("eflags"), int) else None,
                    )
                    invocation.exit_eip = _DerivedScalar(
                        annotations.get("eip")
                        if isinstance(annotations.get("eip"), int)
                        and not isinstance(annotations.get("eip"), bool)
                        else None,
                        "eip" if isinstance(annotations.get("eip"), int) else None,
                    )
                    if invocation.side_effects.value is None and side_effects_value is not None:
                        invocation.side_effects = _DerivedScalar(
                            side_effects_value,
                            derived_provenance.get("side_effects_key"),
                        )
                    if (
                        invocation.exit_eip.value is not None
                        and invocation.return_address.value is not None
                        and invocation.exit_eip.value != invocation.return_address.value
                    ):
                        _record_issue(
                            conn,
                            severity="error",
                            code="exit_eip_mismatch",
                            packet_id=packet_id,
                            event_id=event_id,
                            message="actual exit eip does not match the declared return eip",
                            details={
                                "actual_eip": invocation.exit_eip.value,
                                "return_eip": invocation.return_address.value,
                            },
                        )
                    continue

                if event_type == perfetto.TrackEvent.TYPE_SLICE_END:
                    if not stack:
                        _record_issue(
                            conn,
                            severity="error",
                            code="unexpected_slice_end",
                            packet_id=packet_id,
                            event_id=event_id,
                            message="slice end did not have a matching open slice",
                            details={"track_uuid": track_uuid},
                        )
                        continue
                    invocation = stack.pop()
                    invocation.terminal_close_event_id = event_id
                    invocation.terminal_close_source_id = source_id
                    invocation.terminal_close_packet_id = packet_id
                    invocation.terminal_close_timestamp_ns = timestamp_ns
                    if not invocation.is_real_entry:
                        continue
                    if invocation.exit_event_id is not None:
                        _finalize_invocation(conn, invocation, terminal_close_kind="real_exit")
                    elif global_packet_ordinal > trailing_close_after[(source_id, track_uuid)]:
                        invocation.synthetic_close_event_ids.append(event_id)
                        pending.append(invocation)
                    else:
                        invocation_id = _finalize_invocation(
                            conn,
                            invocation,
                            terminal_close_kind="missing_exit",
                        )
                        _record_issue(
                            conn,
                            severity="error",
                            code="missing_exit_probe",
                            packet_id=packet_id,
                            event_id=event_id,
                            invocation_id=invocation_id,
                            message=f"{invocation.function_name} closed without a real exit probe",
                            details={"track_uuid": track_uuid},
                        )

            for track_uuid, pending in pending_reopens.items():
                while pending:
                    invocation = pending.pop()
                    is_final_source = invocation.terminal_close_source_id == max_source_id
                    terminal_close_kind = (
                        "synthetic_close_in_flight" if is_final_source else "missing_reopen"
                    )
                    invocation_id = _finalize_invocation(
                        conn,
                        invocation,
                        terminal_close_kind=terminal_close_kind,
                    )
                    _record_issue(
                        conn,
                        severity="error",
                        code=(
                            "final_in_flight_call"
                            if is_final_source
                            else "synthetic_close_without_reopen"
                        ),
                        packet_id=invocation.terminal_close_packet_id,
                        event_id=invocation.terminal_close_event_id,
                        invocation_id=invocation_id,
                        message=(
                            f"{invocation.function_name} remained in flight at the final "
                            "synthetic chunk close"
                            if is_final_source
                            else f"{invocation.function_name} was not reopened after a "
                            "synthetic chunk close"
                        ),
                        details={"track_uuid": track_uuid},
                    )

            for track_uuid, stack in open_stacks.items():
                while stack:
                    invocation = stack.pop()
                    if not invocation.is_real_entry:
                        continue
                    has_real_exit = invocation.exit_event_id is not None
                    terminal_close_kind = "missing_slice_end" if has_real_exit else "in_flight"
                    invocation_id = _finalize_invocation(
                        conn,
                        invocation,
                        terminal_close_kind=terminal_close_kind,
                    )
                    _record_issue(
                        conn,
                        severity="error",
                        code="missing_slice_end" if has_real_exit else "final_in_flight_call",
                        packet_id=invocation.exit_packet_id or invocation.entry_packet_id,
                        event_id=invocation.exit_event_id or invocation.entry_event_id,
                        invocation_id=invocation_id,
                        message=(
                            f"{invocation.function_name} emitted a real exit but no slice end"
                            if has_real_exit
                            else f"{invocation.function_name} was still in flight at end of trace"
                        ),
                        details={"track_uuid": track_uuid},
                    )

            open_frame_cookies: dict[int, list[tuple[int, int, int | None, str]]] = {}
            last_frame_timestamp: int | None = None
            for row in conn.execute(
                """
                SELECT
                    frame_event_id,
                    packet_id,
                    event_type,
                    cookie,
                    timestamp_ns
                FROM frame_events
                ORDER BY global_packet_ordinal, frame_event_id
                """
            ):
                frame_event_id, packet_id, event_type, cookie, timestamp_ns = row
                timestamp_ns = _unsigned_from_sqlite(timestamp_ns)
                if (
                    timestamp_ns is not None
                    and last_frame_timestamp is not None
                    and timestamp_ns < last_frame_timestamp
                ):
                    _record_issue(
                        conn,
                        severity="error",
                        code="frame_timestamp_non_monotonic",
                        packet_id=packet_id,
                        message="frame timeline timestamp regressed",
                        details={
                            "previous": last_frame_timestamp,
                            "current": timestamp_ns,
                        },
                    )
                if timestamp_ns is not None:
                    last_frame_timestamp = timestamp_ns
                if cookie is None:
                    continue
                if event_type == "frame_end":
                    pending_starts = open_frame_cookies.get(cookie)
                    if not pending_starts:
                        _record_issue(
                            conn,
                            severity="error",
                            code="frame_end_without_start",
                            packet_id=packet_id,
                            message=f"frame_end for cookie {cookie} had no prior start",
                            details={"cookie": cookie},
                        )
                        continue
                    start_event_id, _, start_timestamp_ns, start_type = pending_starts.pop()
                    if (
                        timestamp_ns is not None
                        and start_timestamp_ns is not None
                        and timestamp_ns < start_timestamp_ns
                    ):
                        _record_issue(
                            conn,
                            severity="error",
                            code="frame_end_before_start",
                            packet_id=packet_id,
                            message=f"frame_end for cookie {cookie} precedes its start",
                            details={
                                "cookie": cookie,
                                "start_event_id": start_event_id,
                                "start_type": start_type,
                            },
                        )
                    if not pending_starts:
                        del open_frame_cookies[cookie]
                    continue
                open_frame_cookies.setdefault(cookie, []).append(
                    (frame_event_id, packet_id, timestamp_ns, event_type)
                )

            for cookie, frame_starts in open_frame_cookies.items():
                for frame_event_id, packet_id, _, event_type in frame_starts:
                    _record_issue(
                        conn,
                        severity="error",
                        code="frame_start_without_end",
                        packet_id=packet_id,
                        message=f"frame cookie {cookie} never observed a frame_end",
                        details={
                            "cookie": cookie,
                            "frame_event_id": frame_event_id,
                            "event_type": event_type,
                        },
                    )

        invocation_count = conn.execute("SELECT COUNT(*) FROM oracle_invocations").fetchone()[0]
        issue_count = conn.execute("SELECT COUNT(*) FROM verification_issues").fetchone()[0]
        missing_exit_count = conn.execute(
            "SELECT COUNT(*) FROM oracle_invocations WHERE terminal_close_kind = 'missing_exit'"
        ).fetchone()[0]
        in_flight_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM oracle_invocations
            WHERE terminal_close_kind IN ('in_flight', 'synthetic_close_in_flight')
            """
        ).fetchone()[0]
    finally:
        conn.close()

    return VerifyStats(
        index_path=db_path,
        invocation_count=int(invocation_count),
        issue_count=int(issue_count),
        missing_exit_count=int(missing_exit_count),
        in_flight_count=int(in_flight_count),
    )
