"""Basic tests for PerfettoTraceBuilder."""

import pytest
from unittest.mock import Mock, patch


# Mock the protobuf module for testing without compilation
@pytest.fixture
def mock_perfetto():
    """Create mock perfetto protobuf module."""
    mock = Mock()
    
    # Mock Trace and TracePacket
    mock.Trace = Mock
    mock.TracePacket = Mock
    
    # Mock TrackEvent types
    mock.TrackEvent.TYPE_SLICE_BEGIN = 1
    mock.TrackEvent.TYPE_SLICE_END = 2
    mock.TrackEvent.TYPE_INSTANT = 3
    mock.TrackEvent.TYPE_COUNTER = 4
    
    return mock


@pytest.fixture
def builder(mock_perfetto):
    """Create a PerfettoTraceBuilder with mocked protobuf."""
    with patch('retrobus_perfetto.builder.perfetto', mock_perfetto):
        from retrobus_perfetto import PerfettoTraceBuilder
        return PerfettoTraceBuilder("Test Process")


def test_builder_initialization(builder):
    """Test builder initializes correctly."""
    assert builder.process_uuid == 1
    assert builder.pid == 1234
    assert builder.last_track_uuid == 1
    assert builder.last_tid == 1


def test_add_thread(builder):
    """Test adding threads."""
    thread1 = builder.add_thread("Thread 1")
    thread2 = builder.add_thread("Thread 2")
    
    assert thread1 == 2
    assert thread2 == 3
    assert builder.last_track_uuid == 3
    
    # Check metadata
    assert builder.get_track_info(thread1)['name'] == "Thread 1"
    assert builder.get_track_info(thread2)['name'] == "Thread 2"


def test_slice_events(builder):
    """Test begin/end slice events."""
    thread = builder.add_thread("Test Thread")
    
    # Begin slice
    event = builder.begin_slice(thread, "test_function", 1000)
    assert event is not None
    
    # Add annotations
    event.add_annotations({
        "test_int": 42,
        "test_string": "hello",
        "test_bool": True,
        "test_float": 3.14
    })
    
    # End slice
    builder.end_slice(thread, 2000)


def test_instant_events(builder):
    """Test instant events."""
    thread = builder.add_thread("Test Thread")
    
    event = builder.add_instant_event(thread, "test_event", 1500)
    assert event is not None
    
    # Test annotation builder
    with event.annotation("test_group") as ann:
        ann.integer("value", 123)
        ann.string("name", "test")
        ann.bool("flag", False)


def test_counter_tracks(builder):
    """Test counter tracks and updates."""
    counter = builder.add_counter_track("Memory", "MB")
    assert counter == 2
    
    # Update counter values
    builder.update_counter(counter, 100, 1000)
    builder.update_counter(counter, 150.5, 2000)
    
    # Check metadata
    info = builder.get_track_info(counter)
    assert info['type'] == 'counter'
    assert info['name'] == 'Memory'
    assert info['unit'] == 'MB'


def test_flow_events(builder):
    """Test flow events."""
    thread1 = builder.add_thread("Thread 1")
    thread2 = builder.add_thread("Thread 2")
    
    flow_id = 12345
    
    # Start flow
    event1 = builder.add_flow(thread1, "Start", 1000, flow_id)
    assert event1 is not None
    
    # Continue flow
    event2 = builder.add_flow(thread2, "Continue", 2000, flow_id)
    
    # Terminate flow
    event3 = builder.add_flow(thread2, "End", 3000, flow_id, terminating=True)


def test_serialization(builder, mock_perfetto):
    """Test trace serialization."""
    # Mock the SerializeToString method
    mock_trace = Mock()
    mock_trace.SerializeToString.return_value = b"mock_trace_data"
    builder.trace = mock_trace
    
    data = builder.serialize()
    assert data == b"mock_trace_data"
    mock_trace.SerializeToString.assert_called_once()


def test_save_to_file(builder, tmp_path, mock_perfetto):
    """Test saving trace to file."""
    # Mock the SerializeToString method
    mock_trace = Mock()
    mock_trace.SerializeToString.return_value = b"mock_trace_data"
    builder.trace = mock_trace
    
    # Save to temporary file
    output_file = tmp_path / "test.perfetto-trace"
    builder.save(str(output_file))
    
    # Verify file contents
    assert output_file.exists()
    assert output_file.read_bytes() == b"mock_trace_data"


def test_annotation_type_detection():
    """Test automatic type detection in annotations."""
    from retrobus_perfetto.annotations import DebugAnnotationBuilder
    
    mock_ann = Mock()
    mock_ann.dict_entries = Mock()
    mock_ann.dict_entries.add.return_value = Mock()
    
    builder = DebugAnnotationBuilder(mock_ann)
    
    # Test different types
    builder.auto("test_int", 42)
    builder.auto("test_bool", True)
    builder.auto("test_float", 3.14)
    builder.auto("test_string", "hello")
    builder.auto("test_object", {"key": "value"})
    
    assert mock_ann.dict_entries.add.call_count == 5


def test_pointer_annotation_heuristic():
    """Test that certain field names are treated as pointers."""
    from retrobus_perfetto.annotations import TrackEventWrapper
    
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