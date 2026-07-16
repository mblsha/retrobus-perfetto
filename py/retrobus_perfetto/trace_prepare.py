"""Helpers for preparing Perfetto traces for compact timeline renders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


SYNTHETIC_SPAN_TRACK_NAME = "Synthetic full trace span"
SYNTHETIC_SPAN_EVENT_NAME = "full_trace"


@dataclass(frozen=True)
class PreparedTraceBounds:
    """Timestamp bounds used while preparing a trace."""

    source_start_ns: int
    duration_ns: int


def _track_name(descriptor: Any) -> str:
    return (
        descriptor.thread.thread_name
        or descriptor.name
        or descriptor.process.process_name
        or f"track_{descriptor.uuid}"
    )


def _synthetic_track_uuids(trace: Any) -> set[int]:
    return {
        packet.track_descriptor.uuid
        for packet in trace.packet
        if packet.HasField("track_descriptor")
        and _track_name(packet.track_descriptor) == SYNTHETIC_SPAN_TRACK_NAME
    }


def _remove_tracks(trace: Any, track_uuids: set[int]) -> None:
    if not track_uuids:
        return
    kept_packets = []
    for packet in trace.packet:
        if packet.HasField("track_descriptor") and packet.track_descriptor.uuid in track_uuids:
            continue
        if packet.HasField("track_event") and packet.track_event.track_uuid in track_uuids:
            continue
        kept_packets.append(packet)
    del trace.packet[:]
    trace.packet.extend(kept_packets)


def trace_time_bounds(
    trace: Any,
    *,
    exclude_tracks: Iterable[int] = (),
) -> tuple[int, int]:
    """Return the first and last timestamped track-event timestamps."""

    excluded = set(exclude_tracks)
    timestamps = [
        packet.timestamp
        for packet in trace.packet
        if packet.HasField("timestamp")
        and packet.HasField("track_event")
        and packet.track_event.track_uuid not in excluded
    ]
    if not timestamps:
        raise ValueError("trace has no timestamped track events")
    return min(timestamps), max(timestamps)


def normalize_timestamps(trace: Any, base_timestamp: int) -> None:
    """Shift timestamped packets so ``base_timestamp`` becomes zero."""

    for packet in trace.packet:
        if packet.HasField("timestamp"):
            packet.timestamp = max(0, packet.timestamp - base_timestamp)


def _next_descriptor_ids(trace: Any) -> tuple[int, int, int]:
    max_uuid = 0
    max_tid = 1000
    max_sequence_id = 0
    for packet in trace.packet:
        if packet.HasField("trusted_packet_sequence_id"):
            max_sequence_id = max(max_sequence_id, packet.trusted_packet_sequence_id)
        if not packet.HasField("track_descriptor"):
            continue
        descriptor = packet.track_descriptor
        max_uuid = max(max_uuid, descriptor.uuid)
        if descriptor.HasField("thread"):
            max_tid = max(max_tid, descriptor.thread.tid)
    return max_uuid + 1, max(max_tid + 1, 9001), max_sequence_id + 1


def _process_track_uuid(trace: Any) -> int:
    for packet in trace.packet:
        if packet.HasField("track_descriptor") and packet.track_descriptor.HasField("process"):
            return packet.track_descriptor.uuid
    return 0


def add_synthetic_full_trace_span(
    trace: Any,
    perfetto_pb2: Any,
    *,
    end_timestamp: int,
) -> None:
    """Add one slice covering the complete normalized trace duration."""

    track_uuid, tid, sequence_id = _next_descriptor_ids(trace)
    parent_uuid = _process_track_uuid(trace)

    descriptor = perfetto_pb2.TracePacket()
    descriptor.trusted_packet_sequence_id = sequence_id
    descriptor.track_descriptor.uuid = track_uuid
    if parent_uuid:
        descriptor.track_descriptor.parent_uuid = parent_uuid
    descriptor.track_descriptor.name = SYNTHETIC_SPAN_TRACK_NAME
    descriptor.track_descriptor.thread.pid = 1234
    descriptor.track_descriptor.thread.tid = tid
    descriptor.track_descriptor.thread.thread_name = SYNTHETIC_SPAN_TRACK_NAME

    begin = perfetto_pb2.TracePacket()
    begin.timestamp = 0
    begin.trusted_packet_sequence_id = sequence_id
    begin.track_event.type = perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN
    begin.track_event.track_uuid = track_uuid
    begin.track_event.name = SYNTHETIC_SPAN_EVENT_NAME

    end = perfetto_pb2.TracePacket()
    end.timestamp = end_timestamp
    end.trusted_packet_sequence_id = sequence_id
    end.track_event.type = perfetto_pb2.TrackEvent.TYPE_SLICE_END
    end.track_event.track_uuid = track_uuid

    trace.packet.insert(0, begin)
    trace.packet.insert(0, descriptor)
    trace.packet.append(end)


def prepare_trace_for_render(
    trace: Any,
    perfetto_pb2: Any,
    *,
    normalize_start: bool = True,
    synthetic_span: bool = True,
) -> PreparedTraceBounds:
    """Normalize a trace and optionally add an idempotent full-duration slice."""

    existing_synthetic_tracks = _synthetic_track_uuids(trace)
    min_timestamp, max_timestamp = trace_time_bounds(
        trace,
        exclude_tracks=existing_synthetic_tracks,
    )
    _remove_tracks(trace, existing_synthetic_tracks)

    if normalize_start:
        normalize_timestamps(trace, min_timestamp)
        max_timestamp -= min_timestamp

    if synthetic_span:
        add_synthetic_full_trace_span(
            trace,
            perfetto_pb2,
            end_timestamp=max_timestamp,
        )

    return PreparedTraceBounds(
        source_start_ns=min_timestamp,
        duration_ns=max_timestamp,
    )
