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
from .compact_codec import CompactCodecEntry, CompactCodecProfile


RBCT_MAGIC_V1 = b"RBCTRC1\0"
RBCT_MAGIC_V2 = b"RBCTRC2\0"
RBCT_MAGIC_V3 = b"RBCTRC3\0"
RBCT_MAGIC_V4 = b"RBCTRC4\0"
RBCT_MAGIC = RBCT_MAGIC_V4
RBCT_MAGICS = frozenset(
    (RBCT_MAGIC_V1, RBCT_MAGIC_V2, RBCT_MAGIC_V3, RBCT_MAGIC_V4)
)
RBCT_CHUNK_MAGIC = b"RBCK"
LEGACY_FORMAT_VERSION = 1
FRAMED_FORMAT_VERSION = 2
SEMANTIC_OPCODE_FORMAT_VERSION = 3
FORMAT_VERSION = 4
LEGACY_FILE_HEADER_BYTES = 160
FILE_HEADER_BYTES = 192
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
    codec_profile_sha256: bytes = b""

    @property
    def finalized(self) -> bool:
        return bool(self.flags & FLAG_FINALIZED)

    @property
    def ring_wrapped(self) -> bool:
        return bool(self.flags & FLAG_RING_WRAPPED)

    @property
    def format_version(self) -> int:
        return int(self.source_format.rsplit("v", 1)[1])

    @property
    def strict_clock(self) -> bool:
        return self.format_version >= FRAMED_FORMAT_VERSION

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
    committed_bits: int | None = None


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
    allow_small_explicit_delta: bool = False,
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
            if strict and delta <= 1 and not allow_small_explicit_delta:
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


def _decode_v3_record(
    data: bytes,
    offset: int,
    limit: int,
    *,
    committed_opcode: int,
    chunk: _Chunk,
    schema: CompactSchema,
    event_by_opcode: Mapping[int, int],
    inline_by_opcode: Mapping[int, tuple[int, int]],
    clock_width_bits: int,
    timestamp: int,
    track_id: int,
    order: int,
) -> tuple[CompactRecord | CompactClockSync, int, int, int]:
    """Decode one v3 opcode whose body was published before its first byte."""
    mask = (1 << clock_width_bits) - 1
    half_range = 1 << (clock_width_bits - 1)
    semantic_opcode = committed_opcode
    if committed_opcode == CONTROL_TRACK:
        selected, offset = _read_varint(data, offset, limit, canonical=True)
        if selected == track_id:
            raise CompactTraceError(
                f"chunk {chunk.sequence} has a non-canonical track wrapper"
            )
        if selected not in schema.tracks:
            raise CompactTraceError(
                f"chunk {chunk.sequence} selects unknown track {selected}"
            )
        if offset >= limit:
            raise CompactTraceError(
                f"chunk {chunk.sequence} ends inside a track wrapper"
            )
        track_id = selected
        semantic_opcode = data[offset]
        offset += 1
        if semantic_opcode == 0 or semantic_opcode in {
            CONTROL_LOSS,
            CONTROL_CLOCK_SYNC,
            CONTROL_TRACK,
        }:
            raise CompactTraceError(
                f"chunk {chunk.sequence} nests a control opcode in a track wrapper"
            )
    elif committed_opcode == CONTROL_CLOCK_SYNC:
        generation, offset = _read_varint(data, offset, limit, canonical=True)
        before, offset = _read_varint(data, offset, limit, canonical=True)
        after, offset = _read_varint(data, offset, limit, canonical=True)
        reference_ns, offset = _read_varint(data, offset, limit, canonical=True)
        uncertainty_ns, offset = _read_varint(data, offset, limit, canonical=True)
        if generation != chunk.generation:
            raise CompactTraceError(
                f"chunk {chunk.sequence} clock sync generation mismatch"
            )
        if before & ~mask or after & ~mask:
            raise CompactTraceError(
                f"chunk {chunk.sequence} clock sync exceeds counter width"
            )
        if ((after - before) & mask) >= half_range:
            raise CompactTraceError(
                f"chunk {chunk.sequence} clock sync interval is ambiguous"
            )
        midpoint = _midpoint_counter(before, after, mask)
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
            midpoint,
            track_id,
        )
    elif committed_opcode == CONTROL_LOSS:
        raise CompactTraceError("loss control is reserved")

    implicit = inline_by_opcode.get(semantic_opcode)
    if implicit is not None:
        event_id, delta = implicit
        return _decode_one_record(
            data,
            offset,
            limit,
            chunk=chunk,
            schema=schema,
            clock_width_bits=clock_width_bits,
            timestamp=timestamp,
            track_id=track_id,
            order=order,
            strict=True,
            implicit_delta=delta,
            inline_event_id=event_id,
        )

    if semantic_opcode == CONTROL_EXTENDED_EVENT:
        event_id, offset = _read_varint(data, offset, limit, canonical=True)
    else:
        event_id = event_by_opcode.get(semantic_opcode, -1)
        if event_id < 0:
            raise CompactTraceError(
                f"chunk {chunk.sequence} uses unknown schema opcode "
                f"0x{semantic_opcode:02x}"
            )
    return _decode_one_record(
        data,
        offset,
        limit,
        chunk=chunk,
        schema=schema,
        clock_width_bits=clock_width_bits,
        timestamp=timestamp,
        track_id=track_id,
        order=order,
        strict=True,
        inline_event_id=event_id,
        allow_small_explicit_delta=True,
    )


