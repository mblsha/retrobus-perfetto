"""Compatibility checks against a pinned full official Perfetto descriptor."""

import hashlib
from pathlib import Path

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

from retrobus_perfetto import (
    ClockReading,
    InlineFrame,
    LegacyEvent,
    PerfettoTraceBuilder,
    Pointer,
    SourceLocation,
    StackFrame,
    StackMapping,
    UInt,
)
from retrobus_perfetto.proto import perfetto_pb2


def _official_pool() -> descriptor_pool.DescriptorPool:
    descriptor_path = (
        Path(__file__).parent
        / "fixtures"
        / "perfetto-official-ec5d16b1.desc"
    )
    descriptor_bytes = descriptor_path.read_bytes()
    assert hashlib.sha256(descriptor_bytes).hexdigest() == (
        "fb1715edc048d2ae2ed4b764b649234c25c7ad464f7ae3103c0fda4607e9d71a"
    )
    descriptor_set = descriptor_pb2.FileDescriptorSet.FromString(descriptor_bytes)
    pool = descriptor_pool.DescriptorPool()
    for file_descriptor in descriptor_set.file:
        pool.Add(file_descriptor)
    return pool


def _official_trace_type() -> type:
    return message_factory.GetMessageClass(
        _official_pool().FindMessageTypeByName("perfetto.protos.Trace")
    )


def test_compact_schema_fields_match_the_full_official_descriptor() -> None:
    official = _official_pool()
    local = perfetto_pb2.DESCRIPTOR.pool
    selected_fields = {
        "InternedData": {
            "event_categories",
            "event_names",
            "debug_annotation_names",
            "source_locations",
            "function_names",
            "frames",
            "callstacks",
            "build_ids",
            "mapping_paths",
            "source_paths",
            "mappings",
            "debug_annotation_value_type_names",
            "debug_annotation_string_values",
        },
        "TrackDescriptor": {
            "sibling_merge_behavior",
            "sibling_merge_key",
            "sibling_merge_key_int",
        },
        "TrackEvent": {
            "legacy_event",
            "source_location",
            "source_location_iid",
            "callstack",
            "callstack_iid",
        },
        "TrackEvent.InlineCallstack": {"frames"},
        "TrackEvent.InlineCallstack.Frame": {
            "function_name",
            "source_file",
            "line_number",
        },
        "TrackEvent.LegacyEvent": {
            "phase",
            "duration_us",
            "thread_duration_us",
            "unscoped_id",
            "local_id",
            "global_id",
            "id_scope",
            "use_async_tts",
            "bind_id",
            "bind_to_enclosing",
            "flow_direction",
            "instant_event_scope",
            "thread_instruction_delta",
            "pid_override",
            "tid_override",
        },
        "DebugAnnotation": {
            "dict_entries",
            "array_values",
            "bool_value",
            "uint_value",
            "int_value",
            "double_value",
            "string_value",
            "string_value_iid",
            "pointer_value",
        },
        "SourceLocation": {"iid", "file_name", "function_name", "line_number"},
        "Mapping": {
            "iid",
            "build_id",
            "path_string_ids",
            "exact_offset",
            "start_offset",
            "start",
            "end",
            "load_bias",
        },
        "Frame": {
            "iid",
            "function_name_id",
            "mapping_id",
            "rel_pc",
            "source_path_iid",
            "line_number",
            "kind",
            "kind_str",
        },
        "Callstack": {"iid", "frame_ids"},
        "ClockSnapshot": {"clocks", "primary_trace_clock"},
        "ClockSnapshot.Clock": {
            "clock_id",
            "timestamp",
            "is_incremental",
            "unit_multiplier_ns",
        },
        "TracePacket": {"clock_snapshot", "timestamp_clock_id"},
    }
    for short_name, field_names in selected_fields.items():
        full_name = f"perfetto.protos.{short_name}"
        official_message = official.FindMessageTypeByName(full_name)
        local_message = local.FindMessageTypeByName(full_name)
        for field_name in field_names:
            official_field = official_message.fields_by_name[field_name]
            local_field = local_message.fields_by_name[field_name]
            assert (
                local_field.number,
                local_field.type,
                local_field.is_repeated,
                local_field.is_required,
                local_field.containing_oneof.name
                if local_field.containing_oneof is not None
                else None,
            ) == (
                official_field.number,
                official_field.type,
                official_field.is_repeated,
                official_field.is_required,
                official_field.containing_oneof.name
                if official_field.containing_oneof is not None
                else None,
            ), f"{full_name}.{field_name} differs from official Perfetto"

    for enum_name in (
        "TrackDescriptor.SiblingMergeBehavior",
        "Frame.Kind",
        "TrackEvent.LegacyEvent.FlowDirection",
        "TrackEvent.LegacyEvent.InstantEventScope",
        "ClockSnapshot.Clock.BuiltinClocks",
        "BuiltinClock",
    ):
        full_name = f"perfetto.protos.{enum_name}"
        official_values = official.FindEnumTypeByName(full_name).values_by_name
        local_values = local.FindEnumTypeByName(full_name).values_by_name
        assert {name: value.number for name, value in local_values.items()} == {
            name: value.number for name, value in official_values.items()
        }


