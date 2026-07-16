"""Streaming Perfetto trace indexing and parity-oracle export helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import sqlite3
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
    "entry_eip",
    "probe_target",
    "function_address",
    "target_eip",
    "bnida_symbol_addr",
    "address",
)
CALLSITE_ADDRESS_KEYS = (
    "source_eip",
    "probe_callsite",
    "callsite",
    "caller_eip",
)
RETURN_ADDRESS_KEYS = (
    "return_eip",
    "exit_eip",
    "eip",
)
TEMPORAL_SEQUENCE_KEYS = (
    "temporal_sequence",
    "sequence",
    "idx",
    "tick",
)
FRAME_INDEX_KEYS = (
    "frame_index",
    "seen_frame_counter",
)
VSYNC_KEYS = (
    "vsync_counter",
    "frame_counter",
)
SIDE_EFFECT_KEYS = (
    "side_effects",
    "side_effect",
)
TRACK_EVENT_TYPE_NAMES = {
    perfetto.TrackEvent.TYPE_SLICE_BEGIN: "slice_begin",
    perfetto.TrackEvent.TYPE_SLICE_END: "slice_end",
    perfetto.TrackEvent.TYPE_INSTANT: "instant",
    perfetto.TrackEvent.TYPE_COUNTER: "counter",
}
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
    event_names: Dict[int, str] = field(default_factory=dict)
    debug_annotation_names: Dict[int, str] = field(default_factory=dict)
    debug_annotation_string_values: Dict[int, str] = field(default_factory=dict)
    valid: bool = False


@dataclass(frozen=True)
class _PacketRecord:
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
    track_uuid: int
    track_name: str
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
    synthetic_close_event_ids: list[int] = field(default_factory=list)
    synthetic_reopen_event_ids: list[int] = field(default_factory=list)
    exit_event_id: int | None = None
    exit_packet_id: int | None = None
    exit_global_packet_ordinal: int | None = None
    exit_timestamp_ns: int | None = None
    exit_annotations: dict[str, Any] | None = None
    exit_annotations_provenance: Any = None
    exit_registers: dict[str, Any] | None = None
    exit_sequence: _DerivedScalar = field(default_factory=lambda: _DerivedScalar(None, None))
    return_address: _DerivedScalar = field(default_factory=lambda: _DerivedScalar(None, None))
    exit_eflags: _DerivedScalar = field(default_factory=lambda: _DerivedScalar(None, None))
    terminal_close_event_id: int | None = None
    terminal_close_packet_id: int | None = None
    terminal_close_timestamp_ns: int | None = None


def _json_dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


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
            packet_kind TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES sources(source_id)
        );
        CREATE INDEX idx_packets_global_packet_ordinal
            ON packets(global_packet_ordinal);

        CREATE TABLE tracks (
            track_uuid INTEGER PRIMARY KEY,
            parent_uuid INTEGER,
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
            track_uuid INTEGER NOT NULL,
            track_name TEXT NOT NULL,
            event_type INTEGER NOT NULL,
            event_type_name TEXT NOT NULL,
            event_name TEXT NOT NULL,
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
            annotations_json TEXT NOT NULL,
            annotations_provenance_json TEXT NOT NULL,
            registers_json TEXT NOT NULL,
            side_effects_json TEXT,
            source_location_json TEXT,
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
            track_uuid INTEGER NOT NULL,
            track_name TEXT NOT NULL,
            entry_event_id INTEGER NOT NULL,
            exit_event_id INTEGER,
            terminal_close_event_id INTEGER,
            function_name TEXT NOT NULL,
            function_base_name TEXT NOT NULL,
            function_address INTEGER,
            callsite_address INTEGER,
            return_address INTEGER,
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
    return _require_lastrowid(cursor)


def iter_trace_packets(trace_paths: Sequence[Path]) -> Iterator[_PacketRecord]:
    """Yield TracePacket messages without parsing the whole Trace wrapper."""
    for source_id, trace_path in enumerate(trace_paths, start=1):
        packet_ordinal = 0
        with trace_path.open("rb") as handle:
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
                payload = handle.read(payload_size)
                if len(payload) != payload_size:
                    raise ValueError(
                        f"{trace_path}: truncated TracePacket payload at byte {offset}"
                    )
                packet = perfetto.TracePacket()
                packet.ParseFromString(payload)
                yield _PacketRecord(
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
        tables.event_names.clear()
        tables.debug_annotation_names.clear()
        tables.debug_annotation_string_values.clear()

    if flags & perfetto.TracePacket.SEQ_INCREMENTAL_STATE_CLEARED:
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
            tables.debug_annotation_string_values[entry.iid] = entry.str.decode(
                "utf-8", errors="replace"
            )

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


def _extract_source_location(event: Any) -> dict[str, Any] | None:
    if not event.HasField("source_location"):
        return None
    location = event.source_location
    return {
        "iid": location.iid,
        "file_name": location.file_name,
        "function_name": location.function_name,
        "line_number": location.line_number,
    }


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
        if isinstance(value, int):
            return _DerivedScalar(value, key)
    return _DerivedScalar(None, None)


def _extract_function_name(event_name: str, annotations: Mapping[str, Any]) -> str:
    mapped = annotations.get("bnida_symbol")
    if isinstance(mapped, str) and mapped:
        return mapped
    if event_name.endswith("#exit"):
        return event_name[: -len("#exit")]
    return event_name


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

    db_path = Path(index_path)
    if replace and db_path.exists():
        db_path.unlink()
    elif db_path.exists():
        raise FileExistsError(f"index already exists: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = _connect_db(db_path)
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
                ("format", "retrobus-perfetto-oracle-index-v1"),
                ("trace_source_count", str(len(normalized_paths))),
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
                        packet_kind
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.source_id,
                        record.source_packet_ordinal,
                        global_packet_ordinal,
                        record.offset,
                        record.payload_size,
                        timestamp_ns,
                        sequence_id if sequence_id != 0 else None,
                        flags,
                        int(bool(packet.previous_packet_dropped)),
                        int(bool(packet.first_packet_on_sequence)),
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
                            descriptor.uuid,
                            descriptor.parent_uuid if descriptor.parent_uuid else None,
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
                    function_base_name = (
                        event_name[: -len("#exit")] if event_name.endswith("#exit") else event_name
                    )
                    event_kind = annotations.get("event_kind")
                    if not isinstance(event_kind, str):
                        event_kind = None
                    derived_registers = _extract_registers(annotations)
                    function_address = _extract_scalar(annotations, FUNCTION_ADDRESS_KEYS)
                    callsite_address = _extract_scalar(annotations, CALLSITE_ADDRESS_KEYS)
                    return_address = _extract_scalar(annotations, RETURN_ADDRESS_KEYS)
                    temporal_sequence = _extract_scalar(annotations, TEMPORAL_SEQUENCE_KEYS)
                    frame_index = _extract_scalar(annotations, ("frame_index",))
                    seen_frame_counter = _extract_scalar(annotations, ("seen_frame_counter",))
                    vsync_counter = _extract_scalar(annotations, ("vsync_counter", "frame_counter"))
                    track_uuid = event.track_uuid
                    track_name = track_names.get(track_uuid, f"track_{track_uuid}")
                    source_location = _extract_source_location(event)
                    side_effects = _extract_side_effects(annotations)
                    conn.execute(
                        """
                        INSERT INTO track_events(
                            packet_id,
                            source_id,
                            global_packet_ordinal,
                            track_uuid,
                            track_name,
                            event_type,
                            event_type_name,
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
                            annotations_json,
                            annotations_provenance_json,
                            registers_json,
                            side_effects_json,
                            source_location_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            packet_id,
                            record.source_id,
                            global_packet_ordinal,
                            track_uuid,
                            track_name,
                            event.type,
                            TRACK_EVENT_TYPE_NAMES.get(event.type, f"event_{event.type}"),
                            event_name,
                            function_base_name,
                            timestamp_ns,
                            event_kind,
                            int(event_kind == "synthetic_chunk_reopen"),
                            int(event.type == perfetto.TrackEvent.TYPE_INSTANT and event_name.endswith("#exit")),
                            temporal_sequence.value,
                            frame_index.value,
                            seen_frame_counter.value,
                            vsync_counter.value,
                            function_address.value,
                            callsite_address.value,
                            return_address.value,
                            _json_dump(annotations),
                            _json_dump(provenance),
                            _json_dump(derived_registers),
                            _json_dump(side_effects.value) if side_effects.value is not None else None,
                            _json_dump(source_location) if source_location is not None else None,
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
                            timestamp_ns,
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
        conn.execute(
            """
            UPDATE track_events
            SET track_name = COALESCE(
                (SELECT name FROM tracks WHERE tracks.track_uuid = track_events.track_uuid),
                track_name
            )
            """
        )
    finally:
        conn.close()

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
    provenance = {
        "function_address_key": invocation.function_address.key,
        "callsite_address_key": invocation.callsite_address.key,
        "entry_sequence_key": invocation.entry_sequence.key,
        "exit_sequence_key": invocation.exit_sequence.key,
        "frame_index_key": invocation.frame_index.key,
        "seen_frame_counter_key": invocation.seen_frame_counter.key,
        "vsync_counter_key": invocation.vsync_counter.key,
        "side_effects_key": invocation.side_effects.key,
        "synthetic_close_event_ids": invocation.synthetic_close_event_ids,
        "synthetic_reopen_event_ids": invocation.synthetic_reopen_event_ids,
        "entry_packet_id": invocation.entry_packet_id,
        "exit_packet_id": invocation.exit_packet_id,
        "terminal_close_packet_id": invocation.terminal_close_packet_id,
    }
    cursor = conn.execute(
        """
        INSERT INTO oracle_invocations(
            track_uuid,
            track_name,
            entry_event_id,
            exit_event_id,
            terminal_close_event_id,
            function_name,
            function_base_name,
            function_address,
            callsite_address,
            return_address,
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invocation.track_uuid,
            invocation.track_name,
            invocation.entry_event_id,
            invocation.exit_event_id,
            invocation.terminal_close_event_id,
            invocation.function_name,
            invocation.function_base_name,
            invocation.function_address.value,
            invocation.callsite_address.value,
            invocation.return_address.value,
            invocation.entry_timestamp_ns,
            invocation.exit_timestamp_ns,
            invocation.terminal_close_timestamp_ns,
            invocation.entry_sequence.value,
            invocation.exit_sequence.value,
            invocation.entry_global_packet_ordinal,
            invocation.exit_global_packet_ordinal,
            invocation.frame_index.value,
            invocation.seen_frame_counter.value,
            invocation.vsync_counter.value,
            len(invocation.synthetic_close_event_ids),
            len(invocation.synthetic_reopen_event_ids),
            terminal_close_kind,
            _json_dump(invocation.entry_registers),
            _json_dump(invocation.exit_registers) if invocation.exit_registers is not None else None,
            invocation.exit_eflags.value,
            invocation.return_address.value,
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


def verify_trace_index(index_path: Path | str) -> VerifyStats:
    """Verify slice/exit integrity and populate the invocation export table."""
    db_path = Path(index_path)
    conn = _connect_db(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM verification_issues")
            conn.execute("DELETE FROM oracle_invocations")

            boundary_state = {
                "frame_index": _DerivedScalar(None, None),
                "seen_frame_counter": _DerivedScalar(None, None),
                "vsync_counter": _DerivedScalar(None, None),
            }
            last_boundary_values: dict[str, int] = {}
            last_temporal_sequence: int | None = None

            open_stacks: dict[int, list[_OpenInvocation]] = {}
            pending_reopens: dict[int, list[_OpenInvocation]] = {}

            for row in conn.execute(
                """
                SELECT
                    event_id,
                    packet_id,
                    global_packet_ordinal,
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
                    annotations_json,
                    annotations_provenance_json,
                    registers_json,
                    side_effects_json
                FROM track_events
                ORDER BY global_packet_ordinal, event_id
                """
            ):
                (
                    event_id,
                    packet_id,
                    global_packet_ordinal,
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
                    annotations_json,
                    annotations_provenance_json,
                    registers_json,
                    side_effects_json,
                ) = row

                annotations = _load_json(annotations_json)
                annotations_provenance = _load_json(annotations_provenance_json)
                registers = _load_json(registers_json)
                side_effects_value = _load_json(side_effects_json)

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
                        boundary_state[key] = _DerivedScalar(value, key)

                if isinstance(temporal_sequence, int):
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
                    last_temporal_sequence = temporal_sequence

                stack = open_stacks.setdefault(track_uuid, [])
                pending = pending_reopens.setdefault(track_uuid, [])

                def flush_pending_missing() -> None:
                    while pending:
                        invocation = pending.pop()
                        invocation_id = _finalize_invocation(
                            conn,
                            invocation,
                            terminal_close_kind="missing_exit",
                        )
                        _record_issue(
                            conn,
                            severity="error",
                            code="missing_exit_probe",
                            packet_id=invocation.terminal_close_packet_id,
                            event_id=invocation.terminal_close_event_id,
                            invocation_id=invocation_id,
                            message=(
                                f"{invocation.function_name} closed without a real exit probe "
                                "and was not reopened"
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
                            invocation = _OpenInvocation(
                                track_uuid=track_uuid,
                                track_name=track_name,
                                function_name=_extract_function_name(event_name, annotations),
                                function_base_name=function_base_name,
                                entry_event_id=event_id,
                                entry_packet_id=packet_id,
                                entry_global_packet_ordinal=global_packet_ordinal,
                                entry_timestamp_ns=timestamp_ns,
                                entry_annotations=annotations,
                                entry_annotations_provenance=annotations_provenance,
                                entry_registers=registers,
                                function_address=_DerivedScalar(function_address_value, None),
                                callsite_address=_DerivedScalar(callsite_address_value, None),
                                entry_sequence=_DerivedScalar(temporal_sequence, None),
                                frame_index=(
                                    _DerivedScalar(frame_index_value, "frame_index")
                                    if isinstance(frame_index_value, int)
                                    else boundary_state["frame_index"]
                                ),
                                seen_frame_counter=(
                                    _DerivedScalar(seen_frame_counter_value, "seen_frame_counter")
                                    if isinstance(seen_frame_counter_value, int)
                                    else boundary_state["seen_frame_counter"]
                                ),
                                vsync_counter=(
                                    _DerivedScalar(vsync_counter_value, "vsync_counter")
                                    if isinstance(vsync_counter_value, int)
                                    else boundary_state["vsync_counter"]
                                ),
                                side_effects=_DerivedScalar(side_effects_value, None),
                            )
                            stack.append(invocation)
                            continue

                        invocation = pending.pop()
                        if invocation.function_base_name != function_base_name:
                            _record_issue(
                                conn,
                                severity="error",
                                code="synthetic_reopen_mismatch",
                                packet_id=packet_id,
                                event_id=event_id,
                                message=(
                                    f"synthetic reopen {function_base_name} did not match "
                                    f"pending {invocation.function_base_name}"
                                ),
                                details={
                                    "expected": invocation.function_base_name,
                                    "actual": function_base_name,
                                    "track_uuid": track_uuid,
                                },
                            )
                        if invocation.terminal_close_event_id is not None:
                            invocation.synthetic_close_event_ids.append(
                                invocation.terminal_close_event_id
                            )
                        invocation.synthetic_reopen_event_ids.append(event_id)
                        invocation.terminal_close_event_id = None
                        invocation.terminal_close_packet_id = None
                        invocation.terminal_close_timestamp_ns = None
                        stack.append(invocation)
                        continue

                    flush_pending_missing()
                    stack.append(
                        _OpenInvocation(
                            track_uuid=track_uuid,
                            track_name=track_name,
                            function_name=_extract_function_name(event_name, annotations),
                            function_base_name=function_base_name,
                            entry_event_id=event_id,
                            entry_packet_id=packet_id,
                            entry_global_packet_ordinal=global_packet_ordinal,
                            entry_timestamp_ns=timestamp_ns,
                            entry_annotations=annotations,
                            entry_annotations_provenance=annotations_provenance,
                            entry_registers=registers,
                            function_address=_DerivedScalar(function_address_value, None),
                            callsite_address=_DerivedScalar(callsite_address_value, None),
                            entry_sequence=_DerivedScalar(temporal_sequence, None),
                            frame_index=(
                                _DerivedScalar(frame_index_value, "frame_index")
                                if isinstance(frame_index_value, int)
                                else boundary_state["frame_index"]
                            ),
                            seen_frame_counter=(
                                _DerivedScalar(seen_frame_counter_value, "seen_frame_counter")
                                if isinstance(seen_frame_counter_value, int)
                                else boundary_state["seen_frame_counter"]
                            ),
                            vsync_counter=(
                                _DerivedScalar(vsync_counter_value, "vsync_counter")
                                if isinstance(vsync_counter_value, int)
                                else boundary_state["vsync_counter"]
                            ),
                            side_effects=_DerivedScalar(side_effects_value, None),
                        )
                    )
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
                    invocation = stack[-1]
                    if invocation.function_base_name != function_base_name:
                        _record_issue(
                            conn,
                            severity="error",
                            code="exit_probe_mismatch",
                            packet_id=packet_id,
                            event_id=event_id,
                            message=(
                                f"{event_name} exit probe did not match the active "
                                f"{invocation.function_name} slice"
                            ),
                            details={
                                "active": invocation.function_name,
                                "probe": event_name,
                                "track_uuid": track_uuid,
                            },
                        )
                    invocation.exit_event_id = event_id
                    invocation.exit_packet_id = packet_id
                    invocation.exit_global_packet_ordinal = global_packet_ordinal
                    invocation.exit_timestamp_ns = timestamp_ns
                    invocation.exit_annotations = annotations
                    invocation.exit_annotations_provenance = annotations_provenance
                    invocation.exit_registers = registers
                    invocation.exit_sequence = _DerivedScalar(temporal_sequence, None)
                    invocation.return_address = _DerivedScalar(return_address_value, None)
                    invocation.exit_eflags = _DerivedScalar(
                        annotations.get("eflags") if isinstance(annotations.get("eflags"), int) else None,
                        "eflags" if isinstance(annotations.get("eflags"), int) else None,
                    )
                    if invocation.side_effects.value is None and side_effects_value is not None:
                        invocation.side_effects = _DerivedScalar(side_effects_value, None)
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
                    invocation.terminal_close_packet_id = packet_id
                    invocation.terminal_close_timestamp_ns = timestamp_ns
                    if invocation.exit_event_id is not None:
                        _finalize_invocation(conn, invocation, terminal_close_kind="real_exit")
                    else:
                        pending.append(invocation)

            for track_uuid, pending in pending_reopens.items():
                while pending:
                    invocation = pending.pop()
                    invocation_id = _finalize_invocation(
                        conn,
                        invocation,
                        terminal_close_kind="missing_exit",
                    )
                    _record_issue(
                        conn,
                        severity="error",
                        code="missing_exit_probe",
                        packet_id=invocation.terminal_close_packet_id,
                        event_id=invocation.terminal_close_event_id,
                        invocation_id=invocation_id,
                        message=(
                            f"{invocation.function_name} closed without a real exit probe "
                            "and was not reopened"
                        ),
                        details={"track_uuid": track_uuid},
                    )

            for track_uuid, stack in open_stacks.items():
                while stack:
                    invocation = stack.pop()
                    invocation_id = _finalize_invocation(
                        conn,
                        invocation,
                        terminal_close_kind="in_flight",
                    )
                    _record_issue(
                        conn,
                        severity="error",
                        code="final_in_flight_call",
                        packet_id=invocation.exit_packet_id or invocation.entry_packet_id,
                        event_id=invocation.exit_event_id or invocation.entry_event_id,
                        invocation_id=invocation_id,
                        message=f"{invocation.function_name} was still in flight at end of trace",
                        details={"track_uuid": track_uuid},
                    )

            open_frame_cookies: dict[int, list[int]] = {}
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
                    pending_starts.pop()
                    if not pending_starts:
                        del open_frame_cookies[cookie]
                    continue
                open_frame_cookies.setdefault(cookie, []).append(frame_event_id)

            for cookie, frame_event_ids in open_frame_cookies.items():
                for frame_event_id in frame_event_ids:
                    _record_issue(
                        conn,
                        severity="error",
                        code="frame_start_without_end",
                        message=f"frame cookie {cookie} never observed a frame_end",
                        details={"cookie": cookie, "frame_event_id": frame_event_id},
                    )

        invocation_count = conn.execute("SELECT COUNT(*) FROM oracle_invocations").fetchone()[0]
        issue_count = conn.execute("SELECT COUNT(*) FROM verification_issues").fetchone()[0]
        missing_exit_count = conn.execute(
            "SELECT COUNT(*) FROM oracle_invocations WHERE terminal_close_kind = 'missing_exit'"
        ).fetchone()[0]
        in_flight_count = conn.execute(
            "SELECT COUNT(*) FROM oracle_invocations WHERE terminal_close_kind = 'in_flight'"
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
