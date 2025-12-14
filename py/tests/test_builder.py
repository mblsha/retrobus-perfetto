"""Basic functional tests for PerfettoTraceBuilder."""
# ruff: noqa: F811  # redefined-outer-name is expected for pytest fixtures

import pytest
from retrobus_perfetto import PerfettoTraceBuilder, resolve_interned_trace
from retrobus_perfetto.proto import perfetto_pb2


@pytest.fixture
def trace_builder():
    """Create a PerfettoTraceBuilder instance."""
    return PerfettoTraceBuilder("Test Process")


def test_builder_initialization(trace_builder):
    """Test builder initializes correctly."""
    assert trace_builder.process_uuid == 1
    assert trace_builder.pid == 1234
    assert trace_builder.last_track_uuid == 1
    assert trace_builder.last_tid == 1


def test_add_thread(trace_builder):
    """Test adding threads."""
    thread1 = trace_builder.add_thread("Thread 1")
    thread2 = trace_builder.add_thread("Thread 2")

    assert thread1 == 2
    assert thread2 == 3
    assert trace_builder.last_track_uuid == 3

    # Check metadata
    assert trace_builder.get_track_info(thread1)['name'] == "Thread 1"
    assert trace_builder.get_track_info(thread2)['name'] == "Thread 2"


def test_slice_events(trace_builder):
    """Test begin/end slice events."""
    thread = trace_builder.add_thread("Test Thread")

    # Begin slice
    event = trace_builder.begin_slice(thread, "test_function", 1000)
    assert event is not None

    # Add annotations
    event.add_annotations({
        "test_int": 42,
        "test_string": "hello",
        "test_bool": True,
        "test_float": 3.14
    })

    # End slice
    trace_builder.end_slice(thread, 2000)
    
    # Verify trace structure
    data = trace_builder.serialize()
    trace = perfetto_pb2.Trace()
    trace.ParseFromString(data)
    resolve_interned_trace(trace, inplace=True)
    
    # Should have 3 packets: process, thread, slice begin, slice end
    assert len(trace.packet) == 4
    
    # Verify slice begin event
    slice_begin = trace.packet[2]
    assert slice_begin.timestamp == 1000
    assert slice_begin.track_event.type == perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN
    assert slice_begin.track_event.name == "test_function"
    assert len(slice_begin.track_event.debug_annotations) == 4


def test_instant_events(trace_builder):
    """Test instant events."""
    thread = trace_builder.add_thread("Test Thread")

    event = trace_builder.add_instant_event(thread, "test_event", 1500)
    assert event is not None

    # Test annotation builder
    with event.annotation("test_group") as ann:
        ann.integer("value", 123)
        ann.string("name", "test")
        ann.bool("flag", False)
    
    # Verify event structure
    data = trace_builder.serialize()
    trace = perfetto_pb2.Trace()
    trace.ParseFromString(data)
    resolve_interned_trace(trace, inplace=True)
    
    # Find instant event packet
    instant_packet = trace.packet[2]
    assert instant_packet.timestamp == 1500
    assert instant_packet.track_event.type == perfetto_pb2.TrackEvent.TYPE_INSTANT
    assert instant_packet.track_event.name == "test_event"
    
    # Check structured annotation
    assert len(instant_packet.track_event.debug_annotations) == 1
    ann = instant_packet.track_event.debug_annotations[0]
    assert ann.name == "test_group"
    assert len(ann.dict_entries) == 3


def test_counter_tracks(trace_builder):
    """Test counter tracks and updates."""
    counter = trace_builder.add_counter_track("Memory", "MB")
    assert counter == 2

    # Update counter values
    trace_builder.update_counter(counter, 100, 1000)
    trace_builder.update_counter(counter, 150.5, 2000)

    # Check metadata
    info = trace_builder.get_track_info(counter)
    assert info['type'] == 'counter'
    assert info['name'] == 'Memory'
    assert info['unit'] == 'MB'
    
    # Verify counter updates in trace
    data = trace_builder.serialize()
    trace = perfetto_pb2.Trace()
    trace.ParseFromString(data)
    
    # Counter track descriptor
    counter_desc = trace.packet[1]
    assert counter_desc.track_descriptor.name == "Memory (MB)"
    # Note: Python implementation doesn't set counter.unit_name field
    
    # Counter updates
    update1 = trace.packet[2]
    assert update1.timestamp == 1000
    assert update1.track_event.type == perfetto_pb2.TrackEvent.TYPE_COUNTER
    assert update1.track_event.counter_value == 100
    
    update2 = trace.packet[3]
    assert update2.timestamp == 2000
    assert update2.track_event.double_counter_value == 150.5


