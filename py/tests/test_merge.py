"""Collision-safe trace merge tests."""

from pathlib import Path

from retrobus_perfetto import PerfettoTraceBuilder, merge_perfetto_traces
from retrobus_perfetto.proto import perfetto_pb2


def _source(path: Path, name: str) -> int:
    builder = PerfettoTraceBuilder(name, encoding="inline")
    track = builder.add_thread("main")
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
