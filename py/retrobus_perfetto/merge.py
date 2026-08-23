"""Merge independently produced Perfetto traces without identifier collisions."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Sequence

from .oracle_index import iter_trace_packets


def _protobuf_varint(value: int) -> bytes:
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        encoded.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(encoded)


def merge_perfetto_traces(
    trace_paths: Sequence[Path | str], output_path: Path | str
) -> dict[str, Any]:
    """Stream packets into one trace while remapping sequence, track, and flow IDs."""
    if not trace_paths:
        raise ValueError("at least one input trace is required")
    inputs = [Path(path).resolve() for path in trace_paths]
    output = Path(output_path).resolve()
    if output in inputs:
        raise ValueError("the merge output must not replace an input trace")

    track_ids: dict[tuple[int, int], int] = {}
    sequence_ids: dict[tuple[int, int], int] = {}
    flow_ids: dict[tuple[int, int], int] = {}
    legacy_ids: dict[tuple[int, str, str, int | None, int], int] = {}
    track_scopes: dict[tuple[int, int], tuple[int, int | None, int | None]] = {}
    default_tracks: dict[tuple[int, int], int] = {}
    next_track = 1
    next_sequence = 1
    next_flow = 1
    next_legacy = 1

    def map_track(source: int, value: int) -> int:
        nonlocal next_track
        if value == 0:
            return 0
        key = (source, value)
        if key not in track_ids:
            track_ids[key] = next_track
            next_track += 1
        return track_ids[key]

    def map_sequence(source: int, value: int) -> int:
        nonlocal next_sequence
        key = (source, value)
        if key not in sequence_ids:
            sequence_ids[key] = next_sequence
            next_sequence += 1
        return sequence_ids[key]

    def map_flow(source: int, value: int) -> int:
        nonlocal next_flow
        key = (source, value)
        if key not in flow_ids:
            flow_ids[key] = next_flow
            next_flow += 1
        return flow_ids[key]

    def map_legacy_id(
        source: int,
        kind: str,
        scope: str,
        pid: int | None,
        value: int,
    ) -> int:
        nonlocal next_legacy
        key = (source, kind, scope, pid, value)
        if key not in legacy_ids:
            legacy_ids[key] = next_legacy
            next_legacy += 1
        return legacy_ids[key]

    def effective_pid(source: int, track_uuid: int | None) -> int | None:
        seen: set[int] = set()
        while track_uuid is not None and track_uuid not in seen:
            seen.add(track_uuid)
            scope = track_scopes.get((source, track_uuid))
            if scope is None:
                return None
            parent_uuid, pid, _ = scope
            if pid is not None:
                return pid
            track_uuid = parent_uuid or None
        return None

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.name}.partial.{os.getpid()}")
    packet_count = 0
    output_bytes = 0
    try:
        with temporary.open("wb") as destination:
            for record in iter_trace_packets(inputs):
                packet = record.packet
                source = record.source_id
                original_sequence_id = (
                    packet.trusted_packet_sequence_id
                    if packet.HasField("trusted_packet_sequence_id")
                    else 0
                )
                if packet.HasField("trusted_packet_sequence_id"):
                    packet.trusted_packet_sequence_id = map_sequence(
                        source, packet.trusted_packet_sequence_id
                    )
                if packet.HasField("track_descriptor"):
                    descriptor = packet.track_descriptor
                    original_uuid = descriptor.uuid if descriptor.HasField("uuid") else 0
                    original_parent = (
                        descriptor.parent_uuid
                        if descriptor.HasField("parent_uuid")
                        else 0
                    )
                    pid = None
                    tid = None
                    if descriptor.HasField("process") and descriptor.process.HasField(
                        "pid"
                    ):
                        pid = descriptor.process.pid
                    elif descriptor.HasField("thread"):
                        if descriptor.thread.HasField("pid"):
                            pid = descriptor.thread.pid
                        if descriptor.thread.HasField("tid"):
                            tid = descriptor.thread.tid
                    if original_uuid:
                        track_scopes[(source, original_uuid)] = (
                            original_parent,
                            pid,
                            tid,
                        )
                    if descriptor.HasField("uuid"):
                        descriptor.uuid = map_track(source, descriptor.uuid)
                    if descriptor.HasField("parent_uuid"):
                        descriptor.parent_uuid = map_track(source, descriptor.parent_uuid)
                if packet.HasField("trace_packet_defaults"):
                    packet_defaults = packet.trace_packet_defaults
                    if packet_defaults.HasField("track_event_defaults"):
                        event_defaults = packet_defaults.track_event_defaults
                        if event_defaults.HasField("track_uuid"):
                            default_tracks[(source, original_sequence_id)] = (
                                event_defaults.track_uuid
                            )
                            event_defaults.track_uuid = map_track(
                                source, event_defaults.track_uuid
                            )
                        for index, value in enumerate(
                            event_defaults.extra_counter_track_uuids
                        ):
                            event_defaults.extra_counter_track_uuids[index] = map_track(
                                source, value
                            )
                        for index, value in enumerate(
                            event_defaults.extra_double_counter_track_uuids
                        ):
                            event_defaults.extra_double_counter_track_uuids[index] = (
                                map_track(source, value)
                            )
                if packet.HasField("track_event"):
                    event = packet.track_event
                    original_track_uuid = (
                        event.track_uuid
                        if event.HasField("track_uuid")
                        else default_tracks.get((source, original_sequence_id))
                    )
                    if event.HasField("track_uuid"):
                        event.track_uuid = map_track(source, event.track_uuid)
                    for index, value in enumerate(event.extra_counter_track_uuids):
                        event.extra_counter_track_uuids[index] = map_track(source, value)
                    for index, value in enumerate(event.extra_double_counter_track_uuids):
                        event.extra_double_counter_track_uuids[index] = map_track(
                            source, value
                        )
                    for index, value in enumerate(event.flow_ids):
                        event.flow_ids[index] = map_flow(source, value)
                    for index, value in enumerate(event.terminating_flow_ids):
                        event.terminating_flow_ids[index] = map_flow(source, value)
                    for index, value in enumerate(event.flow_ids_old):
                        event.flow_ids_old[index] = map_flow(source, value)
                    for index, value in enumerate(event.terminating_flow_ids_old):
                        event.terminating_flow_ids_old[index] = map_flow(source, value)
                    if event.HasField("legacy_event"):
                        legacy = event.legacy_event
                        if legacy.HasField("bind_id"):
                            legacy.bind_id = map_flow(source, legacy.bind_id)
                        id_kind = legacy.WhichOneof("id")
                        if id_kind is not None:
                            value = getattr(legacy, id_kind)
                            scope = legacy.id_scope if legacy.HasField("id_scope") else ""
                            pid = None
                            if id_kind != "global_id":
                                pid = (
                                    legacy.pid_override
                                    if legacy.HasField("pid_override")
                                    else effective_pid(source, original_track_uuid)
                                )
                            setattr(
                                legacy,
                                id_kind,
                                map_legacy_id(
                                    source, id_kind, scope, pid, value
                                ),
                            )
                payload = packet.SerializeToString()
                wrapper = b"\x0a" + _protobuf_varint(len(payload)) + payload
                destination.write(wrapper)
                output_bytes += len(wrapper)
                packet_count += 1
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "sources": len(inputs),
        "packets": packet_count,
        "tracks": len(track_ids),
        "sequences": len(sequence_ids),
        "flows": len(flow_ids),
        "legacy_ids": len(legacy_ids),
        "output_bytes": output_bytes,
    }