class _BitReader:
    def __init__(self, data: bytes, limit: int) -> None:
        if limit < 0 or limit > len(data) * 8:
            raise CompactTraceError("compact v4 bit cursor exceeds payload bounds")
        self.data = data
        self.limit = limit
        self.offset = 0

    def read_bits(self, width: int) -> int:
        if width < 0 or self.offset + width > self.limit:
            raise CompactTraceError("compact v4 record is truncated")
        value = 0
        for index in range(width):
            bit_offset = self.offset + index
            value |= ((self.data[bit_offset >> 3] >> (bit_offset & 7)) & 1) << index
        self.offset += width
        return value

    def read_varint(self) -> int:
        value = 0
        for index in range(10):
            byte = self.read_bits(8)
            if index == 9 and byte > 1:
                raise CompactTraceError("ULEB128 value exceeds unsigned 64-bit range")
            value |= (byte & 0x7F) << (index * 7)
            if byte & 0x80 == 0:
                if index and byte == 0:
                    raise CompactTraceError("ULEB128 value is not canonically encoded")
                return value
        raise CompactTraceError("oversized ULEB128 value")


def _v4_model_state(
    event_id: int, profile: CompactCodecProfile | None
) -> int:
    if profile is None:
        return 2
    if event_id == profile.state_events[0]:
        return 0
    if event_id == profile.state_events[1]:
        return 1
    return 2


def _decode_v4_argument(
    reader: _BitReader, specification: CompactArgumentSchema
) -> Any:
    if specification.type in {"fixed64", "float64"}:
        bits = reader.read_bits(64)
        if specification.type == "float64":
            return struct.unpack("<d", bits.to_bytes(8, "little"))[0]
        return bits
    encoded = reader.read_varint()
    if specification.type == "sint":
        return (encoded >> 1) ^ -(encoded & 1)
    if specification.type == "bool":
        if encoded not in (0, 1):
            raise CompactTraceError(
                f"boolean argument {specification.name!r} is not zero or one"
            )
        return bool(encoded)
    return encoded


