"""Main builder class for creating Perfetto traces."""

from typing import Any, Dict, Optional

# Import will be available after protobuf compilation
try:
    from .proto import perfetto_pb2 as perfetto
except ImportError:
    # This will be resolved after setup.py runs
    perfetto = None  # type: ignore[assignment]

from .annotations import TrackEventWrapper
from .interning import InterningState


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

    def __init__(self, process_name: str, encoding: str = "interned"):
        """
        Initialize a new trace builder.

        Args:
            process_name: Name of the process being traced
            encoding: "interned" (default) or "inline"
        """
        if perfetto is None:
            raise ImportError(
                "Perfetto protobuf module not found. "
                "Please run 'python setup.py build' to generate protobuf files."
            )

        if encoding not in {"inline", "interned"}:
            raise ValueError(f"Unknown encoding: {encoding!r}")

        self.trace = perfetto.Trace()
        self.last_track_uuid = 0
        self.trusted_packet_sequence_id = 0x123
        self.pid = 1234
        self.last_tid = 1
        self.track_metadata: Dict[int, Dict[str, Any]] = {}
        self._encoding = encoding
        self._interning_state: Optional[InterningState] = (
            InterningState() if encoding == "interned" else None
        )

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

    def _add_track_event(
        self,
        track_uuid: int,
        timestamp: int,
        event_type: int,
        name: Optional[str] = None,
    ):
        """Create a packet with a populated track event."""
        packet = self.trace.packet.add()
        packet.timestamp = timestamp
        packet.track_event.type = event_type
        packet.track_event.track_uuid = track_uuid
        if name is not None:
            if self._interning_state is not None:
                packet.track_event.name_iid = self._interning_state.intern_event_name(
                    name, packet
                )
            else:
                packet.track_event.name = name
        packet.trusted_packet_sequence_id = self.trusted_packet_sequence_id
        return packet

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
        event = self._add_track_event(
            track_uuid,
            timestamp,
            perfetto.TrackEvent.TYPE_SLICE_BEGIN,
            name,
        )

        return TrackEventWrapper(
            event.track_event, packet=event, interning_state=self._interning_state
        )

    def end_slice(self, track_uuid: int, timestamp: int) -> None:
        """
        End a duration slice event.

        Args:
            track_uuid: Track containing the slice
            timestamp: Timestamp in nanoseconds
        """
        self._add_track_event(track_uuid, timestamp, perfetto.TrackEvent.TYPE_SLICE_END)

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
        event = self._add_track_event(
            track_uuid,
            timestamp,
            perfetto.TrackEvent.TYPE_INSTANT,
            name,
        )

        return TrackEventWrapper(
            event.track_event, packet=event, interning_state=self._interning_state
        )

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
        event = self._add_track_event(
            track_uuid,
            timestamp,
            perfetto.TrackEvent.TYPE_COUNTER,
        )

        if isinstance(value, int):
            event.track_event.counter_value = value
        else:
            event.track_event.double_counter_value = value

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
