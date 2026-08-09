"""Decode compact target traces and reconstruct native Perfetto tracks."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field, replace
import math
import os
from pathlib import Path
import struct
import tempfile
from typing import Any, BinaryIO, Iterator, Mapping, Sequence
import zlib

from .annotations import TrackEventWrapper
from .builder import PerfettoTraceBuilder
from .compact_schema import (
    CompactArgumentSchema,
    CompactConstantArgumentSchema,
    CompactEventSchema,
    CompactSchema,
)


RBCT_MAGIC_V1 = b"RBCTRC1\0"
RBCT_MAGIC_V2 = b"RBCTRC2\0"
RBCT_MAGIC = RBCT_MAGIC_V2
RBCT_MAGICS = frozenset((RBCT_MAGIC_V1, RBCT_MAGIC_V2))
RBCT_CHUNK_MAGIC = b"RBCK"
LEGACY_FORMAT_VERSION = 1
FORMAT_VERSION = 2
FILE_HEADER_BYTES = 160
CHUNK_HEADER_BYTES = 48
CHUNK_BYTES = 4096
RECORD_FRAME_BYTES = 1
MAX_RECORD_BYTES = 70
FRAME_DELTA_ZERO_BASE = MAX_RECORD_BYTES
FRAME_DELTA_ONE_BASE = 2 * MAX_RECORD_BYTES
FRAME_DELTA_ONE_LIMIT = FRAME_DELTA_ONE_BASE + MAX_RECORD_BYTES
FRAME_INLINE_ZERO_BASE = FRAME_DELTA_ONE_LIMIT
FRAME_INLINE_ONE_BASE = FRAME_INLINE_ZERO_BASE + 22
FRAME_INLINE_ONE_LIMIT = FRAME_INLINE_ONE_BASE + 22
FLAG_FINALIZED = 0x0001
FLAG_RING_WRAPPED = 0x0002
FLAG_CHUNK_HEADER_CRC = 0x0004
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
    def ring_wrapped(self) -> bool:
        return bool(self.flags & FLAG_RING_WRAPPED)

    @property
    def format_version(self) -> int:
        return (
            FORMAT_VERSION
            if self.source_format.endswith("v2")
            else LEGACY_FORMAT_VERSION
        )

    @property
    def strict_clock(self) -> bool:
        return self.format_version >= FORMAT_VERSION

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
    _anchors: Mapping[int, tuple[tuple[int, ...], tuple[CompactClockSync, ...]]] = (
        field(init=False, repr=False, compare=False)
    )
    _relative_origins: Mapping[int, tuple[int, int]] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.header.strict_clock:
            ordered_syncs = sorted(self.clock_syncs, key=lambda sync: sync.order)
            for previous, current in zip(ordered_syncs, ordered_syncs[1:]):
                if current.reference_timestamp_ns < previous.reference_timestamp_ns:
                    raise CompactTraceError("clock reference time moves backwards")
        anchors: dict[int, list[CompactClockSync]] = {}
        for sync in self.clock_syncs:
            anchors.setdefault(sync.generation, []).append(sync)
        anchor_index: dict[
            int, tuple[tuple[int, ...], tuple[CompactClockSync, ...]]
        ] = {}
        for generation, generation_syncs in anchors.items():
            if not self.header.strict_clock:
                first_sync = min(generation_syncs, key=lambda sync: sync.order)
                anchor_index[generation] = (
                    (first_sync.extended_tick,),
                    (first_sync,),
                )
                continue
            sorted_syncs = sorted(generation_syncs, key=lambda sync: sync.extended_tick)
            for previous, current in zip(sorted_syncs, sorted_syncs[1:]):
                if current.extended_tick <= previous.extended_tick:
                    raise CompactTraceError(
                        f"clock generation {generation} has non-advancing anchors"
                    )
                if current.reference_timestamp_ns < previous.reference_timestamp_ns:
                    raise CompactTraceError(
                        f"clock generation {generation} has backwards references"
                    )
            anchor_index[generation] = (
                tuple(sync.extended_tick for sync in sorted_syncs),
                tuple(sorted_syncs),
            )

        spans: dict[int, tuple[int, int]] = {}
        for record in self.records:
            first = record.extended_tick
            if record.duration_ticks is not None:
                first -= record.duration_ticks
            span = spans.get(record.generation)
            if span is None:
                spans[record.generation] = (first, record.extended_tick)
            else:
                spans[record.generation] = (
                    min(span[0], first),
                    max(span[1], record.extended_tick),
                )
        relative_origins: dict[int, tuple[int, int]] = {}
        offset_ns = 0
        for generation, (first_tick, last_tick) in spans.items():
            relative_origins[generation] = (first_tick, offset_ns)
            offset_ns += self._scale_delta(last_tick - first_tick) + 1

        object.__setattr__(self, "_anchors", anchor_index)
        object.__setattr__(self, "_relative_origins", relative_origins)
        if self.header.strict_clock:
            if self.clock_syncs:
                missing_generations = tuple(
                    dict.fromkeys(
                        record.generation
                        for record in self.records
                        if record.generation not in anchor_index
                    )
                )
                ordered_observations: list[CompactRecord | CompactClockSync] = sorted(
                    (*self.records, *self.clock_syncs), key=lambda item: item.order
                )
                first_generation = (
                    ordered_observations[0].generation if ordered_observations else None
                )
                if missing_generations and (
                    not self.header.ring_wrapped
                    or missing_generations != (first_generation,)
                ):
                    raise CompactTraceError(
                        f"clock generation {missing_generations[0]} has no correlation anchor"
                    )
                if missing_generations:
                    missing_generation = missing_generations[0]
                    next_anchored = next(
                        (
                            observation
                            for observation in ordered_observations
                            if observation.generation in anchor_index
                        ),
                        None,
                    )
                    if next_anchored is None:
                        raise CompactTraceError(
                            f"clock generation {missing_generation} has no usable "
                            "correlation successor"
                        )
                    first_tick, last_tick = spans[missing_generation]
                    next_timestamp = self.timestamp_ns(
                        next_anchored.generation, next_anchored.extended_tick
                    )
                    prefix_origin = next_timestamp - self._scale_delta(
                        last_tick - first_tick
                    )
                    if prefix_origin < 0:
                        raise CompactTraceError(
                            "wrapped unanchored prefix cannot be placed before its "
                            "correlation successor"
                        )
                    relative_origins[missing_generation] = (
                        first_tick,
                        prefix_origin,
                    )
                    object.__setattr__(self, "_relative_origins", relative_origins)
            previous_timestamp: int | None = None
            observations: list[CompactRecord | CompactClockSync] = [
                *self.records,
                *self.clock_syncs,
            ]
            for observation in sorted(observations, key=lambda item: item.order):
                timestamp = self.timestamp_ns(
                    observation.generation, observation.extended_tick
                )
                if previous_timestamp is not None and timestamp < previous_timestamp:
                    raise CompactTraceError("mapped clock time moves backwards")
                previous_timestamp = timestamp

    def _scale_delta(self, ticks: int) -> int:
        numerator = ticks * self.header.clock_rate_denominator * 1_000_000_000
        denominator = self.header.clock_rate_numerator
        if numerator >= 0:
            return (numerator + denominator // 2) // denominator
        return -((-numerator + denominator // 2) // denominator)

    def timestamp_ns(self, generation: int, extended_tick: int) -> int:
        anchor_index = self._anchors.get(generation)
        if anchor_index is not None:
            ticks, anchors = anchor_index
            insertion = bisect_left(ticks, extended_tick)
            if insertion == 0:
                anchor = anchors[0]
                return anchor.reference_timestamp_ns + self._scale_delta(
                    extended_tick - anchor.extended_tick
                )
            if insertion == len(anchors):
                anchor = anchors[-1]
                return anchor.reference_timestamp_ns + self._scale_delta(
                    extended_tick - anchor.extended_tick
                )
            before = anchors[insertion - 1]
            after = anchors[insertion]
            elapsed_ticks = extended_tick - before.extended_tick
            span_ticks = after.extended_tick - before.extended_tick
            span_ns = after.reference_timestamp_ns - before.reference_timestamp_ns
            return (
                before.reference_timestamp_ns
                + (elapsed_ticks * span_ns + span_ticks // 2) // span_ticks
            )

        relative_origin = self._relative_origins.get(generation)
        if relative_origin is None:
            return 0
        first_tick, preceding_ns = relative_origin
        return preceding_ns + self._scale_delta(extended_tick - first_tick)

    def duration_ns(self, ticks: int) -> int:
        return self._scale_delta(ticks)

    @property
    def uncorrelated_generations(self) -> tuple[int, ...]:
        """Clock generations reconstructed without a retained absolute anchor."""
        anchored = set(self._anchors)
        return tuple(
            dict.fromkeys(
                record.generation
                for record in self.records
                if record.generation not in anchored
            )
        )


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


def _read_varint(
    data: bytes, offset: int, limit: int, *, canonical: bool = True
) -> tuple[int, int]:
    value = 0
    for index in range(10):
        if offset >= limit:
            break
        byte = data[offset]
        offset += 1
        if index == 9 and byte > 1:
            raise CompactTraceError("ULEB128 value exceeds unsigned 64-bit range")
        value |= (byte & 0x7F) << (index * 7)
        if byte & 0x80 == 0:
            if canonical and index and byte == 0:
                raise CompactTraceError("ULEB128 value is not canonically encoded")
            return value, offset
    raise CompactTraceError("truncated or oversized ULEB128 value")


def _read_argument(
    data: bytes,
    offset: int,
    limit: int,
    specification: CompactArgumentSchema,
    *,
    canonical: bool = True,
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
    encoded, offset = _read_varint(data, offset, limit, canonical=canonical)
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
    half_range = 1 << (header.clock_width_bits - 1)
    state: dict[int, tuple[int, int]] = {}
    strict = header.strict_clock
    closed_generations: set[int] = set()
    active_generation: int | None = None
    first_retained_generation: int | None = None
    generation_has_record = False
    generation_has_sync = False
    records: list[CompactRecord] = []
    syncs: list[CompactClockSync] = []
    for item in items:
        if strict and item.generation != active_generation:
            if item.generation in closed_generations:
                raise CompactTraceError(
                    f"clock generation {item.generation} reappears after a transition"
                )
            if active_generation is not None:
                closed_generations.add(active_generation)
                if item.generation != (active_generation + 1) & 0xFFFF_FFFF:
                    raise CompactTraceError(
                        f"clock generation jumps from {active_generation} "
                        f"to {item.generation}"
                    )
                if not isinstance(item, CompactClockSync):
                    raise CompactTraceError(
                        f"clock generation {item.generation} does not start with "
                        "a synchronization record"
                    )
            elif (
                not header.ring_wrapped
                and item.generation != header.initial_generation
                and not (
                    isinstance(item, CompactClockSync)
                    and item.generation == (header.initial_generation + 1) & 0xFFFF_FFFF
                )
            ):
                raise CompactTraceError(
                    f"first clock generation {item.generation} is inconsistent with "
                    f"initial generation {header.initial_generation}"
                )
            active_generation = item.generation
            if first_retained_generation is None:
                first_retained_generation = item.generation
            generation_has_record = False
            generation_has_sync = False
        if strict:
            if isinstance(item, CompactClockSync):
                if (
                    generation_has_record
                    and not generation_has_sync
                    and not (
                        header.ring_wrapped
                        and item.generation == first_retained_generation
                    )
                ):
                    raise CompactTraceError(
                        f"clock generation {item.generation} first synchronizes "
                        "after a data record"
                    )
                generation_has_sync = True
            else:
                generation_has_record = True
        if isinstance(item, CompactRecord):
            raw = item.raw_timestamp
        else:
            raw = _midpoint_counter(item.counter_before, item.counter_after, mask)
        previous = state.get(item.generation)
        if previous is None:
            extended = raw
        else:
            previous_raw, previous_extended = previous
            delta = (raw - previous_raw) & mask
            if strict and delta >= half_range:
                raise CompactTraceError(
                    f"clock generation {item.generation} has an ambiguous counter gap"
                )
            extended = previous_extended + delta
        state[item.generation] = (raw, extended)
        if isinstance(item, CompactRecord):
            records.append(replace(item, extended_tick=extended))
        else:
            syncs.append(replace(item, extended_tick=extended))
    return tuple(records), tuple(syncs)


def _decode_one_record(
    data: bytes,
    offset: int,
    limit: int,
    *,
    chunk: _Chunk,
    schema: CompactSchema,
    clock_width_bits: int,
    timestamp: int,
    track_id: int,
    order: int,
    strict: bool,
    implicit_delta: int | None = None,
    inline_event_id: int | None = None,
) -> tuple[CompactRecord | CompactClockSync, int, int, int]:
    mask = (1 << clock_width_bits) - 1
    half_range = 1 << (clock_width_bits - 1)
    selected_track = False
    while offset < limit or inline_event_id is not None:
        if inline_event_id is None:
            lead = data[offset]
            offset += 1
        else:
            lead = inline_event_id
            inline_event_id = None
        if lead == CONTROL_TRACK:
            selected, offset = _read_varint(data, offset, limit, canonical=strict)
            if strict and (selected_track or selected == track_id):
                raise CompactTraceError(
                    f"chunk {chunk.sequence} has a non-canonical track selection"
                )
            if selected not in schema.tracks:
                raise CompactTraceError(
                    f"chunk {chunk.sequence} selects unknown track {selected}"
                )
            track_id = selected
            selected_track = True
            continue
        if lead == CONTROL_CLOCK_SYNC:
            if strict and implicit_delta is not None:
                raise CompactTraceError("clock sync uses an implicit event delta")
            if strict and selected_track:
                raise CompactTraceError(
                    f"chunk {chunk.sequence} selects a track before clock sync"
                )
            generation, offset = _read_varint(data, offset, limit, canonical=strict)
            before, offset = _read_varint(data, offset, limit, canonical=strict)
            after, offset = _read_varint(data, offset, limit, canonical=strict)
            reference_ns, offset = _read_varint(data, offset, limit, canonical=strict)
            uncertainty_ns, offset = _read_varint(data, offset, limit, canonical=strict)
            if generation != chunk.generation:
                raise CompactTraceError(
                    f"chunk {chunk.sequence} clock sync generation mismatch"
                )
            if strict and (before & ~mask or after & ~mask):
                raise CompactTraceError(
                    f"chunk {chunk.sequence} clock sync exceeds counter width"
                )
            if strict and ((after - before) & mask) >= half_range:
                raise CompactTraceError(
                    f"chunk {chunk.sequence} clock sync interval is ambiguous"
                )
            return (
                CompactClockSync(
                    generation,
                    before,
                    after,
                    reference_ns,
                    uncertainty_ns,
                    order,
                ),
                offset,
                _midpoint_counter(before, after, mask) if strict else timestamp,
                track_id,
            )
        if lead == CONTROL_LOSS:
            raise CompactTraceError("loss control is reserved")
        if lead == CONTROL_EXTENDED_EVENT:
            event_id, offset = _read_varint(data, offset, limit, canonical=strict)
            if strict and event_id <= 251:
                raise CompactTraceError(
                    f"event ID {event_id} uses a non-canonical extended encoding"
                )
        else:
            event_id = lead
        event = schema.events.get(event_id)
        if event is None:
            raise CompactTraceError(f"unknown compact event ID {event_id}")
        if implicit_delta is None:
            delta, offset = _read_varint(data, offset, limit, canonical=strict)
            if strict and delta <= 1:
                raise CompactTraceError(
                    "event uses a non-canonical explicit timestamp delta"
                )
        else:
            delta = implicit_delta
        if strict and delta & ~mask:
            raise CompactTraceError(
                f"event {event.id} timestamp delta exceeds counter width"
            )
        timestamp = (timestamp + delta) & mask
        duration: int | None = None
        if event.kind == "slice":
            duration, offset = _read_varint(data, offset, limit, canonical=strict)
            if strict and duration >= half_range:
                raise CompactTraceError(f"slice event {event.id} duration is ambiguous")
        arguments: list[Any] = []
        for argument in event.arguments:
            value, offset = _read_argument(
                data, offset, limit, argument, canonical=strict
            )
            arguments.append(value)

        track = schema.tracks[track_id]
        is_counter = event.kind == "counter"
        if is_counter != (track.kind == "counter"):
            raise CompactTraceError(
                f"event {event.id} is incompatible with {track.kind} track {track_id}"
            )
        if is_counter:
            value = arguments[0]
            if isinstance(value, int) and value > 0x7FFF_FFFF_FFFF_FFFF:
                raise CompactTraceError(
                    f"counter event {event.id} exceeds Perfetto's signed 64-bit range"
                )
            if isinstance(value, float) and not math.isfinite(value):
                raise CompactTraceError(
                    f"counter event {event.id} has a non-finite value"
                )
        return (
            CompactRecord(
                event,
                chunk.generation,
                track_id,
                timestamp,
                duration,
                tuple(arguments),
                order,
            ),
            offset,
            timestamp,
            track_id,
        )
    raise CompactTraceError(f"chunk {chunk.sequence} ends after a track selection")


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
        self._file_identity: tuple[int, int, int, int, int]
        self.header, self._chunks = self._read_header_and_chunks()

    @staticmethod
    def _identity(source: BinaryIO) -> tuple[int, int, int, int, int]:
        status = os.fstat(source.fileno())
        return (
            status.st_dev,
            status.st_ino,
            status.st_size,
            status.st_mtime_ns,
            status.st_ctime_ns,
        )

    def _read_header_and_chunks(self) -> tuple[CompactTraceHeader, tuple[_Chunk, ...]]:
        try:
            with self.path.open("rb") as source:
                self._file_identity = self._identity(source)
                file_size = self._file_identity[2]
                raw_header = source.read(FILE_HEADER_BYTES)
                if len(raw_header) != FILE_HEADER_BYTES:
                    raise CompactTraceError("compact file header is truncated")
                magic = raw_header[:8]
                if magic not in RBCT_MAGICS:
                    raise CompactTraceError("not a retrobus compact trace")
                version, header_bytes, chunk_header_bytes, reserved = (
                    struct.unpack_from("<HHHH", raw_header, 8)
                )
                chunk_bytes = struct.unpack_from("<I", raw_header, 16)[0]
                if (
                    version not in (LEGACY_FORMAT_VERSION, FORMAT_VERSION)
                    or magic
                    != (RBCT_MAGIC_V2 if version == FORMAT_VERSION else RBCT_MAGIC_V1)
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
                if flags & ~(
                    FLAG_FINALIZED | FLAG_RING_WRAPPED | FLAG_CHUNK_HEADER_CRC
                ):
                    raise CompactTraceError(f"unsupported compact flags 0x{flags:x}")
                if version == LEGACY_FORMAT_VERSION and flags & FLAG_CHUNK_HEADER_CRC:
                    raise CompactTraceError(
                        "version 1 compact trace declares version 2 chunk-header CRCs"
                    )
                if (
                    version == FORMAT_VERSION
                    and flags & FLAG_FINALIZED
                    and not flags & FLAG_CHUNK_HEADER_CRC
                ):
                    raise CompactTraceError(
                        "finalized version 2 compact trace lacks chunk-header CRCs"
                    )
                if flags & FLAG_FINALIZED:
                    if actual_crc != expected_crc:
                        if self.allow_unfinalized:
                            flags &= ~FLAG_FINALIZED
                        else:
                            raise CompactTraceError("compact file-header CRC mismatch")
                elif not self.allow_unfinalized:
                    raise CompactTraceError("compact trace was not finalized")
                recovering = self.allow_unfinalized and not bool(flags & FLAG_FINALIZED)

                rate_numerator, rate_denominator = struct.unpack_from(
                    "<QQ", raw_header, 20
                )
                width = struct.unpack_from("<H", raw_header, 36)[0]
                producer_id, schema_version = struct.unpack_from("<II", raw_header, 40)
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
                if (
                    buffer_bytes != file_size
                    or (file_size - FILE_HEADER_BYTES) % CHUNK_BYTES
                    or file_size < FILE_HEADER_BYTES + CHUNK_BYTES
                ):
                    raise CompactTraceError(
                        "compact buffer size does not match file size"
                    )
                if default_track not in self.schema.tracks:
                    raise CompactTraceError(f"unknown default track {default_track}")

                chunks: list[_Chunk] = []
                chunk_count = (file_size - FILE_HEADER_BYTES) // CHUNK_BYTES
                mask = (1 << width) - 1
                for physical_index in range(chunk_count):
                    source.seek(FILE_HEADER_BYTES + physical_index * CHUNK_BYTES)
                    chunk_header = source.read(CHUNK_HEADER_BYTES)
                    if chunk_header == b"\0" * CHUNK_HEADER_BYTES:
                        if flags & FLAG_FINALIZED:
                            unused_payload = source.read(
                                CHUNK_BYTES - CHUNK_HEADER_BYTES
                            )
                            if len(unused_payload) != CHUNK_BYTES - CHUNK_HEADER_BYTES:
                                raise CompactTraceError(
                                    f"unused physical chunk {physical_index} is truncated"
                                )
                            if unused_payload != b"\0" * len(unused_payload):
                                raise CompactTraceError(
                                    f"unused physical chunk {physical_index} is nonzero"
                                )
                        continue
                    if chunk_header[:4] != RBCT_CHUNK_MAGIC:
                        if recovering:
                            continue
                        raise CompactTraceError(
                            f"invalid chunk magic at physical chunk {physical_index}"
                        )
                    sequence, base = struct.unpack_from("<QQ", chunk_header, 4)
                    generation, chunk_track = struct.unpack_from(
                        "<II", chunk_header, 20
                    )
                    used, records = struct.unpack_from("<HH", chunk_header, 28)
                    events = struct.unpack_from("<I", chunk_header, 32)[0]
                    syncs, chunk_reserved = struct.unpack_from("<HH", chunk_header, 36)
                    payload_crc, final_reserved = struct.unpack_from(
                        "<II", chunk_header, 40
                    )
                    if flags & FLAG_CHUNK_HEADER_CRC:
                        crc_header = bytearray(chunk_header)
                        struct.pack_into("<I", crc_header, 44, 0)
                        actual_chunk_header_crc = zlib.crc32(crc_header) & 0xFFFF_FFFF
                        if actual_chunk_header_crc != final_reserved:
                            if recovering:
                                continue
                            raise CompactTraceError(
                                f"chunk {sequence} header CRC mismatch"
                            )
                    elif final_reserved != 0:
                        crc_header = bytearray(chunk_header)
                        struct.pack_into("<I", crc_header, 44, 0)
                        actual_chunk_header_crc = zlib.crc32(crc_header) & 0xFFFF_FFFF
                        if not (
                            recovering and actual_chunk_header_crc == final_reserved
                        ):
                            if recovering:
                                continue
                            raise CompactTraceError(
                                f"chunk {sequence} reserved fields are nonzero"
                            )
                    if used > CHUNK_BYTES - CHUNK_HEADER_BYTES:
                        if recovering and version == LEGACY_FORMAT_VERSION:
                            continue
                        if not recovering:
                            raise CompactTraceError(
                                f"chunk {sequence} payload exceeds bounds"
                            )
                    if flags & FLAG_FINALIZED and used == 0:
                        raise CompactTraceError(
                            f"chunk {sequence} is finalized with an empty payload"
                        )
                    if chunk_reserved != 0:
                        if recovering:
                            continue
                        raise CompactTraceError(
                            f"chunk {sequence} reserved fields are nonzero"
                        )
                    if version == FORMAT_VERSION and base & ~mask:
                        if recovering:
                            continue
                        raise CompactTraceError(
                            f"chunk {sequence} base timestamp exceeds counter width"
                        )
                    if chunk_track not in self.schema.tracks:
                        if recovering:
                            continue
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
                if self._identity(source) != self._file_identity:
                    raise CompactTraceError(
                        "compact trace changed while chunk headers were read"
                    )
        except OSError as error:
            raise CompactTraceError(
                f"cannot read compact trace {self.path}: {error}"
            ) from error

        chunks.sort(key=lambda chunk: chunk.sequence)
        for index, (previous, current) in enumerate(zip(chunks, chunks[1:]), start=1):
            if current.sequence != previous.sequence + 1:
                if recovering:
                    chunks = chunks[:index]
                    break
                raise CompactTraceError("compact chunk sequence is not contiguous")
        if recovering and chunks and chunks[0].sequence != 0:
            flags |= FLAG_RING_WRAPPED
        total_records, overwritten_records, dropped_records = counts[:3]
        total_events, overwritten_events = counts[3:5]
        if flags & FLAG_FINALIZED and (
            overwritten_records > total_records or overwritten_events > total_events
        ):
            raise CompactTraceError("compact overwrite counts exceed total counts")
        if flags & FLAG_FINALIZED and not (
            overwritten_records <= overwritten_events <= 2 * overwritten_records
        ):
            raise CompactTraceError(
                "compact overwrite counts have inconsistent event expansion"
            )
        if flags & FLAG_FINALIZED:
            wrapped = bool(flags & FLAG_RING_WRAPPED)
            if wrapped:
                if len(chunks) != chunk_count or not chunks or chunks[0].sequence == 0:
                    raise CompactTraceError("wrapped compact ring is incomplete")
            else:
                if overwritten_records != 0 or overwritten_events != 0:
                    raise CompactTraceError(
                        "non-wrapped compact ring has overwrite counts"
                    )
                if any(
                    chunk.sequence != index or chunk.physical_index != index
                    for index, chunk in enumerate(chunks)
                ):
                    raise CompactTraceError(
                        "non-wrapped compact chunk layout is inconsistent"
                    )
        header = CompactTraceHeader(
            source_format=f"retrobus-compact-v{version}",
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
        strict = self.header.strict_clock
        recover = self.allow_unfinalized and not self.header.finalized
        try:
            with self.path.open("rb") as source:
                if self._identity(source) != self._file_identity:
                    raise CompactTraceError("compact trace changed while being read")
                for chunk in self._chunks:
                    source.seek(
                        FILE_HEADER_BYTES
                        + chunk.physical_index * CHUNK_BYTES
                        + CHUNK_HEADER_BYTES
                    )
                    payload_bytes = (
                        CHUNK_BYTES - CHUNK_HEADER_BYTES
                        if strict and recover
                        else chunk.used
                    )
                    payload = source.read(payload_bytes)
                    if len(payload) != payload_bytes:
                        raise CompactTraceError(f"chunk {chunk.sequence} is truncated")
                    if (
                        self.header.finalized
                        and (zlib.crc32(payload) & 0xFFFF_FFFF) != chunk.crc32
                    ):
                        raise CompactTraceError(f"chunk {chunk.sequence} CRC mismatch")
                    if self.header.finalized and strict:
                        slack = source.read(
                            CHUNK_BYTES - CHUNK_HEADER_BYTES - chunk.used
                        )
                        if len(slack) != CHUNK_BYTES - CHUNK_HEADER_BYTES - chunk.used:
                            raise CompactTraceError(
                                f"chunk {chunk.sequence} slack is truncated"
                            )
                        if slack != b"\0" * len(slack):
                            raise CompactTraceError(
                                f"chunk {chunk.sequence} has nonzero payload slack"
                            )
                    offset = 0
                    timestamp = chunk.base_timestamp
                    track_id = chunk.default_track
                    chunk_records = 0
                    chunk_events = 0
                    chunk_syncs = 0

                    def account(item: CompactRecord | CompactClockSync) -> None:
                        nonlocal chunk_records, chunk_events, chunk_syncs
                        if isinstance(item, CompactClockSync):
                            chunk_syncs += 1
                        else:
                            chunk_records += 1
                            chunk_events += 2 if item.event.kind == "slice" else 1

                    if strict:
                        while offset < len(payload):
                            if len(payload) - offset < RECORD_FRAME_BYTES:
                                if recover:
                                    break
                                raise CompactTraceError(
                                    f"chunk {chunk.sequence} has a truncated record frame"
                                )
                            frame_marker = payload[offset]
                            if frame_marker == 0 and recover:
                                break
                            implicit_delta: int | None = None
                            inline_event_id: int | None = None
                            if 1 <= frame_marker <= MAX_RECORD_BYTES:
                                frame_length = frame_marker
                            elif frame_marker <= FRAME_DELTA_ONE_BASE:
                                frame_length = frame_marker - FRAME_DELTA_ZERO_BASE
                                implicit_delta = 0
                            elif frame_marker <= FRAME_DELTA_ONE_LIMIT:
                                frame_length = frame_marker - FRAME_DELTA_ONE_BASE
                                implicit_delta = 1
                            elif frame_marker <= FRAME_INLINE_ONE_BASE:
                                frame_length = 0
                                implicit_delta = 0
                                inline_event_id = (
                                    frame_marker - FRAME_INLINE_ZERO_BASE - 1
                                )
                            elif frame_marker <= FRAME_INLINE_ONE_LIMIT:
                                frame_length = 0
                                implicit_delta = 1
                                inline_event_id = (
                                    frame_marker - FRAME_INLINE_ONE_BASE - 1
                                )
                            else:
                                frame_length = 0
                            if (
                                frame_length == 0 and inline_event_id is None
                            ) or frame_length > (
                                len(payload) - offset - RECORD_FRAME_BYTES
                            ):
                                if recover:
                                    break
                                raise CompactTraceError(
                                    f"chunk {chunk.sequence} has an invalid record frame"
                                )
                            frame_start = offset + RECORD_FRAME_BYTES
                            frame_end = frame_start + frame_length
                            try:
                                item, decoded, timestamp, track_id = _decode_one_record(
                                    payload,
                                    frame_start,
                                    frame_end,
                                    chunk=chunk,
                                    schema=self.schema,
                                    clock_width_bits=self.header.clock_width_bits,
                                    timestamp=timestamp,
                                    track_id=track_id,
                                    order=order,
                                    strict=True,
                                    implicit_delta=implicit_delta,
                                    inline_event_id=inline_event_id,
                                )
                                if decoded != frame_end:
                                    raise CompactTraceError(
                                        f"chunk {chunk.sequence} record frame has trailing bytes"
                                    )
                            except CompactTraceError:
                                if recover:
                                    break
                                raise
                            account(item)
                            yield item
                            order += 1
                            offset = frame_end
                    else:
                        while offset < len(payload):
                            try:
                                item, offset, timestamp, track_id = _decode_one_record(
                                    payload,
                                    offset,
                                    len(payload),
                                    chunk=chunk,
                                    schema=self.schema,
                                    clock_width_bits=self.header.clock_width_bits,
                                    timestamp=timestamp,
                                    track_id=track_id,
                                    order=order,
                                    strict=False,
                                )
                            except CompactTraceError:
                                if recover:
                                    break
                                raise
                            account(item)
                            yield item
                            order += 1
                    if self.header.finalized and (
                        chunk_records != chunk.records
                        or chunk_events != chunk.events
                        or chunk_syncs != chunk.syncs
                    ):
                        raise CompactTraceError(
                            f"chunk {chunk.sequence} record/event/sync count mismatch"
                        )
                    retained_records += chunk_records
                    retained_events += chunk_events
                if self._identity(source) != self._file_identity:
                    raise CompactTraceError("compact trace changed while being read")
        except OSError as error:
            raise CompactTraceError(
                f"cannot read compact trace {self.path}: {error}"
            ) from error
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
    correlation_id: int | None = None
    truncated: str | None = None
    suborder: int = 0


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
    elif specification.type in {"uint", "fixed64"}:
        annotation.uint_value = value
    else:
        annotation.int_value = value


def _add_arguments(wrapper: TrackEventWrapper, record: CompactRecord) -> None:
    if record.event.id_argument is not None:
        annotation = wrapper.event.debug_annotations.add()
        annotation.name = record.event.id_argument
        annotation.uint_value = record.event.id
    for constant_specification in record.event.constant_arguments:
        _add_typed_annotation(
            wrapper, constant_specification, constant_specification.value
        )
    for stored_specification, value in zip(record.event.arguments, record.arguments):
        _add_typed_annotation(wrapper, stored_specification, value)


def _correlation_value(record: CompactRecord) -> int:
    name = record.event.correlation_argument
    if name is None:
        raise CompactTraceError(f"event {record.event.id} lacks a correlation argument")
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
            assert record.event.series is not None
            async_key = (record.track_id, record.event.series, correlation)
            if async_key not in async_tracks:
                base = trace.schema.tracks[record.track_id].name
                async_tracks[async_key] = builder.add_thread(
                    f"{base}: {record.event.series} [{correlation}]"
                )

    clock_track: int | None = None
    visible_syncs = [sync for sync in trace.clock_syncs if not sync.synthetic]
    if visible_syncs:
        clock_track = builder.add_thread("Clock correlation")

    actions: list[_Action] = []
    async_open: dict[tuple[int, str, int], tuple[CompactRecord, int]] = {}
    flow_open: dict[tuple[str, int], tuple[int, int]] = {}
    used_flow_ids: set[int] = set()
    slice_intervals: dict[int, list[tuple[int, int]]] = {}
    last_timestamp: int | None = None
    zero_slice_groups: dict[tuple[int, int, int], list[CompactRecord]] = {}
    for record in trace.records:
        if record.event.kind != "slice":
            continue
        assert record.duration_ticks is not None
        end = trace.timestamp_ns(record.generation, record.extended_tick)
        start = trace.timestamp_ns(
            record.generation,
            record.extended_tick - record.duration_ticks,
        )
        if start == end:
            zero_slice_groups.setdefault(
                (record.generation, record.track_id, end), []
            ).append(record)
    zero_slice_begins: dict[int, tuple[int, int]] = {}
    for group in zero_slice_groups.values():
        zero_intervals = sorted(
            group,
            key=lambda record: (
                record.extended_tick - (record.duration_ticks or 0),
                -record.extended_tick,
                -record.order,
            ),
        )
        components: list[list[CompactRecord]] = []
        component_end: int | None = None
        component_start: int | None = None
        for record in zero_intervals:
            start_tick = record.extended_tick - (record.duration_ticks or 0)
            if component_end is None or (
                start_tick >= component_end
                and not (
                    start_tick == component_start
                    and record.extended_tick == component_end
                )
            ):
                components.append([])
                component_start = start_tick
                component_end = record.extended_tick
            else:
                component_end = max(component_end, record.extended_tick)
            components[-1].append(record)
        for component in components:
            anchor_order = min(record.order for record in component)
            for index, record in enumerate(component):
                zero_slice_begins[record.order] = (
                    anchor_order,
                    index - len(component),
                )

    def allocate_flow_id(correlation: int) -> int:
        mapped_flow_id = correlation
        while mapped_flow_id in used_flow_ids:
            mapped_flow_id = (mapped_flow_id + 1) & 0xFFFF_FFFF_FFFF_FFFF
        used_flow_ids.add(mapped_flow_id)
        return mapped_flow_id

    def truncate_flow_end(action_index: int) -> None:
        action = actions[action_index]
        truncated = "both" if action.truncated == "begin" else "end"
        actions[action_index] = replace(action, truncated=truncated)

    for record in trace.records:
        timestamp = trace.timestamp_ns(record.generation, record.extended_tick)
        last_timestamp = (
            timestamp if last_timestamp is None else max(last_timestamp, timestamp)
        )
        if record.event.kind == "slice":
            assert record.duration_ticks is not None
            start = trace.timestamp_ns(
                record.generation,
                record.extended_tick - record.duration_ticks,
            )
            duration = timestamp - start
            slice_intervals.setdefault(record.track_id, []).append((start, timestamp))
            if duration == 0:
                begin_order, begin_suborder = zero_slice_begins[record.order]
                actions.append(
                    _Action(
                        start,
                        1,
                        0,
                        begin_order,
                        "slice_begin",
                        record,
                        suborder=begin_suborder,
                    )
                )
                actions.append(
                    _Action(
                        timestamp,
                        1,
                        0,
                        record.order,
                        "slice_end",
                        record,
                        suborder=1,
                    )
                )
            else:
                actions.append(
                    _Action(
                        start,
                        2,
                        -duration,
                        -record.order,
                        "slice_begin",
                        record,
                    )
                )
                actions.append(
                    _Action(
                        timestamp,
                        1,
                        0,
                        record.order,
                        "slice_end",
                        record,
                    )
                )
        elif record.event.kind == "async_begin":
            assert record.event.series is not None
            async_key = (
                record.track_id,
                record.event.series,
                _correlation_value(record),
            )
            previous = async_open.get(async_key)
            if previous is not None:
                previous_record, _ = previous
                actions.append(
                    _Action(
                        timestamp,
                        1,
                        0,
                        record.order,
                        "async_synthetic_end",
                        previous_record,
                        truncated="end",
                        suborder=-1,
                    )
                )
            async_open[async_key] = (record, timestamp)
            actions.append(
                _Action(
                    timestamp,
                    1,
                    0,
                    record.order,
                    "async_begin",
                    record,
                )
            )
        elif record.event.kind == "async_end":
            assert record.event.series is not None
            async_key = (
                record.track_id,
                record.event.series,
                _correlation_value(record),
            )
            if async_key in async_open:
                async_open.pop(async_key)
                actions.append(
                    _Action(
                        timestamp,
                        1,
                        0,
                        record.order,
                        "async_end",
                        record,
                    )
                )
            else:
                actions.append(
                    _Action(
                        timestamp,
                        1,
                        0,
                        record.order,
                        "async_orphan_end",
                        record,
                        truncated="begin",
                    )
                )
        elif record.event.kind.startswith("flow_"):
            assert record.event.series is not None
            correlation = _correlation_value(record)
            flow_key = (record.event.series, correlation)
            if record.event.kind == "flow_start":
                previous_flow = flow_open.pop(flow_key, None)
                if previous_flow is not None:
                    previous_action, _ = previous_flow
                    truncate_flow_end(previous_action)
                mapped_flow_id = allocate_flow_id(correlation)
                actions.append(
                    _Action(
                        timestamp,
                        1,
                        0,
                        record.order,
                        "flow_start",
                        record,
                        correlation_id=mapped_flow_id,
                    )
                )
                flow_open[flow_key] = (len(actions) - 1, mapped_flow_id)
            else:
                current = flow_open.get(flow_key)
                if current is None:
                    if record.event.kind == "flow_step":
                        mapped_flow_id = allocate_flow_id(correlation)
                        actions.append(
                            _Action(
                                timestamp,
                                1,
                                0,
                                record.order,
                                "flow_step",
                                record,
                                correlation_id=mapped_flow_id,
                                truncated="begin",
                            )
                        )
                        flow_open[flow_key] = (
                            len(actions) - 1,
                            mapped_flow_id,
                        )
                    else:
                        actions.append(
                            _Action(
                                timestamp,
                                1,
                                0,
                                record.order,
                                "flow_orphan",
                                record,
                                truncated="begin",
                            )
                        )
                else:
                    _, mapped_flow_id = current
                    actions.append(
                        _Action(
                            timestamp,
                            1,
                            0,
                            record.order,
                            record.event.kind,
                            record,
                            correlation_id=mapped_flow_id,
                        )
                    )
                    if record.event.kind == "flow_end":
                        flow_open.pop(flow_key)
        else:
            actions.append(
                _Action(timestamp, 1, 0, record.order, record.event.kind, record)
            )
    for sync in visible_syncs:
        timestamp = trace.timestamp_ns(sync.generation, sync.extended_tick)
        last_timestamp = (
            timestamp if last_timestamp is None else max(last_timestamp, timestamp)
        )
        actions.append(_Action(timestamp, 1, 0, sync.order, "clock_sync", sync=sync))

    for record, begin_timestamp in async_open.values():
        closing_timestamp = (
            begin_timestamp
            if last_timestamp is None
            else max(last_timestamp, begin_timestamp)
        )
        actions.append(
            _Action(
                closing_timestamp,
                1,
                0,
                record.order,
                "async_synthetic_end",
                record,
                truncated="end",
                suborder=1,
            )
        )

    for start_action, _ in flow_open.values():
        truncate_flow_end(start_action)

    if trace.header.strict_clock:
        for track_id, intervals in slice_intervals.items():
            endings: list[int] = []
            for start, end in sorted(intervals, key=lambda item: (item[0], -item[1])):
                while endings and start >= endings[-1]:
                    endings.pop()
                if endings and end > endings[-1]:
                    raise CompactTraceError(
                        f"slice intervals cross on track {track_id}"
                    )
                endings.append(end)

    if normalize_start and actions:
        first = min(action.timestamp_ns for action in actions)
        actions = [
            replace(action, timestamp_ns=action.timestamp_ns - first)
            for action in actions
        ]
    actions.sort(
        key=lambda action: (
            action.timestamp_ns,
            action.phase,
            action.nesting,
            action.order,
            action.suborder,
        )
    )
    for action in actions:
        if not 0 <= action.timestamp_ns <= 0xFFFF_FFFF_FFFF_FFFF:
            raise CompactTraceError(
                f"mapped timestamp {action.timestamp_ns} is outside Perfetto's uint64 range"
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
            wrapper = builder.add_instant_event(
                base_track, event.name, action.timestamp_ns
            )
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
            wrapper = builder.update_counter(
                base_track, record.arguments[0], action.timestamp_ns
            )
            _add_category(wrapper, event.category)
            _add_arguments(wrapper, record)
        elif action.action in {"flow_start", "flow_step", "flow_end"}:
            assert action.correlation_id is not None
            wrapper = builder.add_flow(
                base_track,
                event.name,
                action.timestamp_ns,
                action.correlation_id,
                terminating=action.action == "flow_end",
            )
            _add_category(wrapper, event.category)
            _add_arguments(wrapper, record)
            if action.truncated in {"begin", "both"}:
                wrapper.add_annotations({"retrobus.truncated_begin": True})
            if action.truncated in {"end", "both"}:
                wrapper.add_annotations({"retrobus.truncated_end": True})
        elif action.action == "flow_orphan":
            wrapper = builder.add_instant_event(
                base_track,
                f"{event.name} (truncated begin)",
                action.timestamp_ns,
            )
            _add_category(wrapper, event.category)
            _add_arguments(wrapper, record)
            wrapper.add_annotations({"retrobus.truncated_begin": True})
        elif action.action in {
            "async_begin",
            "async_end",
            "async_synthetic_end",
            "async_orphan_end",
        }:
            assert event.series is not None
            key = (record.track_id, event.series, _correlation_value(record))
            async_track_uuid = async_tracks[key]
            if action.action == "async_begin":
                wrapper = builder.begin_slice(
                    async_track_uuid, event.name, action.timestamp_ns
                )
            elif action.action == "async_orphan_end":
                wrapper = builder.add_instant_event(
                    async_track_uuid,
                    f"{event.name} (truncated begin)",
                    action.timestamp_ns,
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
            if action.truncated is not None:
                wrapper.add_annotations(
                    {f"retrobus.truncated_{action.truncated}": True}
                )
        else:
            raise CompactTraceError(
                f"unsupported reconstructed action {action.action!r}"
            )
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
    input_source = Path(input_path)
    output = Path(output_path)
    if input_source.resolve() == output.resolve():
        raise CompactTraceError("compact conversion output must not replace its input")
    if (
        not isinstance(schema_path, CompactSchema)
        and Path(schema_path).resolve() == output.resolve()
    ):
        raise CompactTraceError("compact conversion output must not replace its schema")
    trace = read_compact_trace(
        input_path, schema_path, allow_unfinalized=allow_unfinalized
    )
    builder = compact_trace_to_builder(trace, normalize_start=normalize_start)
    serialized = builder.serialize()
    temporary: Path | None = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{output.name}.partial.",
            dir=output.parent,
            delete=False,
        ) as destination:
            temporary = Path(destination.name)
            destination.write(serialized)
            destination.flush()
            os.fsync(destination.fileno())
        assert temporary is not None
        os.replace(temporary, output)
    except OSError as error:
        raise CompactTraceError(
            f"cannot publish converted trace {output}: {error}"
        ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "format": trace.header.source_format,
        "producer": trace.schema.producer_name,
        "schema_version": trace.schema.version,
        "input_bytes": trace.header.buffer_bytes,
        "output_bytes": len(serialized),
        "records": trace.header.total_records,
        "retained_records": trace.header.retained_records,
        "events": trace.header.total_events,
        "retained_events": trace.header.retained_events,
        "overwritten_records": trace.header.overwritten_records,
        "dropped_records": trace.header.dropped_records,
        "clock_syncs": len(trace.clock_syncs),
        "uncorrelated_generations": list(trace.uncorrelated_generations),
    }