def test_flow_events(trace_builder):
    """Test flow events."""
    thread1 = trace_builder.add_thread("Thread 1")
    thread2 = trace_builder.add_thread("Thread 2")

    flow_id = 12345

    # Start flow
    event1 = trace_builder.add_flow(thread1, "Start", 1000, flow_id)
    assert event1 is not None

    # Continue flow
    event2 = trace_builder.add_flow(thread2, "Continue", 2000, flow_id)
    assert event2 is not None

    # Terminate flow
    event3 = trace_builder.add_flow(thread2, "End", 3000, flow_id, terminating=True)
    assert event3 is not None
    
    # Verify flow events
    data = trace_builder.serialize()
    trace = perfetto_pb2.Trace()
    trace.ParseFromString(data)
    
    # First flow event
    flow1 = trace.packet[3]
    assert flow1.timestamp == 1000
    assert flow1.track_event.flow_ids[0] == flow_id
    
    # Continue flow
    flow2 = trace.packet[4]
    assert flow2.timestamp == 2000
    assert flow2.track_event.flow_ids[0] == flow_id
    
    # Terminate flow
    flow3 = trace.packet[5]
    assert flow3.timestamp == 3000
    # Terminating flows only have terminating_flow_ids, not flow_ids
    assert flow3.track_event.terminating_flow_ids[0] == flow_id


def test_serialization(trace_builder):
    """Test trace serialization."""
    # Add some content
    thread = trace_builder.add_thread("Test")
    trace_builder.add_instant_event(thread, "event", 1000)
    
    data = trace_builder.serialize()
    assert isinstance(data, bytes)
    assert len(data) > 0
    
    # Verify it's valid protobuf
    trace = perfetto_pb2.Trace()
    trace.ParseFromString(data)
    assert len(trace.packet) >= 3  # process, thread, event


def test_save_to_file(trace_builder, tmp_path):
    """Test saving trace to file."""
    # Add some content
    thread = trace_builder.add_thread("Test")
    trace_builder.add_instant_event(thread, "event", 1000)
    
    # Save to temporary file
    output_file = tmp_path / "test.perfetto-trace"
    trace_builder.save(str(output_file))

    # Verify file contents
    assert output_file.exists()
    
    # Load and parse the file
    data = output_file.read_bytes()
    trace = perfetto_pb2.Trace()
    trace.ParseFromString(data)
    assert len(trace.packet) >= 3


def test_annotation_type_detection():
    """Test automatic type detection in annotations."""
    builder = PerfettoTraceBuilder("Test")
    thread = builder.add_thread("Test Thread")
    
    event = builder.begin_slice(thread, "test", 1000)
    event.add_annotations({
        "test_int": 42,
        "test_bool": True,
        "test_float": 3.14,
        "test_string": "hello",
        "test_object": {"key": "value"}  # Will be converted to string
    })
    
    # Verify annotations in trace
    data = builder.serialize()
    trace = perfetto_pb2.Trace()
    trace.ParseFromString(data)
    resolve_interned_trace(trace, inplace=True)
    
    annotations = trace.packet[2].track_event.debug_annotations
    
    # Find each annotation and verify type
    ann_dict = {ann.name: ann for ann in annotations}
    
    assert ann_dict["test_int"].int_value == 42
    assert ann_dict["test_bool"].bool_value is True
    assert ann_dict["test_float"].double_value == 3.14
    assert ann_dict["test_string"].string_value == "hello"
    assert ann_dict["test_object"].string_value == "{'key': 'value'}"


def test_pointer_annotation_heuristic():
    """Test that certain field names are treated as pointers."""
    builder = PerfettoTraceBuilder("Test")
    thread = builder.add_thread("Test Thread")
    
    event = builder.begin_slice(thread, "test", 1000)
    event.add_annotations({
        "reg_pc": 0x1234,           # Should be pointer (ends with _pc)
        "mem_address": 0x5678,      # Should be pointer (ends with _address)
        "count": 100,               # Should be int
        "stack_pointer": 0x7FFF     # Should be pointer (ends with _pointer)
    })
    
    # Verify annotations in trace
    data = builder.serialize()
    trace = perfetto_pb2.Trace()
    trace.ParseFromString(data)
    resolve_interned_trace(trace, inplace=True)
    
    annotations = trace.packet[2].track_event.debug_annotations
    ann_dict = {ann.name: ann for ann in annotations}
    
    # Pointer fields should have pointer_value
    assert ann_dict["reg_pc"].pointer_value == 0x1234
    assert ann_dict["mem_address"].pointer_value == 0x5678
    assert ann_dict["stack_pointer"].pointer_value == 0x7FFF
    
    # Non-pointer field should have int_value
    assert ann_dict["count"].int_value == 100


