"""Main builder class for creating Perfetto traces."""

from typing import Optional, Dict, Any

# Import will be available after protobuf compilation
try:
    from .proto import perfetto_pb2 as perfetto
except ImportError:
    # This will be resolved after setup.py runs
    perfetto = None  # type: ignore[assignment]

from .annotations import TrackEventWrapper


# Type stubs for type checking when perfetto is not available
if not perfetto:
    class _MockPerfetto:
        """Mock perfetto module for type checking."""
        class Trace:
            """Mock Trace class."""

        class TrackEvent:
            """Mock TrackEvent class."""
            TYPE_SLICE_BEGIN = 1
            TYPE_SLICE_END = 2
            TYPE_INSTANT = 3
            TYPE_COUNTER = 4


class PerfettoTraceBuilder:
    """
    Builder for creating Perfetto traces with a clean API.

    This class provides a medium-level abstraction over the Perfetto protobuf format,
    making it easy to create traces for retrocomputer emulators and similar applications.
    """

    def __init__(self, process_name: str):
        """
        Initialize a new trace builder.

        Args:
            process_name: Name of the process being traced
        """
        if perfetto is None:
            raise ImportError(
                "Perfetto protobuf module not found. "
                "Please run 'python setup.py build' to generate protobuf files."
            )

        self.trace = perfetto.Trace()
        self.last_track_uuid = 0
        self.trusted_packet_sequence_id = 0x123
        self.pid = 1234
        self.last_tid = 1
        self.track_metadata: Dict[int, Dict[str, Any]] = {}

        # Create the main process
        self.process_uuid = self.add_process(process_name)

    def _next_uuid(self) -> int:
        """Generate the next track UUID."""
        self.last_track_uuid += 1
        return self.last_track_uuid

    def _next_tid(self) -> int:
        """Generate the next thread ID."""
        tid = self.last_tid
        self.last_tid += 1
        return tid

    def add_process(self, process_name: str) -> int:
        """
        Add a process descriptor to the trace.

        Args:
            process_name: Name of the process

        Returns:
            UUID of the created process track
        """
        track_uuid = self._next_uuid()

        packet = self.trace.packet.add()
        packet.track_descriptor.uuid = track_uuid
        packet.track_descriptor.process.pid = self.pid
        packet.track_descriptor.process.process_name = process_name

        self.track_metadata[track_uuid] = {
            'type': 'process',
            'name': process_name
        }

        return track_uuid

    def add_thread(self, thread_name: str, process_uuid: Optional[int] = None) -> int:
        """
        Add a thread descriptor to the trace.

        Args:
            thread_name: Name of the thread
            process_uuid: Parent process UUID (defaults to main process)

        Returns:
            UUID of the created thread track
        """
        if process_uuid is None:
            process_uuid = self.process_uuid

        track_uuid = self._next_uuid()
        tid = self._next_tid()

        packet = self.trace.packet.add()
        packet.track_descriptor.uuid = track_uuid
        packet.track_descriptor.parent_uuid = process_uuid
        packet.track_descriptor.thread.pid = self.pid
        packet.track_descriptor.thread.tid = tid
        packet.track_descriptor.thread.thread_name = thread_name

        self.track_metadata[track_uuid] = {
            'type': 'thread',
            'name': thread_name,
            'parent': process_uuid
        }

        return track_uuid

    def begin_slice(self, track_uuid: int, name: str, timestamp: int) -> TrackEventWrapper:
        """
        Begin a duration slice event.

        Args:
            track_uuid: Track to add the event to
            name: Name of the event
            timestamp: Timestamp in nanoseconds

        Returns:
            TrackEventWrapper for adding annotations
        """
        packet = self.trace.packet.add()
        packet.timestamp = timestamp
        packet.track_event.type = perfetto.TrackEvent.TYPE_SLICE_BEGIN
        packet.track_event.track_uuid = track_uuid
        packet.track_event.name = name
        packet.trusted_packet_sequence_id = self.trusted_packet_sequence_id

        return TrackEventWrapper(packet.track_event)

    def end_slice(self, track_uuid: int, timestamp: int) -> None:
        """
        End a duration slice event.

        Args:
            track_uuid: Track containing the slice
            timestamp: Timestamp in nanoseconds
        """
        packet = self.trace.packet.add()
        packet.timestamp = timestamp
        packet.track_event.type = perfetto.TrackEvent.TYPE_SLICE_END
        packet.track_event.track_uuid = track_uuid
        packet.trusted_packet_sequence_id = self.trusted_packet_sequence_id

    def add_instant_event(self, track_uuid: int, name: str, timestamp: int) -> TrackEventWrapper:
        """
        Add an instant (point-in-time) event.

        Args:
            track_uuid: Track to add the event to
            name: Name of the event
            timestamp: Timestamp in nanoseconds

        Returns:
            TrackEventWrapper for adding annotations
        """
        packet = self.trace.packet.add()
        packet.timestamp = timestamp
        packet.track_event.type = perfetto.TrackEvent.TYPE_INSTANT
        packet.track_event.track_uuid = track_uuid
        packet.track_event.name = name
        packet.trusted_packet_sequence_id = self.trusted_packet_sequence_id

        return TrackEventWrapper(packet.track_event)

    def add_counter_track(self, name: str, unit: str = "",
                         parent_uuid: Optional[int] = None) -> int:
        """
        Add a counter track for numeric values over time.

        Args:
            name: Name of the counter
            unit: Unit of measurement (e.g., "bytes", "ms")
            parent_uuid: Parent track UUID (defaults to main process)

        Returns:
            UUID of the created counter track
        """
        if parent_uuid is None:
            parent_uuid = self.process_uuid

        track_uuid = self._next_uuid()

        packet = self.trace.packet.add()
        packet.track_descriptor.uuid = track_uuid
        packet.track_descriptor.parent_uuid = parent_uuid
        packet.track_descriptor.name = f"{name} ({unit})" if unit else name

        self.track_metadata[track_uuid] = {
            'type': 'counter',
            'name': name,
            'unit': unit,
            'parent': parent_uuid
        }

        return track_uuid

    def update_counter(self, track_uuid: int, value: float, timestamp: int) -> None:
        """
        Update a counter value.

        Args:
            track_uuid: Counter track UUID
            value: New counter value
            timestamp: Timestamp in nanoseconds
        """
        packet = self.trace.packet.add()
        packet.timestamp = timestamp
        packet.track_event.type = perfetto.TrackEvent.TYPE_COUNTER
        packet.track_event.track_uuid = track_uuid

        if isinstance(value, int):
            packet.track_event.counter_value = value
        else:
            packet.track_event.double_counter_value = value

        packet.trusted_packet_sequence_id = self.trusted_packet_sequence_id

    def add_flow(self, track_uuid: int, name: str, timestamp: int,
                 flow_id: int, terminating: bool = False) -> TrackEventWrapper:
        """
        Add a flow event to connect events across tracks.

        Args:
            track_uuid: Track to add the event to
            name: Name of the event
            timestamp: Timestamp in nanoseconds
            flow_id: Unique flow identifier
            terminating: Whether this terminates the flow

        Returns:
            TrackEventWrapper for adding annotations
        """
        event = self.add_instant_event(track_uuid, name, timestamp)

        if terminating:
            event.event.terminating_flow_ids.append(flow_id)
        else:
            event.event.flow_ids.append(flow_id)

        return event

    def serialize(self) -> bytes:
        """
        Serialize the trace to Perfetto binary format.

        Returns:
            Binary protobuf data
        """
        return self.trace.SerializeToString()

    def save(self, filename: str) -> None:
        """
        Save the trace to a file.

        Args:
            filename: Path to save the trace to
        """
        with open(filename, 'wb') as file:
            file.write(self.serialize())

    def get_track_info(self, track_uuid: int) -> Dict[str, Any]:
        """
        Get metadata about a track.

        Args:
            track_uuid: Track UUID to query

        Returns:
            Dictionary with track metadata
        """
        return self.track_metadata.get(track_uuid, {})
    
    def get_all_tracks(self) -> list:
        """
        Get all tracks in the trace.

        Returns:
            List of (uuid, metadata) tuples for all tracks
        """
        return list(self.track_metadata.items())
