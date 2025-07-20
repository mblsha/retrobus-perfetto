"""Basic tests for PerfettoTraceBuilder."""
# pylint: disable=W0621  # redefined-outer-name is expected for pytest fixtures

from unittest.mock import Mock, patch
import pytest


# Mock the protobuf module for testing without compilation
@pytest.fixture
def perfetto_mock():
    """Create mock perfetto protobuf module."""
    mock = Mock()

    # Mock Trace class
    mock.Trace = Mock
    mock.Trace.return_value = Mock(packet=Mock(add=Mock(return_value=Mock())))

    # Mock TracePacket
    mock.TracePacket = Mock

    # Mock TrackEvent types
    mock.TrackEvent = Mock()
    mock.TrackEvent.TYPE_SLICE_BEGIN = 1
    mock.TrackEvent.TYPE_SLICE_END = 2
    mock.TrackEvent.TYPE_INSTANT = 3
    mock.TrackEvent.TYPE_COUNTER = 4

    # Mock BuiltinClock
    mock.BuiltinClock = Mock()
    mock.BuiltinClock.BUILTIN_CLOCK_BOOTTIME = 6

    return mock


@pytest.fixture
def trace_builder(perfetto_mock):
    """Create a PerfettoTraceBuilder with mocked protobuf."""
    # Patch the module before importing
    import sys  # pylint: disable=C0415
    if 'retrobus_perfetto.proto.perfetto_pb2' in sys.modules:
        del sys.modules['retrobus_perfetto.proto.perfetto_pb2']
    if 'retrobus_perfetto.builder' in sys.modules:
        del sys.modules['retrobus_perfetto.builder']
    if 'retrobus_perfetto' in sys.modules:
        del sys.modules['retrobus_perfetto']

    with patch.dict('sys.modules', {'retrobus_perfetto.proto.perfetto_pb2': perfetto_mock}):
        from retrobus_perfetto import PerfettoTraceBuilder  # pylint: disable=C0415
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


def test_serialization(trace_builder, perfetto_mock):  # pylint: disable=W0613
    """Test trace serialization."""
    # Mock the SerializeToString method
    mock_trace = Mock()
    mock_trace.SerializeToString.return_value = b"mock_trace_data"
    trace_builder.trace = mock_trace

    data = trace_builder.serialize()
    assert data == b"mock_trace_data"
    mock_trace.SerializeToString.assert_called_once()


def test_save_to_file(trace_builder, tmp_path, perfetto_mock):  # pylint: disable=W0613
    """Test saving trace to file."""
    # Mock the SerializeToString method
    mock_trace = Mock()
    mock_trace.SerializeToString.return_value = b"mock_trace_data"
    trace_builder.trace = mock_trace

    # Save to temporary file
    output_file = tmp_path / "test.perfetto-trace"
    trace_builder.save(str(output_file))

    # Verify file contents
    assert output_file.exists()
    assert output_file.read_bytes() == b"mock_trace_data"


def test_annotation_type_detection():
    """Test automatic type detection in annotations."""
    from retrobus_perfetto.annotations import DebugAnnotationBuilder  # pylint: disable=C0415

    mock_ann = Mock()
    mock_ann.dict_entries = Mock()
    mock_ann.dict_entries.add.return_value = Mock()

    ann_builder = DebugAnnotationBuilder(mock_ann)

    # Test different types
    ann_builder.auto("test_int", 42)
    ann_builder.auto("test_bool", True)
    ann_builder.auto("test_float", 3.14)
    ann_builder.auto("test_string", "hello")
    ann_builder.auto("test_object", {"key": "value"})

    assert mock_ann.dict_entries.add.call_count == 5


def test_pointer_annotation_heuristic():
    """Test that certain field names are treated as pointers."""
    from retrobus_perfetto.annotations import TrackEventWrapper  # pylint: disable=C0415

    mock_event = Mock()
    mock_event.debug_annotations = Mock()
    mock_ann = Mock()
    mock_event.debug_annotations.add.return_value = mock_ann

    wrapper = TrackEventWrapper(mock_event)
    wrapper.add_annotations({
        "pc": 0x1234,           # Should be pointer
        "address": 0x5678,      # Should be pointer
        "count": 100,           # Should be int
        "stack_pointer": 0x7FFF # Should be pointer
    })

    # Verify correct number of annotations added
    assert mock_event.debug_annotations.add.call_count == 4
