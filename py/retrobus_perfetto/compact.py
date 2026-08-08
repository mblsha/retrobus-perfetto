"""Decode compact target traces and reconstruct native Perfetto tracks."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path
import struct
from typing import Any, Iterator, Sequence
import zlib

from .annotations import TrackEventWrapper
from .builder import PerfettoTraceBuilder
from .compact_schema import (
    CompactArgumentSchema,
    CompactConstantArgumentSchema,
    CompactEventSchema,
    CompactSchema,
)


RBCT_MAGIC = b"RBCTRC1\0"
RBCT_CHUNK_MAGIC = b"RBCK"
FORMAT_VERSION = 1
FILE_HEADER_BYTES = 160
CHUNK_HEADER_BYTES = 48
CHUNK_BYTES = 4096
FLAG_FINALIZED = 0x0001
FLAG_RING_WRAPPED = 0x0002
CONTROL_LOSS = 0xFC
CONTROL_CLOCK_SYNC = 0xFD
CONTROL_TRACK = 0xFE
CONTROL_EXTENDED_EVENT = 0xFF


class CompactTraceError(ValueError):
    """A compact image is unsupported, corrupt, or inconsistent."""


@dataclass(frozen=True)
class CompactTraceHeader:
    source_format: str
    flags: int
    clock_rate_numerator: int
    clock_rate_denominator: int
    clock_width_bits: int
    producer_id: int
    schema_version: int
    schema_sha256: bytes
    session_id: bytes
    total_records: int
    overwritten_records: int
    dropped_records: int
    total_events: int
    overwritten_events: int
    buffer_bytes: int
    initial_generation: int
    default_track: int

    @property
    def finalized(self) -> bool:
        return bool(self.flags & FLAG_FINALIZED)

    @property
    def retained_records(self) -> int:
        return self.total_records - self.overwritten_records

    @property
    def retained_events(self) -> int:
        return self.total_events - self.overwritten_events


@dataclass(frozen=True)
class CompactClockSync:
    generation: int
    counter_before: int
    counter_after: int
    reference_timestamp_ns: int
    uncertainty_ns: int
    order: int
    extended_tick: int = 0
    synthetic: bool = False


@dataclass(frozen=True)
class CompactRecord:
    event: CompactEventSchema
    generation: int
    track_id: int
    raw_timestamp: int
    duration_ticks: int | None
    arguments: tuple[Any, ...]
    order: int
    extended_tick: int = 0

    def argument(self, name: str) -> Any:
        for specification, value in zip(self.event.arguments, self.arguments):
            if specification.name == name:
                return value
        raise CompactTraceError(
            f"event {self.event.id} does not contain argument {name!r}"
        )


@dataclass(frozen=True)
class CompactTrace:
    header: CompactTraceHeader
    schema: CompactSchema
    records: tuple[CompactRecord, ...]
    clock_syncs: tuple[CompactClockSync, ...]

    def _scale_delta(self, ticks: int) -> int:
        numerator = ticks * self.header.clock_rate_denominator * 1_000_000_000
        denominator = self.header.clock_rate_numerator
        if numerator >= 0:
            return (numerator + denominator // 2) // denominator
        return -((-numerator + denominator // 2) // denominator)

    def timestamp_ns(self, generation: int, extended_tick: int) -> int:
        anchors = [
            sync
            for sync in self.clock_syncs
            if sync.generation == generation
        ]
        if anchors:
            anchor = anchors[0]
            return anchor.reference_timestamp_ns + self._scale_delta(
                extended_tick - anchor.extended_tick
            )

        generation_records = [
            record for record in self.records if record.generation == generation
        ]
        if not generation_records:
            return 0
        first_tick = generation_records[0].extended_tick
        preceding_ns = 0
        seen: set[int] = set()
        for record in self.records:
            if record.generation == generation:
                break
            if record.generation in seen:
                continue
            seen.add(record.generation)
            records = [
                candidate
                for candidate in self.records
                if candidate.generation == record.generation
            ]
            if records:
                preceding_ns += self._scale_delta(
                    records[-1].extended_tick - records[0].extended_tick
                ) + 1
        return preceding_ns + self._scale_delta(extended_tick - first_tick)

    def duration_ns(self, ticks: int) -> int:
        return self._scale_delta(ticks)


@dataclass(frozen=True)
class _Chunk:
    physical_index: int
    sequence: int
    base_timestamp: int
    generation: int
    default_track: int
    used: int
    records: int
    events: int
    syncs: int
    crc32: int


def _read_varint(data: bytes, offset: int, limit: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < limit and shift < 70:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            return value, offset
        shift += 7
    raise CompactTraceError("truncated or oversized ULEB128 value")


def _read_argument(
    data: bytes, offset: int, limit: int, specification: CompactArgumentSchema
) -> tuple[Any, int]:
    if specification.type in {"fixed64", "float64"}:
        if limit - offset < 8:
            raise CompactTraceError(
                f"truncated fixed-width argument {specification.name!r}"
            )
        raw = data[offset : offset + 8]
        if specification.type == "float64":
            return struct.unpack("<d", raw)[0], offset + 8
        return struct.unpack("<Q", raw)[0], offset + 8
    encoded, offset = _read_varint(data, offset, limit)
    if specification.type == "sint":
        return (encoded >> 1) ^ -(encoded & 1), offset
    if specification.type == "bool":
        if encoded not in (0, 1):
            raise CompactTraceError(
                f"boolean argument {specification.name!r} is not zero or one"
            )
        return bool(encoded), offset
    return encoded, offset


def _midpoint_counter(before: int, after: int, mask: int) -> int:
    return (before + (((after - before) & mask) // 2)) & mask


def _extend_items(
    header: CompactTraceHeader,
    items: Sequence[CompactRecord | CompactClockSync],
) -> tuple[tuple[CompactRecord, ...], tuple[CompactClockSync, ...]]:
    mask = (1 << header.clock_width_bits) - 1
    state: dict[int, tuple[int, int]] = {}
    records: list[CompactRecord] = []
    syncs: list[CompactClockSync] = []
    for item in items:
        if isinstance(item, CompactRecord):
            raw = item.raw_timestamp
        else:
            raw = _midpoint_counter(item.counter_before, item.counter_after, mask)
        previous = state.get(item.generation)
        if previous is None:
            extended = raw
        else:
            previous_raw, previous_extended = previous
            extended = previous_extended + ((raw - previous_raw) & mask)
        state[item.generation] = (raw, extended)
        if isinstance(item, CompactRecord):
            records.append(replace(item, extended_tick=extended))
        else:
            syncs.append(replace(item, extended_tick=extended))
    return tuple(records), tuple(syncs)


class CompactTraceReader:
    """Scan chunk headers first, then decode bounded payloads in sequence order."""

    def __init__(
        self,
        path: Path | str,
        schema: CompactSchema,
        *,
        allow_unfinalized: bool = False,
    ) -> None:
        self.path = Path(path)
        self.schema = schema
        self.allow_unfinalized = allow_unfinalized
        self.header, self._chunks = self._read_header_and_chunks()

    def _read_header_and_chunks(self) -> tuple[CompactTraceHeader, tuple[_Chunk, ...]]:
        try:
            file_size = self.path.stat().st_size
            with self.path.open("rb") as source:
                raw_header = source.read(FILE_HEADER_BYTES)
                if len(raw_header) != FILE_HEADER_BYTES:
                    raise CompactTraceError("compact file header is truncated")
                if raw_header[:8] != RBCT_MAGIC:
                    raise CompactTraceError("not a retrobus compact trace")
                version, header_bytes, chunk_header_bytes, reserved = struct.unpack_from(
                    "<HHHH", raw_header, 8
                )
                chunk_bytes = struct.unpack_from("<I", raw_header, 16)[0]
                if (
                    version != FORMAT_VERSION
                    or header_bytes != FILE_HEADER_BYTES
                    or chunk_header_bytes != CHUNK_HEADER_BYTES
                    or chunk_bytes != CHUNK_BYTES
                    or reserved != 0
                    or raw_header[156:160] != b"\0" * 4
                ):
                    raise CompactTraceError("unsupported compact header layout")
                expected_crc = struct.unpack_from("<I", raw_header, 152)[0]
                crc_header = bytearray(raw_header)
                struct.pack_into("<I", crc_header, 152, 0)
                actual_crc = zlib.crc32(crc_header) & 0xFFFF_FFFF
                flags = struct.unpack_from("<H", raw_header, 38)[0]
                if flags & ~(FLAG_FINALIZED | FLAG_RING_WRAPPED):
                    raise CompactTraceError(f"unsupported compact flags 0x{flags:x}")
                if flags & FLAG_FINALIZED:
                    if actual_crc != expected_crc:
                        raise CompactTraceError("compact file-header CRC mismatch")
                elif not self.allow_unfinalized:
                    raise CompactTraceError("compact trace was not finalized")

                rate_numerator, rate_denominator = struct.unpack_from(
                    "<QQ", raw_header, 20
                )
                width = struct.unpack_from("<H", raw_header, 36)[0]
                producer_id, schema_version = struct.unpack_from(
                    "<II", raw_header, 40
                )
                counts = struct.unpack_from("<QQQQQQ", raw_header, 96)
                initial_generation, default_track = struct.unpack_from(
                    "<II", raw_header, 144
                )
                if rate_numerator == 0 or rate_denominator == 0 or not 1 <= width <= 64:
                    raise CompactTraceError("invalid compact clock description")
                if producer_id != self.schema.producer_id:
                    raise CompactTraceError(
                        f"producer ID {producer_id} does not match schema "
                        f"{self.schema.producer_id}"
                    )
                if schema_version != self.schema.version:
                    raise CompactTraceError(
                        f"schema version {schema_version} does not match "
                        f"{self.schema.version}"
                    )
                schema_hash = raw_header[48:80]
                if schema_hash != self.schema.sha256:
                    raise CompactTraceError("producer schema SHA-256 mismatch")
                buffer_bytes = counts[5]
                if buffer_bytes != file_size or (
                    file_size - FILE_HEADER_BYTES
                ) % CHUNK_BYTES:
                    raise CompactTraceError("compact buffer size does not match file size")
                if default_track not in self.schema.tracks:
                    raise CompactTraceError(f"unknown default track {default_track}")

                chunks: list[_Chunk] = []
                chunk_count = (file_size - FILE_HEADER_BYTES) // CHUNK_BYTES
                for physical_index in range(chunk_count):
                    source.seek(FILE_HEADER_BYTES + physical_index * CHUNK_BYTES)
                    chunk_header = source.read(CHUNK_HEADER_BYTES)
                    if chunk_header == b"\0" * CHUNK_HEADER_BYTES:
                        continue
                    if chunk_header[:4] != RBCT_CHUNK_MAGIC:
                        raise CompactTraceError(
                            f"invalid chunk magic at physical chunk {physical_index}"
                        )
                    sequence, base = struct.unpack_from("<QQ", chunk_header, 4)
                    generation, chunk_track = struct.unpack_from("<II", chunk_header, 20)
                    used, records = struct.unpack_from("<HH", chunk_header, 28)
                    events = struct.unpack_from("<I", chunk_header, 32)[0]
                    syncs, chunk_reserved = struct.unpack_from("<HH", chunk_header, 36)
                    payload_crc, final_reserved = struct.unpack_from(
                        "<II", chunk_header, 40
                    )
                    if used > CHUNK_BYTES - CHUNK_HEADER_BYTES:
                        raise CompactTraceError(f"chunk {sequence} payload exceeds bounds")
                    if chunk_reserved != 0 or final_reserved != 0:
                        raise CompactTraceError(f"chunk {sequence} reserved fields are nonzero")
                    if chunk_track not in self.schema.tracks:
                        raise CompactTraceError(
                            f"chunk {sequence} uses unknown track {chunk_track}"
                        )
                    chunks.append(
                        _Chunk(
                            physical_index,
                            sequence,
                            base,
                            generation,
                            chunk_track,
                            used,
                            records,
                            events,
                            syncs,
                            payload_crc,
                        )
                    )
        except OSError as error:
            raise CompactTraceError(f"cannot read compact trace {self.path}: {error}") from error

        chunks.sort(key=lambda chunk: chunk.sequence)
        for previous, current in zip(chunks, chunks[1:]):
            if current.sequence != previous.sequence + 1:
                raise CompactTraceError("compact chunk sequence is not contiguous")
        total_records, overwritten_records, dropped_records = counts[:3]
        total_events, overwritten_events = counts[3:5]
        if overwritten_records > total_records or overwritten_events > total_events:
            raise CompactTraceError("compact overwrite counts exceed total counts")
        header = CompactTraceHeader(
            source_format="retrobus-compact-v1",
            flags=flags,
            clock_rate_numerator=rate_numerator,
            clock_rate_denominator=rate_denominator,
            clock_width_bits=width,
            producer_id=producer_id,
            schema_version=schema_version,
            schema_sha256=schema_hash,
            session_id=raw_header[80:96],
            total_records=total_records,
            overwritten_records=overwritten_records,
            dropped_records=dropped_records,
            total_events=total_events,
            overwritten_events=overwritten_events,
            buffer_bytes=buffer_bytes,
            initial_generation=initial_generation,
            default_track=default_track,
        )
        return header, tuple(chunks)

    def iter_items(self) -> Iterator[CompactRecord | CompactClockSync]:
        order = 0
        retained_records = 0
        retained_events = 0
        try:
            with self.path.open("rb") as source:
                for chunk in self._chunks:
                    source.seek(
                        FILE_HEADER_BYTES
                        + chunk.physical_index * CHUNK_BYTES
                        + CHUNK_HEADER_BYTES
                    )
                    payload = source.read(chunk.used)
                    if len(payload) != chunk.used:
                        raise CompactTraceError(f"chunk {chunk.sequence} is truncated")
                    if self.header.finalized and (
                        zlib.crc32(payload) & 0xFFFF_FFFF
                    ) != chunk.crc32:
                        raise CompactTraceError(f"chunk {chunk.sequence} CRC mismatch")
                    offset = 0
                    timestamp = chunk.base_timestamp
                    track_id = chunk.default_track
                    chunk_records = 0
                    chunk_events = 0
                    chunk_syncs = 0
                    mask = (1 << self.header.clock_width_bits) - 1
                    while offset < len(payload):
                        lead = payload[offset]
                        offset += 1
                        if lead == CONTROL_TRACK:
                            track_id, offset = _read_varint(payload, offset, len(payload))
                            if track_id not in self.schema.tracks:
                                raise CompactTraceError(
                                    f"chunk {chunk.sequence} selects unknown track {track_id}"
                                )
                            continue
                        if lead == CONTROL_CLOCK_SYNC:
                            generation, offset = _read_varint(payload, offset, len(payload))
                            before, offset = _read_varint(payload, offset, len(payload))
                            after, offset = _read_varint(payload, offset, len(payload))
                            reference_ns, offset = _read_varint(
                                payload, offset, len(payload)
                            )
                            uncertainty_ns, offset = _read_varint(
                                payload, offset, len(payload)
                            )
                            if generation != chunk.generation:
                                raise CompactTraceError(
                                    f"chunk {chunk.sequence} clock sync generation mismatch"
                                )
                            if before & ~mask or after & ~mask:
                                raise CompactTraceError(
                                    f"chunk {chunk.sequence} clock sync exceeds counter width"
                                )
                            yield CompactClockSync(
                                generation,
                                before,
                                after,
                                reference_ns,
                                uncertainty_ns,
                                order,
                            )
                            order += 1
                            chunk_syncs += 1
                            continue
                        if lead == CONTROL_LOSS:
                            raise CompactTraceError("version 1 loss control is reserved")
                        if lead == CONTROL_EXTENDED_EVENT:
                            event_id, offset = _read_varint(payload, offset, len(payload))
                        else:
                            event_id = lead
                        event = self.schema.events.get(event_id)
                        if event is None:
                            raise CompactTraceError(f"unknown compact event ID {event_id}")
                        delta, offset = _read_varint(payload, offset, len(payload))
                        timestamp = (timestamp + delta) & mask
                        duration: int | None = None
                        if event.kind == "slice":
                            duration, offset = _read_varint(payload, offset, len(payload))
                        arguments: list[Any] = []
                        for argument in event.arguments:
                            value, offset = _read_argument(
                                payload, offset, len(payload), argument
                            )
                            arguments.append(value)
                        yield CompactRecord(
                            event,
                            chunk.generation,
                            track_id,
                            timestamp,
                            duration,
                            tuple(arguments),
                            order,
                        )
                        order += 1
                        chunk_records += 1
                        chunk_events += 2 if event.kind == "slice" else 1
                    if (
                        chunk_records != chunk.records
                        or chunk_events != chunk.events
                        or chunk_syncs != chunk.syncs
                    ):
                        raise CompactTraceError(
                            f"chunk {chunk.sequence} record/event/sync count mismatch"
                        )
                    retained_records += chunk_records
                    retained_events += chunk_events
        except OSError as error:
            raise CompactTraceError(f"cannot read compact trace {self.path}: {error}") from error
        if self.header.finalized and retained_records != self.header.retained_records:
            raise CompactTraceError("file-level retained record count mismatch")
        if self.header.finalized and retained_events != self.header.retained_events:
            raise CompactTraceError("file-level retained event count mismatch")

    def read(self) -> CompactTrace:
        records, syncs = _extend_items(self.header, tuple(self.iter_items()))
        header = self.header
        if not header.finalized:
            retained_events = sum(
                2 if record.event.kind == "slice" else 1 for record in records
            )
            header = replace(
                header,
                total_records=len(records),
                overwritten_records=0,
                dropped_records=0,
                total_events=retained_events,
                overwritten_events=0,
            )
        return CompactTrace(header, self.schema, records, syncs)


def read_compact_trace(
    path: Path | str,
    schema: CompactSchema | Path | str,
    *,
    allow_unfinalized: bool = False,
) -> CompactTrace:
    """Read and validate a producer-neutral `.rbct` image."""
    producer_schema = (
        schema if isinstance(schema, CompactSchema) else CompactSchema.load(schema)
    )
    source = Path(path)
    try:
        with source.open("rb") as file:
            magic = file.read(8)
    except OSError as error:
        raise CompactTraceError(f"cannot read compact trace {source}: {error}") from error
    if magic != RBCT_MAGIC:
        raise CompactTraceError("unrecognized compact trace magic")
    return CompactTraceReader(
        source, producer_schema, allow_unfinalized=allow_unfinalized
    ).read()


@dataclass(frozen=True)
class _Action:
    timestamp_ns: int
    phase: int
    nesting: int
    order: int
    action: str
    record: CompactRecord | None = None
    sync: CompactClockSync | None = None


def _add_category(wrapper: TrackEventWrapper, category: str) -> None:
    if category:
        wrapper.event.categories.append(category)


def _add_typed_annotation(
    wrapper: TrackEventWrapper,
    specification: CompactArgumentSchema | CompactConstantArgumentSchema,
    value: Any,
) -> None:
    annotation = wrapper.event.debug_annotations.add()
    annotation.name = specification.name
    if specification.type == "bool":
        annotation.bool_value = value
    elif specification.type == "float64":
        annotation.double_value = value
    elif specification.type == "fixed64" or (
        specification.type == "uint" and value > 0x7FFF_FFFF_FFFF_FFFF
    ):
        annotation.pointer_value = value
    else:
        annotation.int_value = value


def _add_arguments(wrapper: TrackEventWrapper, record: CompactRecord) -> None:
    if record.event.id_argument is not None:
        annotation = wrapper.event.debug_annotations.add()
        annotation.name = record.event.id_argument
        annotation.int_value = record.event.id
    for constant_specification in record.event.constant_arguments:
        _add_typed_annotation(
            wrapper, constant_specification, constant_specification.value
        )
    for stored_specification, value in zip(
        record.event.arguments, record.arguments
    ):
        _add_typed_annotation(wrapper, stored_specification, value)


def _correlation_value(record: CompactRecord) -> int:
    name = record.event.correlation_argument
    if name is None:
        raise CompactTraceError(
            f"event {record.event.id} lacks a correlation argument"
        )
    value = record.argument(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CompactTraceError(
            f"event {record.event.id} correlation value is not an unsigned integer"
        )
    return value


def compact_trace_to_builder(
    trace: CompactTrace, *, normalize_start: bool = False
) -> PerfettoTraceBuilder:
    """Reconstruct a compact capture as ordinary Perfetto TrackEvent packets."""
    builder = PerfettoTraceBuilder(trace.schema.process_name, encoding="inline")
    track_uuids: dict[int, int] = {}
    for track in sorted(trace.schema.tracks.values(), key=lambda value: value.id):
        if track.kind == "counter":
            track_uuids[track.id] = builder.add_counter_track(track.name, track.unit)
        else:
            track_uuids[track.id] = builder.add_thread(track.name)

    async_tracks: dict[tuple[int, str, int], int] = {}
    for record in trace.records:
        if record.event.kind.startswith("async_"):
            correlation = _correlation_value(record)
            key = (record.track_id, record.event.name, correlation)
            if key not in async_tracks:
                base = trace.schema.tracks[record.track_id].name
                async_tracks[key] = builder.add_thread(
                    f"{base}: {record.event.name} [{correlation}]"
                )

    clock_track: int | None = None
    visible_syncs = [sync for sync in trace.clock_syncs if not sync.synthetic]
    if visible_syncs:
        clock_track = builder.add_thread("Clock correlation")

    actions: list[_Action] = []
    for record in trace.records:
        timestamp = trace.timestamp_ns(record.generation, record.extended_tick)
        if record.event.kind == "slice":
            assert record.duration_ticks is not None
            duration = trace.duration_ns(record.duration_ticks)
            start = timestamp - duration
            actions.append(
                _Action(start, 2, -duration, record.order * 2, "slice_begin", record)
            )
            end_phase = 3 if duration == 0 else 0
            actions.append(
                _Action(timestamp, end_phase, duration, record.order * 2 + 1,
                        "slice_end", record)
            )
        elif record.event.kind == "async_begin":
            actions.append(_Action(timestamp, 2, 0, record.order, "async_begin", record))
        elif record.event.kind == "async_end":
            actions.append(_Action(timestamp, 0, 0, record.order, "async_end", record))
        else:
            actions.append(_Action(timestamp, 1, 0, record.order, record.event.kind, record))
    for sync in visible_syncs:
        timestamp = trace.timestamp_ns(sync.generation, sync.extended_tick)
        actions.append(_Action(timestamp, 1, 0, sync.order, "clock_sync", sync=sync))

    if normalize_start and actions:
        first = min(action.timestamp_ns for action in actions)
        actions = [replace(action, timestamp_ns=action.timestamp_ns - first) for action in actions]
    actions.sort(
        key=lambda action: (
            action.timestamp_ns,
            action.phase,
            action.nesting,
            action.order,
        )
    )

    for action in actions:
        if action.action == "clock_sync":
            assert action.sync is not None and clock_track is not None
            wrapper = builder.add_instant_event(
                clock_track, "clock sync", action.timestamp_ns
            )
            wrapper.event.categories.append("clock")
            wrapper.add_annotations(
                {
                    "generation": action.sync.generation,
                    "counter_before": action.sync.counter_before,
                    "counter_after": action.sync.counter_after,
                    "reference_timestamp_ns": action.sync.reference_timestamp_ns,
                    "uncertainty_ns": action.sync.uncertainty_ns,
                }
            )
            continue
        assert action.record is not None
        record = action.record
        base_track = track_uuids.get(record.track_id)
        if base_track is None:
            raise CompactTraceError(f"record uses unknown track {record.track_id}")
        event = record.event
        if action.action == "slice_begin":
            wrapper = builder.begin_slice(base_track, event.name, action.timestamp_ns)
            _add_category(wrapper, event.category)
            _add_arguments(wrapper, record)
        elif action.action == "slice_end":
            builder.end_slice(base_track, action.timestamp_ns)
        elif action.action == "instant":
            wrapper = builder.add_instant_event(base_track, event.name, action.timestamp_ns)
            _add_category(wrapper, event.category)
            _add_arguments(wrapper, record)
        elif action.action == "counter":
            if trace.schema.tracks[record.track_id].kind != "counter":
                raise CompactTraceError(
                    f"counter event {event.id} was recorded on a non-counter track"
                )
            if (
                isinstance(record.arguments[0], int)
                and record.arguments[0] > 0x7FFF_FFFF_FFFF_FFFF
            ):
                raise CompactTraceError(
                    f"counter event {event.id} exceeds Perfetto's signed 64-bit range"
                )
            builder.update_counter(base_track, record.arguments[0], action.timestamp_ns)
        elif action.action in {"flow_start", "flow_step", "flow_end"}:
            wrapper = builder.add_flow(
                base_track,
                event.name,
                action.timestamp_ns,
                _correlation_value(record),
                terminating=action.action == "flow_end",
            )
            _add_category(wrapper, event.category)
            _add_arguments(wrapper, record)
        elif action.action in {"async_begin", "async_end"}:
            key = (record.track_id, event.name, _correlation_value(record))
            async_track_uuid = async_tracks[key]
            if action.action == "async_begin":
                wrapper = builder.begin_slice(
                    async_track_uuid, event.name, action.timestamp_ns
                )
            else:
                packet = builder._add_track_event(  # noqa: SLF001
                    async_track_uuid,
                    action.timestamp_ns,
                    2,
                )
                wrapper = TrackEventWrapper(packet.track_event)
            _add_category(wrapper, event.category)
            _add_arguments(wrapper, record)
        else:
            raise CompactTraceError(f"unsupported reconstructed action {action.action!r}")
    return builder


def convert_compact_trace(
    input_path: Path | str,
    schema_path: CompactSchema | Path | str,
    output_path: Path | str,
    *,
    normalize_start: bool = False,
    allow_unfinalized: bool = False,
) -> dict[str, Any]:
    """Decode, validate, reconstruct, and atomically publish a Perfetto trace."""
    trace = read_compact_trace(
        input_path, schema_path, allow_unfinalized=allow_unfinalized
    )
    builder = compact_trace_to_builder(trace, normalize_start=normalize_start)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.name}.partial.{os.getpid()}")
    serialized = builder.serialize()
    try:
        temporary.write_bytes(serialized)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "format": trace.header.source_format,
        "producer": trace.schema.producer_name,
        "schema_version": trace.schema.version,
        "input_bytes": Path(input_path).stat().st_size,
        "output_bytes": len(serialized),
        "records": trace.header.total_records,
        "retained_records": trace.header.retained_records,
        "events": trace.header.total_events,
        "retained_events": trace.header.retained_events,
        "overwritten_records": trace.header.overwritten_records,
        "dropped_records": trace.header.dropped_records,
        "clock_syncs": len(trace.clock_syncs),
    }