def test_full_official_perfetto_schema_parses_every_fidelity_capability() -> None:
    builder = PerfettoTraceBuilder("Profiler", timestamp_clock_id=65)
    builder.add_clock_snapshot(
        [
            ClockReading(65, 1_000, is_incremental=True, unit_multiplier_ns=10),
            ClockReading(perfetto_pb2.BUILTIN_CLOCK_MONOTONIC, 20_000),
            ClockReading(perfetto_pb2.BUILTIN_CLOCK_REALTIME, 30_000),
        ],
        primary_trace_clock=perfetto_pb2.BUILTIN_CLOCK_MONOTONIC,
    )
    first_lane = builder.add_merged_track_lane("Kernel lane 0", "cuda-kernels")
    second_lane = builder.add_merged_track_lane("Kernel lane 1", "cuda-kernels")
    mapping = StackMapping(
        path=("usr", "lib", "libcuda.so"),
        build_id=b"\x01\x02build",
        start=0x1000,
        end=0x9000,
    )
    launch_event = builder.add_instant_event(
        first_lane,
        "launch",
        100,
        categories=("cuda", "kernel"),
    )
    launch_event.add_annotations(
        {
            "launch": {
                "grid": [UInt(128), UInt(2), UInt(1)],
                "occupancy": 0.75,
                "cooperative": True,
                "stream": Pointer(0xFEED),
                "kernel": "vector_add",
            }
        }
    )
    launch_event.set_source_location(
        SourceLocation("/src/cuda.cc", "launch_kernel", 88)
    ).set_callstack(
        [
            StackFrame(function_name="main"),
            StackFrame(
                function_name="launch_kernel",
                mapping=mapping,
                rel_pc=0x123,
                source_path="/src/cuda.cc",
                line_number=88,
                kind=perfetto_pb2.Frame.KIND_NATIVE,
            ),
        ]
    )
    builder.add_instant_event(second_lane, "inline", 110).set_inline_callstack(
        [InlineFrame("outer"), InlineFrame("inner", "/src/cuda.cc", 88)]
    )
    builder.add_legacy_event(
        first_lane,
        "legacy",
        120,
        LegacyEvent(
            phase="X",
            duration_us=20,
            thread_duration_us=10,
            id=0x123,
            id_type="global",
            id_scope="scope",
            bind_id=0x456,
            flow_direction=perfetto_pb2.TrackEvent.LegacyEvent.FLOW_INOUT,
            pid_override=10,
            tid_override=11,
        ),
        timestamp_clock_id=perfetto_pb2.BUILTIN_CLOCK_REALTIME,
    )

    trace_type = _official_trace_type()
    trace = trace_type()
    consumed = trace.ParseFromString(builder.serialize())
    assert consumed > 0

    descriptors = [
        packet.track_descriptor
        for packet in trace.packet
        if packet.HasField("track_descriptor")
        and packet.track_descriptor.HasField("sibling_merge_behavior")
    ]
    assert len(descriptors) == 2
    assert {descriptor.sibling_merge_key for descriptor in descriptors} == {
        "cuda-kernels"
    }

    events = [
        packet for packet in trace.packet if packet.HasField("track_event")
    ]
    launch = events[0]
    assert [entry.name for entry in launch.interned_data.event_categories] == [
        "cuda",
        "kernel",
    ]
    assert list(launch.track_event.category_iids) == [1, 2]
    assert launch.track_event.HasField("source_location_iid")
    assert launch.track_event.HasField("callstack_iid")
    assert len(launch.interned_data.source_locations) == 1
    assert len(launch.interned_data.mappings) == 1
    assert len(launch.interned_data.frames) == 2
    assert len(launch.interned_data.callstacks) == 1
    root = launch.track_event.debug_annotations[0]
    fields = {entry.name_iid: entry for entry in root.dict_entries}
    assert len(fields) == 5
    assert any(len(entry.array_values) == 3 for entry in fields.values())
    assert events[1].track_event.callstack.frames[1].function_name == "inner"

    legacy_packet = events[2]
    legacy = legacy_packet.track_event.legacy_event
    assert legacy.phase == ord("X")
    assert legacy.global_id == 0x123
    assert legacy.bind_id == 0x456
    assert legacy_packet.timestamp_clock_id == perfetto_pb2.BUILTIN_CLOCK_REALTIME

    defaults = next(
        packet.trace_packet_defaults
        for packet in trace.packet
        if packet.HasField("trace_packet_defaults")
    )
    snapshot = next(
        packet.clock_snapshot
        for packet in trace.packet
        if packet.HasField("clock_snapshot")
    )
    assert defaults.timestamp_clock_id == 65
    assert len(snapshot.clocks) == 3
    assert snapshot.clocks[0].unit_multiplier_ns == 10