def test_get_all_tracks(trace_builder):
    """Test getting all tracks."""
    # Add various tracks
    trace_builder.add_thread("Thread 1")
    trace_builder.add_thread("Thread 2")
    trace_builder.add_counter_track("CPU", "%")
    
    tracks = trace_builder.get_all_tracks()
    
    # Should have process + 3 tracks
    assert len(tracks) == 4
    
    # Check track names
    track_names = [info['name'] for uuid, info in tracks]
    assert "Test Process" in track_names
    assert "Thread 1" in track_names
    assert "Thread 2" in track_names
    assert "CPU" in track_names


def test_default_encoding_is_interned():
    """Default encoding emits dictionaries + uses *_iid fields."""
    builder = PerfettoTraceBuilder("Test")
    thread = builder.add_thread("Test Thread")

    event = builder.add_instant_event(thread, "test_event", 1500)
    event.add_annotations({"arg_string": "hello", "arg_int": 42})

    # Emit a second event reusing the same strings.
    builder.add_instant_event(thread, "test_event", 1600)

    trace = perfetto_pb2.Trace()
    trace.ParseFromString(builder.serialize())

    first_packet = trace.packet[2]
    assert first_packet.sequence_flags & perfetto_pb2.TracePacket.SEQ_NEEDS_INCREMENTAL_STATE
    assert (
        first_packet.sequence_flags
        & perfetto_pb2.TracePacket.SEQ_INCREMENTAL_STATE_CLEARED
    )
    assert first_packet.track_event.HasField("name_iid")
    assert not first_packet.track_event.HasField("name")

    assert first_packet.HasField("interned_data")
    assert len(first_packet.interned_data.event_names) == 1
    assert first_packet.interned_data.event_names[0].name == "test_event"
    assert first_packet.interned_data.event_names[0].iid == first_packet.track_event.name_iid

    ann_names = {e.name: e.iid for e in first_packet.interned_data.debug_annotation_names}
    assert set(ann_names) == {"arg_string", "arg_int"}

    anns_by_iid = {
        a.name_iid: a for a in first_packet.track_event.debug_annotations if a.HasField("name_iid")
    }
    assert anns_by_iid[ann_names["arg_int"]].int_value == 42

    str_ann = anns_by_iid[ann_names["arg_string"]]
    assert str_ann.HasField("string_value_iid")
    str_values = {e.str: e.iid for e in first_packet.interned_data.debug_annotation_string_values}
    assert str_values[b"hello"] == str_ann.string_value_iid

    second_packet = trace.packet[3]
    assert second_packet.sequence_flags & perfetto_pb2.TracePacket.SEQ_NEEDS_INCREMENTAL_STATE
    assert (
        second_packet.sequence_flags
        & perfetto_pb2.TracePacket.SEQ_INCREMENTAL_STATE_CLEARED
    ) == 0
    assert second_packet.track_event.name_iid == first_packet.track_event.name_iid
    assert not second_packet.HasField("interned_data")

def test_inline_encoding_uses_strings():
    builder = PerfettoTraceBuilder("Test", encoding="inline")
    thread = builder.add_thread("Test Thread")
    event = builder.add_instant_event(thread, "test_event", 1500)
    event.add_annotations({"arg_string": "hello", "arg_int": 42})

    trace = perfetto_pb2.Trace()
    trace.ParseFromString(builder.serialize())

    packet = trace.packet[2]
    assert packet.track_event.HasField("name")
    assert not packet.track_event.HasField("name_iid")
    assert not packet.HasField("interned_data")

    anns = packet.track_event.debug_annotations
    assert {a.name for a in anns} == {"arg_string", "arg_int"}
    assert any(a.HasField("string_value") and a.string_value == "hello" for a in anns)
    assert any(a.HasField("int_value") and a.int_value == 42 for a in anns)


def test_resolve_interned_trace_restores_strings():
    """resolve_interned_trace makes interned traces readable by string-based tooling."""
    from retrobus_perfetto import resolve_interned_trace

    builder = PerfettoTraceBuilder("Test", encoding="interned")
    thread = builder.add_thread("Test Thread")
    event = builder.add_instant_event(thread, "test_event", 1500)
    event.add_annotations({"arg_string": "hello"})

    trace = perfetto_pb2.Trace()
    trace.ParseFromString(builder.serialize())

    resolved = resolve_interned_trace(trace, inplace=False)
    packet = resolved.packet[2]
    assert packet.track_event.name == "test_event"
    assert packet.track_event.debug_annotations[0].name == "arg_string"
    assert packet.track_event.debug_annotations[0].string_value == "hello"