def _decode_v4_item(
    reader: _BitReader,
    *,
    chunk: _Chunk,
    schema: CompactSchema,
    event_by_opcode: Mapping[int, int],
    profile: CompactCodecProfile | None,
    model_state: int,
    clock_width_bits: int,
    timestamp: int,
    track_id: int,
    order: int,
) -> tuple[CompactRecord | CompactClockSync, int, int, int]:
    code = 0
    entry: object = ...
    for width in range(1, 13):
        code |= reader.read_bits(1) << (width - 1)
        if profile is None:
            if width == 1 and code == 0:
                entry = None
                break
        else:
            entry = profile.decode_symbol(model_state, code, width)
            if entry is not ...:
                break
    if entry is ...:
        raise CompactTraceError(
            f"chunk {chunk.sequence} uses an unknown v4 prefix code"
        )
    mask = (1 << clock_width_bits) - 1
    half_range = 1 << (clock_width_bits - 1)
    if entry is None:
        literal_kind = reader.read_bits(2)
        if literal_kind == 2:
            generation = reader.read_varint()
            before = reader.read_varint()
            after = reader.read_varint()
            reference_ns = reader.read_varint()
            uncertainty_ns = reader.read_varint()
            if generation != chunk.generation:
                raise CompactTraceError(
                    f"chunk {chunk.sequence} clock sync generation mismatch"
                )
            if before & ~mask or after & ~mask:
                raise CompactTraceError(
                    f"chunk {chunk.sequence} clock sync exceeds counter width"
                )
            if ((after - before) & mask) >= half_range:
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
                _midpoint_counter(before, after, mask),
                track_id,
                model_state,
            )
        if literal_kind not in (0, 1):
            raise CompactTraceError("compact v4 literal kind is reserved")
        if literal_kind == 1:
            selected_track = reader.read_varint()
            if selected_track == track_id:
                raise CompactTraceError(
                    f"chunk {chunk.sequence} has a redundant track selection"
                )
            if selected_track not in schema.tracks:
                raise CompactTraceError(
                    f"chunk {chunk.sequence} selects unknown track {selected_track}"
                )
            track_id = selected_track
        identity = reader.read_bits(8)
        if identity == 0xFF:
            event_id = reader.read_varint()
        else:
            event_id = event_by_opcode.get(identity, -1)
            if event_id < 0:
                raise CompactTraceError(
                    f"chunk {chunk.sequence} uses unknown schema opcode "
                    f"0x{identity:02x}"
                )
        event = schema.events.get(event_id)
        if event is None:
            raise CompactTraceError(f"unknown compact event ID {event_id}")
        delta = reader.read_varint()
        if delta & ~mask or delta >= half_range:
            raise CompactTraceError(
                f"event {event.id} timestamp delta is ambiguous"
            )
        duration: int | None = None
        if event.kind == "slice":
            duration = reader.read_varint()
        arguments = tuple(
            _decode_v4_argument(reader, specification)
            for specification in event.arguments
        )
    else:
        if not isinstance(entry, CompactCodecEntry):
            raise AssertionError("unexpected compact v4 profile symbol")
        event_id = entry.event_id
        event = schema.events[event_id]
        delta = entry.delta
        duration = entry.duration
        arguments = ()
    if duration is not None and duration >= half_range:
        raise CompactTraceError(f"slice event {event.id} duration is ambiguous")
    timestamp = (timestamp + delta) & mask
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
            arguments,
            order,
        ),
        timestamp,
        track_id,
        _v4_model_state(event.id, profile),
    )


