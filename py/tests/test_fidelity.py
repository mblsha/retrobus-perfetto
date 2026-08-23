"""High-fidelity schema, builder, reader, and compatibility tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from google.protobuf.descriptor import FieldDescriptor

from retrobus_perfetto import (
    ClockReading,
    DebugAnnotationCycleError,
    DebugAnnotationDepthError,
    InlineFrame,
    LegacyEvent,
    PerfettoTraceBuilder,
    Pointer,
    SourceLocation,
    StackFrame,
    StackMapping,
    UInt,
    iter_resolved_track_events,
    resolve_interned_trace,
)
from retrobus_perfetto.proto import perfetto_pb2


def _event_packets(builder: PerfettoTraceBuilder) -> list[object]:
    return [
        packet
        for packet in builder.trace.packet
        if packet.HasField("track_event")
    ]


def test_official_field_numbers_wire_types_and_enum_values() -> None:
    """Keep the compact schema pinned to the upstream public proto contract."""
    interned = perfetto_pb2.InternedData.DESCRIPTOR.fields_by_name
    assert {
        name: (field.number, field.type)
        for name, field in interned.items()
        if name
        in {
            "event_categories",
            "event_names",
            "source_locations",
            "function_names",
            "frames",
            "callstacks",
            "build_ids",
            "mapping_paths",
            "source_paths",
            "mappings",
        }
    } == {
        "event_categories": (1, FieldDescriptor.TYPE_MESSAGE),
        "event_names": (2, FieldDescriptor.TYPE_MESSAGE),
        "source_locations": (4, FieldDescriptor.TYPE_MESSAGE),
        "function_names": (5, FieldDescriptor.TYPE_MESSAGE),
        "frames": (6, FieldDescriptor.TYPE_MESSAGE),
        "callstacks": (7, FieldDescriptor.TYPE_MESSAGE),
        "build_ids": (16, FieldDescriptor.TYPE_MESSAGE),
        "mapping_paths": (17, FieldDescriptor.TYPE_MESSAGE),
        "source_paths": (18, FieldDescriptor.TYPE_MESSAGE),
        "mappings": (19, FieldDescriptor.TYPE_MESSAGE),
    }

    track = perfetto_pb2.TrackDescriptor.DESCRIPTOR.fields_by_name
    assert track["sibling_merge_behavior"].number == 15
    assert track["sibling_merge_key"].number == 16
    assert track["sibling_merge_key_int"].number == 17
    assert (
        perfetto_pb2.TrackDescriptor.SIBLING_MERGE_BEHAVIOR_BY_SIBLING_MERGE_KEY
        == 3
    )

    event = perfetto_pb2.TrackEvent.DESCRIPTOR.fields_by_name
    assert event["legacy_event"].number == 6
    assert event["source_location"].number == 33
    assert event["source_location_iid"].number == 34
    assert event["callstack"].number == 55
    assert event["callstack_iid"].number == 56
    assert event["callstack_iid"].type == FieldDescriptor.TYPE_UINT64

    packet = perfetto_pb2.TracePacket.DESCRIPTOR.fields_by_name
    assert packet["clock_snapshot"].number == 6
    assert packet["timestamp_clock_id"].number == 58
    clock = perfetto_pb2.ClockSnapshot.Clock.DESCRIPTOR.fields_by_name
    assert clock["clock_id"].number == 1
    assert clock["timestamp"].number == 2
    assert clock["is_incremental"].number == 3
    assert clock["unit_multiplier_ns"].number == 4


def test_categories_are_interned_reused_and_resolved() -> None:
    builder = PerfettoTraceBuilder("Profiler")
    lane = builder.add_thread("GPU")
    first = builder.add_instant_event(
        lane, "launch", 10, categories=("cuda", "kernel")
    )
    first.add_category("cuda")
    builder.add_instant_event(lane, "launch", 20, categories=("cuda", "kernel"))

    packets = _event_packets(builder)
    assert list(packets[0].track_event.category_iids) == [1, 2, 1]
    assert [entry.name for entry in packets[0].interned_data.event_categories] == [
        "cuda",
        "kernel",
    ]
    assert not packets[1].HasField("interned_data")

    trace = perfetto_pb2.Trace()
    trace.ParseFromString(builder.serialize())
    resolved_events = list(iter_resolved_track_events(trace))
    assert resolved_events[0].categories == ("cuda", "kernel", "cuda")
    resolved = resolve_interned_trace(trace)
    assert list(resolved.packet[-2].track_event.categories) == [
        "cuda",
        "kernel",
        "cuda",
    ]
    assert not resolved.packet[-2].track_event.category_iids


def test_recursive_annotations_preserve_types_and_intern_strings() -> None:
    builder = PerfettoTraceBuilder("CUDA")
    lane = builder.add_thread("Kernels")
    event = builder.add_instant_event(lane, "launch", 10)
    event.add_annotations(
        {
            "launch": {
                "grid": [UInt(128), UInt(2), UInt(1)],
                "block": [UInt(32), UInt(4), UInt(1)],
                "occupancy": 0.75,
                "cooperative": True,
                "stream_ptr": Pointer(0xFEED),
                "kernel": "vector_add",
                "nested": [{"kernel": "vector_add"}, -7],
            }
        }
    )

    packet = _event_packets(builder)[0]
    strings = [
        entry.str for entry in packet.interned_data.debug_annotation_string_values
    ]
    assert strings == [b"vector_add"]
    names = {
        entry.name for entry in packet.interned_data.debug_annotation_names
    }
    assert {
        "launch",
        "grid",
        "block",
        "occupancy",
        "cooperative",
        "stream_ptr",
        "kernel",
        "nested",
    } <= names

    resolved = resolve_interned_trace(builder.trace)
    root = _event_packets_from_trace(resolved)[0].track_event.debug_annotations[0]
    values = {entry.name: entry for entry in root.dict_entries}
    assert [item.uint_value for item in values["grid"].array_values] == [128, 2, 1]
    assert values["occupancy"].double_value == 0.75
    assert values["cooperative"].bool_value is True
    assert values["stream_ptr"].pointer_value == 0xFEED
    assert values["kernel"].string_value == "vector_add"
    assert values["nested"].array_values[1].int_value == -7


def _event_packets_from_trace(trace: object) -> list[object]:
    return [
        packet
        for packet in trace.packet
        if packet.HasField("track_event")
    ]


def test_recursive_annotation_errors_are_explicit_and_atomic() -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)
    builder = PerfettoTraceBuilder("Errors", annotation_max_depth=2)
    lane = builder.add_thread("main")
    event = builder.add_instant_event(lane, "event", 1)

    with pytest.raises(DebugAnnotationCycleError):
        event.add_annotations({"cycle": cyclic})
    assert not event.event.debug_annotations

    with pytest.raises(DebugAnnotationDepthError):
        event.add_annotations({"deep": {"a": {"b": {"c": 1}}}})
    assert not event.event.debug_annotations

    with pytest.raises(TypeError, match="support"):
        event.add_annotations({"opaque": object()})
    assert not event.event.debug_annotations

    with pytest.raises(OverflowError, match="pointer"):
        event.add_annotations({"bad_address": -1})
    assert not event.event.debug_annotations


def test_sibling_merge_lanes_use_exact_official_api() -> None:
    builder = PerfettoTraceBuilder("CUDA")
    first = builder.add_merged_track_lane("Kernel lane 0", "cuda-kernels")
    second = builder.add_merged_track_lane("Kernel lane 1", "cuda-kernels")
    third = builder.add_merged_track_lane("Kernel lane 2", 42)
    descriptors = {
        packet.track_descriptor.uuid: packet.track_descriptor
        for packet in builder.trace.packet
        if packet.HasField("track_descriptor")
    }
    for lane in (first, second, third):
        assert (
            descriptors[lane].sibling_merge_behavior
            == perfetto_pb2.TrackDescriptor.SIBLING_MERGE_BEHAVIOR_BY_SIBLING_MERGE_KEY
        )
    assert descriptors[first].sibling_merge_key == "cuda-kernels"
    assert descriptors[second].sibling_merge_key == "cuda-kernels"
    assert descriptors[third].sibling_merge_key_int == 42

    with pytest.raises(ValueError, match="BY_SIBLING"):
        builder.add_track(
            "invalid",
            sibling_merge_behavior=(
                perfetto_pb2.TrackDescriptor.SIBLING_MERGE_BEHAVIOR_NONE
            ),
            sibling_merge_key="cuda-kernels",
        )


def test_source_locations_and_callstacks_are_interned_and_losslessly_read() -> None:
    builder = PerfettoTraceBuilder("Profiler")
    lane = builder.add_thread("Samples")
    mapping = StackMapping(
        path=("usr", "lib", "libcuda.so"),
        build_id=b"\x01\x02build",
        start=0x1000,
        end=0x9000,
        exact_offset=0,
    )
    frames = (
        StackFrame(
            function_name="main",
            source_path="/src/main.cc",
            line_number=7,
            kind=perfetto_pb2.Frame.KIND_NATIVE,
        ),
        StackFrame(
            function_name="launch_kernel",
            mapping=mapping,
            rel_pc=0x123,
            source_path="/src/cuda.cc",
            line_number=88,
            kind="cuda",
        ),
    )
    event = builder.add_instant_event(lane, "sample", 10)
    event.set_source_location(SourceLocation("/src/cuda.cc", "launch_kernel", 88))
    event.set_callstack(frames)
    builder.add_instant_event(lane, "sample", 20).set_callstack(frames)

    first, second = _event_packets(builder)
    assert first.track_event.HasField("source_location_iid")
    assert first.track_event.HasField("callstack_iid")
    assert len(first.interned_data.callstacks) == 1
    assert len(first.interned_data.frames) == 2
    assert len(first.interned_data.mappings) == 1
    assert {entry.str for entry in first.interned_data.function_names} == {
        b"main",
        b"launch_kernel",
    }
    assert not second.HasField("interned_data")

    resolved = list(iter_resolved_track_events(builder.trace))
    assert resolved[0].source_location == SourceLocation(
        "/src/cuda.cc", "launch_kernel", 88
    )
    callstack = resolved[0].callstack
    assert callstack is not None and callstack.complete
    assert [frame.function_name for frame in callstack.frames] == [
        "main",
        "launch_kernel",
    ]
    assert callstack.frames[1].mapping is not None
    assert callstack.frames[1].mapping.path == ("usr", "lib", "libcuda.so")
    assert callstack.frames[1].mapping.build_id == b"\x01\x02build"
    assert callstack.frames[1].rel_pc == 0x123

    inline = builder.add_instant_event(lane, "inline", 30)
    inline.set_inline_callstack(
        [InlineFrame("outer"), InlineFrame("inner", "/src/inline.cc", 5)]
    )
    inline_resolved = list(iter_resolved_track_events(builder.trace))[-1].callstack
    assert inline_resolved is not None
    assert [frame.function_name for frame in inline_resolved.frames] == [
        "outer",
        "inner",
    ]


def test_source_location_can_remain_inline() -> None:
    builder = PerfettoTraceBuilder("Inline source")
    lane = builder.add_thread("main")
    event = builder.add_instant_event(lane, "event", 1)
    event.set_source_location(
        SourceLocation("/src/main.cc", "main", 9), intern=False
    )

    assert event.event.HasField("source_location")
    assert not event.event.HasField("source_location_iid")
    assert event.event.source_location.file_name == "/src/main.cc"
    assert not event.event.source_location.HasField("iid")


def test_legacy_event_carries_all_requested_fields() -> None:
    builder = PerfettoTraceBuilder("Chrome")
    lane = builder.add_thread("Legacy")
    event = builder.add_legacy_event(
        lane,
        "async",
        100,
        LegacyEvent(
            phase="X",
            duration_us=20,
            thread_duration_us=10,
            thread_instruction_delta=7,
            id=0x123,
            id_type="global",
            id_scope="scope",
            use_async_tts=True,
            bind_id=0x456,
            bind_to_enclosing=True,
            flow_direction=perfetto_pb2.TrackEvent.LegacyEvent.FLOW_INOUT,
            instant_event_scope=perfetto_pb2.TrackEvent.LegacyEvent.SCOPE_PROCESS,
            pid_override=10,
            tid_override=11,
        ),
        categories=("legacy",),
    )
    legacy = event.event.legacy_event
    assert not event.event.HasField("type")
    assert legacy.phase == ord("X")
    assert legacy.duration_us == 20
    assert legacy.thread_duration_us == 10
    assert legacy.thread_instruction_delta == 7
    assert legacy.WhichOneof("id") == "global_id"
    assert legacy.global_id == 0x123
    assert legacy.id_scope == "scope"
    assert legacy.use_async_tts is True
    assert legacy.bind_id == 0x456
    assert legacy.bind_to_enclosing is True
    assert legacy.flow_direction == perfetto_pb2.TrackEvent.LegacyEvent.FLOW_INOUT
    assert legacy.instant_event_scope == perfetto_pb2.TrackEvent.LegacyEvent.SCOPE_PROCESS
    assert legacy.pid_override == 10
    assert legacy.tid_override == 11


def test_clock_snapshot_and_timestamp_clock_overrides() -> None:
    builder = PerfettoTraceBuilder("Clocked", timestamp_clock_id=65)
    builder.add_clock_snapshot(
        [
            ClockReading(65, 1000, is_incremental=True, unit_multiplier_ns=10),
            ClockReading(perfetto_pb2.BUILTIN_CLOCK_MONOTONIC, 20_000),
            ClockReading(perfetto_pb2.BUILTIN_CLOCK_REALTIME, 30_000),
        ],
        primary_trace_clock=perfetto_pb2.BUILTIN_CLOCK_MONOTONIC,
    )
    lane = builder.add_thread("producer")
    builder.add_instant_event(lane, "relative", 5)
    builder.add_instant_event(
        lane,
        "realtime",
        30_100,
        timestamp_clock_id=perfetto_pb2.BUILTIN_CLOCK_REALTIME,
    )

    defaults = next(
        packet.trace_packet_defaults
        for packet in builder.trace.packet
        if packet.HasField("trace_packet_defaults")
    )
    assert defaults.timestamp_clock_id == 65
    snapshot_packet = next(
        packet
        for packet in builder.trace.packet
        if packet.HasField("clock_snapshot")
    )
    assert snapshot_packet.trusted_packet_sequence_id == builder.trusted_packet_sequence_id
    assert snapshot_packet.clock_snapshot.primary_trace_clock == (
        perfetto_pb2.BUILTIN_CLOCK_MONOTONIC
    )
    clocks = {
        clock.clock_id: clock for clock in snapshot_packet.clock_snapshot.clocks
    }
    assert clocks[65].is_incremental is True
    assert clocks[65].unit_multiplier_ns == 10
    first, second = _event_packets(builder)
    assert not first.HasField("timestamp_clock_id")
    assert second.timestamp_clock_id == perfetto_pb2.BUILTIN_CLOCK_REALTIME


def test_fidelity_trace_round_trips_unknown_fields(tmp_path: Path) -> None:
    """Serialized bytes remain stable across parse/serialize round trips."""
    builder = PerfettoTraceBuilder("Round trip")
    lane = builder.add_merged_track_lane("lane", "logical")
    builder.add_instant_event(lane, "event", 1, categories=("profile",)).set_inline_callstack(
        [InlineFrame("main")]
    )
    path = tmp_path / "fidelity.perfetto-trace"
    builder.save(str(path))
    parsed = perfetto_pb2.Trace()
    parsed.ParseFromString(path.read_bytes())
    assert parsed.SerializeToString() == path.read_bytes()
