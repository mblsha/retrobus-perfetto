"""Collision-safe trace merge tests."""

from pathlib import Path

from retrobus_perfetto import (
    LegacyEvent,
    PerfettoTraceBuilder,
    SourceLocation,
    StackFrame,
    iter_resolved_track_events,
    merge_perfetto_traces,
)
from retrobus_perfetto.proto import perfetto_pb2


def _source(path: Path, name: str) -> int:
    builder = PerfettoTraceBuilder(name, encoding="inline")
    track = builder.add_thread("main")
    integer_counter = track + 1000
    double_counter = track + 2000
    for uuid, descriptor_name in (
        (integer_counter, "integer counter"),
        (double_counter, "double counter"),
    ):
        descriptor = builder.trace.packet.add().track_descriptor
        descriptor.uuid = uuid
        descriptor.name = descriptor_name
    defaults_packet = builder.trace.packet.add()
    defaults_packet.trusted_packet_sequence_id = builder.trusted_packet_sequence_id
    defaults = defaults_packet.trace_packet_defaults.track_event_defaults
    defaults.track_uuid = track
    defaults.extra_counter_track_uuids.append(integer_counter)
    defaults.extra_double_counter_track_uuids.append(double_counter)
    event_packet = builder.trace.packet.add()
    event_packet.trusted_packet_sequence_id = builder.trusted_packet_sequence_id
    event_packet.track_event.type = perfetto_pb2.TrackEvent.TYPE_INSTANT
    event_packet.track_event.name = "defaulted event"
    event_packet.track_event.extra_counter_values.append(1)
    event_packet.track_event.extra_double_counter_values.append(2.0)
    builder.add_flow(track, "begin", 1000, 77)
    builder.add_flow(track, "end", 2000, 77, terminating=True)
    builder.save(str(path))
    return len(builder.trace.packet)


def test_merge_remaps_colliding_identifiers(tmp_path: Path) -> None:
    first = tmp_path / "first.perfetto-trace"
    second = tmp_path / "second.perfetto-trace"
    output = tmp_path / "merged.perfetto-trace"
    expected_packets = _source(first, "first") + _source(second, "second")

    summary = merge_perfetto_traces([first, second], output)
    assert summary["packets"] == expected_packets
    assert summary["sources"] == 2

    trace = perfetto_pb2.Trace()
    trace.ParseFromString(output.read_bytes())
    assert len(trace.packet) == expected_packets
    descriptor_ids = [
        packet.track_descriptor.uuid
        for packet in trace.packet
        if packet.HasField("track_descriptor")
    ]
    assert len(descriptor_ids) == len(set(descriptor_ids))
    default_tracks = [
        packet.trace_packet_defaults.track_event_defaults
        for packet in trace.packet
        if packet.HasField("trace_packet_defaults")
    ]
    assert len(default_tracks) == 2
    default_uuids = {
        defaults.track_uuid
        for defaults in default_tracks
    } | {
        uuid
        for defaults in default_tracks
        for uuid in (
            *defaults.extra_counter_track_uuids,
            *defaults.extra_double_counter_track_uuids,
        )
    }
    assert len(default_uuids) == 6
    assert default_uuids <= set(descriptor_ids)
    sequence_ids = {
        packet.trusted_packet_sequence_id
        for packet in trace.packet
        if packet.HasField("trusted_packet_sequence_id")
    }
    assert len(sequence_ids) == 2
    starting_flows = [
        event.flow_ids[0]
        for packet in trace.packet
        if packet.HasField("track_event")
        for event in (packet.track_event,)
        if event.flow_ids
    ]
    assert len(starting_flows) == 2
    assert starting_flows[0] != starting_flows[1]


def _fidelity_source(path: Path, name: str) -> None:
    builder = PerfettoTraceBuilder(name)
    lane = builder.add_merged_track_lane("lane", "logical-kernels")
    builder.add_instant_event(
        lane, "sample", 10, categories=("profile", name)
    ).set_source_location(
        SourceLocation(f"/{name}.cc", f"{name}_kernel", 7)
    ).set_callstack(
        [StackFrame(function_name=f"{name}_kernel")]
    )
    builder.add_legacy_event(
        lane,
        "legacy",
        20,
        LegacyEvent(
            phase="b",
            id=77,
            id_type="local",
            id_scope="scope",
            bind_id=88,
        ),
    )
    builder.save(str(path))


def test_merge_keeps_interning_scoped_and_remaps_legacy_identifiers(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first-fidelity.perfetto-trace"
    second = tmp_path / "second-fidelity.perfetto-trace"
    output = tmp_path / "merged-fidelity.perfetto-trace"
    _fidelity_source(first, "first")
    _fidelity_source(second, "second")

    summary = merge_perfetto_traces([first, second], output)
    assert summary["legacy_ids"] == 2
    trace = perfetto_pb2.Trace.FromString(output.read_bytes())
    sequence_ids = {
        packet.trusted_packet_sequence_id
        for packet in trace.packet
        if packet.HasField("trusted_packet_sequence_id")
    }
    assert len(sequence_ids) == 2

    samples = [
        event
        for event in iter_resolved_track_events(trace)
        if event.name == "sample"
    ]
    assert [event.categories for event in samples] == [
        ("profile", "first"),
        ("profile", "second"),
    ]
    assert [event.source_location.file_name for event in samples] == [
        "/first.cc",
        "/second.cc",
    ]
    assert [event.callstack.frames[0].function_name for event in samples] == [
        "first_kernel",
        "second_kernel",
    ]

    legacy = [
        packet.track_event.legacy_event
        for packet in trace.packet
        if packet.HasField("track_event")
        and packet.track_event.HasField("legacy_event")
    ]
    assert len({event.local_id for event in legacy}) == 2
    assert len({event.bind_id for event in legacy}) == 2
    descriptors = [
        packet.track_descriptor
        for packet in trace.packet
        if packet.HasField("track_descriptor")
        and packet.track_descriptor.HasField("sibling_merge_key")
    ]
    assert [descriptor.sibling_merge_key for descriptor in descriptors] == [
        "logical-kernels",
        "logical-kernels",
    ]


def test_merge_keeps_process_scoped_legacy_ids_distinct(tmp_path: Path) -> None:
    source = tmp_path / "multi-process.perfetto-trace"
    output = tmp_path / "multi-process-merged.perfetto-trace"
    builder = PerfettoTraceBuilder("root", encoding="inline")
    for track_uuid, pid in ((100, 10), (200, 20)):
        descriptor = builder.trace.packet.add().track_descriptor
        descriptor.uuid = track_uuid
        descriptor.thread.pid = pid
        descriptor.thread.tid = 1
        builder.add_legacy_event(
            track_uuid,
            "async",
            pid,
            LegacyEvent(phase="b", id=77, id_type="local", id_scope="scope"),
        )
    builder.save(str(source))

    summary = merge_perfetto_traces([source], output)
    assert summary["legacy_ids"] == 2
    trace = perfetto_pb2.Trace.FromString(output.read_bytes())
    local_ids = [
        packet.track_event.legacy_event.local_id
        for packet in trace.packet
        if packet.HasField("track_event")
    ]
    assert len(local_ids) == len(set(local_ids)) == 2