class CompactTraceReader:
    """Scan chunk headers first, then decode bounded payloads in sequence order."""

    def __init__(
        self,
        path: Path | str,
        schema: CompactSchema,
        *,
        allow_unfinalized: bool = False,
        codec_profile: CompactCodecProfile | Path | str | None = None,
    ) -> None:
        self.path = Path(path)
        self.schema = schema
        self.allow_unfinalized = allow_unfinalized
        self.codec_profile = (
            codec_profile
            if isinstance(codec_profile, CompactCodecProfile)
            else (
                CompactCodecProfile.load(codec_profile, schema)
                if codec_profile is not None
                else None
            )
        )
        if (
            self.codec_profile is not None
            and self.codec_profile.schema_sha256 != schema.sha256
        ):
            raise CompactTraceError("compact codec profile schema SHA-256 mismatch")
        if self.codec_profile is not None:
            if any(event_id not in schema.events for event_id in self.codec_profile.state_events):
                raise CompactTraceError("compact codec state event is absent from schema")
            for entry in self.codec_profile.entries:
                event = schema.events.get(entry.event_id)
                if event is None or event.kind != "slice" or event.arguments:
                    raise CompactTraceError(
                        "compact codec entry is not a zero-argument schema slice"
                    )
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
                header_prefix = source.read(16)
                if len(header_prefix) != 16:
                    raise CompactTraceError("compact file header is truncated")
                magic = header_prefix[:8]
                if magic not in RBCT_MAGICS:
                    raise CompactTraceError("not a retrobus compact trace")
                version, header_bytes, chunk_header_bytes, reserved = (
                    struct.unpack_from("<HHHH", header_prefix, 8)
                )
                if header_bytes not in (LEGACY_FILE_HEADER_BYTES, FILE_HEADER_BYTES):
                    raise CompactTraceError("unsupported compact header layout")
                raw_header = header_prefix + source.read(header_bytes - 16)
                if len(raw_header) != header_bytes:
                    raise CompactTraceError("compact file header is truncated")
                chunk_bytes = struct.unpack_from("<I", raw_header, 16)[0]
                if (
                    version
                    not in (
                        LEGACY_FORMAT_VERSION,
                        FRAMED_FORMAT_VERSION,
                        SEMANTIC_OPCODE_FORMAT_VERSION,
                        FORMAT_VERSION,
                    )
                    or magic
                    != {
                        LEGACY_FORMAT_VERSION: RBCT_MAGIC_V1,
                        FRAMED_FORMAT_VERSION: RBCT_MAGIC_V2,
                        SEMANTIC_OPCODE_FORMAT_VERSION: RBCT_MAGIC_V3,
                        FORMAT_VERSION: RBCT_MAGIC_V4,
                    }[version]
                    or header_bytes
                    != (
                        FILE_HEADER_BYTES
                        if version == FORMAT_VERSION
                        else LEGACY_FILE_HEADER_BYTES
                    )
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
                    version >= FRAMED_FORMAT_VERSION
                    and flags & FLAG_FINALIZED
                    and not flags & FLAG_CHUNK_HEADER_CRC
                ):
                    raise CompactTraceError(
                        "finalized compact trace lacks chunk-header CRCs"
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
                profile_hash = raw_header[160:192] if version == FORMAT_VERSION else b""
                if version == FORMAT_VERSION:
                    if profile_hash == b"\0" * 32:
                        if self.codec_profile is not None:
                            raise CompactTraceError(
                                "literal-only compact v4 trace does not use a codec profile"
                            )
                    elif self.codec_profile is None:
                        raise CompactTraceError(
                            "compact v4 trace requires its external codec profile"
                        )
                    elif profile_hash != self.codec_profile.sha256:
                        raise CompactTraceError("compact codec profile SHA-256 mismatch")
                buffer_bytes = counts[5]
                if (
                    buffer_bytes != file_size
                    or (file_size - header_bytes) % CHUNK_BYTES
                    or file_size < header_bytes + CHUNK_BYTES
                ):
                    raise CompactTraceError(
                        "compact buffer size does not match file size"
                    )
                if default_track not in self.schema.tracks:
                    raise CompactTraceError(f"unknown default track {default_track}")

                chunks: list[_Chunk] = []
                chunk_count = (file_size - header_bytes) // CHUNK_BYTES
                mask = (1 << width) - 1
                for physical_index in range(chunk_count):
                    source.seek(header_bytes + physical_index * CHUNK_BYTES)
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
                    used_field, records = struct.unpack_from("<HH", chunk_header, 28)
                    committed_bits = used_field if version == FORMAT_VERSION else None
                    used = (
                        (used_field + 7) // 8
                        if committed_bits is not None
                        else used_field
                    )
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
                    elif final_reserved != 0 and not (
                        recovering and version >= SEMANTIC_OPCODE_FORMAT_VERSION
                    ):
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
                    if (
                        committed_bits is not None
                        and committed_bits > (CHUNK_BYTES - CHUNK_HEADER_BYTES) * 8
                    ) or used > CHUNK_BYTES - CHUNK_HEADER_BYTES:
                        if recovering:
                            # V2/v3 treat the byte cursor as lagging metadata and
                            # scan exactly one physical payload. V1 uses it as a
                            # read bound, and v4 uses committed_bits as its
                            # publication bound, so malformed values in those
                            # formats make the chunk unrecoverable.
                            if version in (LEGACY_FORMAT_VERSION, FORMAT_VERSION):
                                continue
                        else:
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
                    if version >= FRAMED_FORMAT_VERSION and base & ~mask:
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
                            committed_bits,
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
            codec_profile_sha256=profile_hash,
        )
        return header, tuple(chunks)

    def iter_items(self) -> Iterator[CompactRecord | CompactClockSync]:
        order = 0
        retained_records = 0
        retained_events = 0
        strict = self.header.strict_clock
        format_version = self.header.format_version
        recover = self.allow_unfinalized and not self.header.finalized
        event_by_opcode = {
            opcode: event_id
            for event_id, opcode in self.schema.v3_event_opcodes.items()
        }
        inline_by_opcode = {
            opcode: (event_id, delta)
            for event_id, opcodes in self.schema.v3_inline_opcodes.items()
            for delta, opcode in enumerate(opcodes)
        }
        stop_recovery = False
        try:
            with self.path.open("rb") as source:
                if self._identity(source) != self._file_identity:
                    raise CompactTraceError("compact trace changed while being read")
                for chunk_index, chunk in enumerate(self._chunks):
                    file_header_bytes = (
                        FILE_HEADER_BYTES
                        if format_version == FORMAT_VERSION
                        else LEGACY_FILE_HEADER_BYTES
                    )
                    source.seek(
                        file_header_bytes
                        + chunk.physical_index * CHUNK_BYTES
                        + CHUNK_HEADER_BYTES
                    )
                    payload_bytes = (
                        CHUNK_BYTES - CHUNK_HEADER_BYTES
                        if strict and recover and format_version != FORMAT_VERSION
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
                        if (
                            format_version == FORMAT_VERSION
                            and chunk.committed_bits is not None
                            and chunk.committed_bits & 7
                            and payload
                            and payload[-1] & ~((1 << (chunk.committed_bits & 7)) - 1)
                        ):
                            raise CompactTraceError(
                                f"chunk {chunk.sequence} has nonzero unused payload bits"
                            )
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
                    model_state = 2

                    def account(item: CompactRecord | CompactClockSync) -> None:
                        nonlocal chunk_records, chunk_events, chunk_syncs
                        if isinstance(item, CompactClockSync):
                            chunk_syncs += 1
                        else:
                            chunk_records += 1
                            chunk_events += 2 if item.event.kind == "slice" else 1

                    if format_version == FORMAT_VERSION:
                        assert chunk.committed_bits is not None
                        bit_reader = _BitReader(payload, chunk.committed_bits)
                        while bit_reader.offset < bit_reader.limit:
                            try:
                                item, timestamp, track_id, model_state = _decode_v4_item(
                                    bit_reader,
                                    chunk=chunk,
                                    schema=self.schema,
                                    event_by_opcode=event_by_opcode,
                                    profile=self.codec_profile,
                                    model_state=model_state,
                                    clock_width_bits=self.header.clock_width_bits,
                                    timestamp=timestamp,
                                    track_id=track_id,
                                    order=order,
                                )
                            except CompactTraceError:
                                if recover:
                                    stop_recovery = True
                                    break
                                raise
                            account(item)
                            yield item
                            order += 1
                    elif format_version == FRAMED_FORMAT_VERSION:
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
                    elif format_version == SEMANTIC_OPCODE_FORMAT_VERSION:
                        while offset < len(payload):
                            committed_opcode = payload[offset]
                            if committed_opcode == 0 and recover:
                                stop_recovery = chunk_index == len(self._chunks) - 1
                                break
                            offset += RECORD_FRAME_BYTES
                            try:
                                item, offset, timestamp, track_id = _decode_v3_record(
                                    payload,
                                    offset,
                                    len(payload),
                                    committed_opcode=committed_opcode,
                                    chunk=chunk,
                                    schema=self.schema,
                                    event_by_opcode=event_by_opcode,
                                    inline_by_opcode=inline_by_opcode,
                                    clock_width_bits=self.header.clock_width_bits,
                                    timestamp=timestamp,
                                    track_id=track_id,
                                    order=order,
                                )
                            except CompactTraceError:
                                if recover:
                                    stop_recovery = True
                                    break
                                raise
                            account(item)
                            yield item
                            order += 1
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
                    if stop_recovery:
                        break
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
    codec_profile: CompactCodecProfile | Path | str | None = None,
) -> CompactTrace:
    """Read and validate a producer-neutral `.rbct` image."""
    producer_schema = (
        schema if isinstance(schema, CompactSchema) else CompactSchema.load(schema)
    )
    source = Path(path)
    return CompactTraceReader(
        source,
        producer_schema,
        allow_unfinalized=allow_unfinalized,
        codec_profile=codec_profile,
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
    codec_profile: CompactCodecProfile | Path | str | None = None,
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
        input_path,
        schema_path,
        allow_unfinalized=allow_unfinalized,
        codec_profile=codec_profile,
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
