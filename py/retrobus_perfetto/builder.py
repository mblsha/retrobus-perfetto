"""Main builder class for creating Perfetto traces."""

from typing import Any, Dict, Optional, Sequence, Union

from .proto import perfetto_pb2 as perfetto

from .annotations import TrackEventWrapper
from .interning import InterningState
from .models import ClockReading, LegacyEvent


class PerfettoTraceBuilder:
    """
    Builder for creating Perfetto traces with a clean API.

    This class provides a medium-level abstraction over the Perfetto protobuf format,
    making it easy to create traces for retrocomputer emulators and similar applications.
    """

    def __init__(
        self,
        process_name: str,
        encoding: str = "interned",
        *,
        annotation_max_depth: int = 64,
        timestamp_clock_id: Optional[int] = None,
    ):
        """
        Initialize a new trace builder.

        Args:
            process_name: Name of the process being traced
            encoding: "interned" (default) or "inline"
            annotation_max_depth: Maximum structured annotation container depth
            timestamp_clock_id: Optional per-sequence default timestamp clock
        """
        if encoding not in {"inline", "interned"}:
            raise ValueError(f"Unknown encoding: {encoding!r}")
        if annotation_max_depth < 1:
            raise ValueError("annotation_max_depth must be at least 1")

        self.trace = perfetto.Trace()
        self.last_track_uuid = 0
        self.trusted_packet_sequence_id = 0x123
        self.pid = 1234
        self.last_tid = 1
        self.track_metadata: Dict[int, Dict[str, Any]] = {}
        self._encoding = encoding
        self._annotation_max_depth = annotation_max_depth
        self._default_timestamp_clock_id: Optional[int] = None
        self._interning_state: Optional[InterningState] = (
            InterningState() if encoding == "interned" else None
        )

        # Create the main process
        self.process_uuid = self.add_process(process_name)
        if timestamp_clock_id is not None:
            self.set_default_timestamp_clock(timestamp_clock_id)

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

    def add_track(
        self,
        name: str,
        parent_uuid: Optional[int] = None,
        *,
        sibling_merge_behavior: Optional[int] = None,
        sibling_merge_key: Optional[Union[str, int]] = None,
    ) -> int:
        """Add a generic nestable TrackEvent track.

        Set ``sibling_merge_behavior`` to the exact
        ``TrackDescriptor.SIBLING_MERGE_BEHAVIOR_*`` enum. Supplying a merge key
        defaults the behavior to ``BY_SIBLING_MERGE_KEY``. Multiple backing
        lanes with the same parent and key can overlap while Perfetto presents
        them as one logical nested track.
        """
        if parent_uuid is None:
            parent_uuid = self.process_uuid
        if sibling_merge_behavior is not None and (
            isinstance(sibling_merge_behavior, bool)
            or sibling_merge_behavior not in range(4)
        ):
            raise ValueError("sibling_merge_behavior must be an official enum value")
        if isinstance(sibling_merge_key, bool):
            raise TypeError("sibling_merge_key must be a string or uint64")
        if sibling_merge_key is not None and not isinstance(
            sibling_merge_key, (str, int)
        ):
            raise TypeError("sibling_merge_key must be a string or uint64")
        if isinstance(sibling_merge_key, int) and not (
            0 <= sibling_merge_key <= 0xFFFF_FFFF_FFFF_FFFF
        ):
            raise ValueError("integer sibling_merge_key must fit in uint64")
        if sibling_merge_key is not None and sibling_merge_behavior is None:
            sibling_merge_behavior = (
                perfetto.TrackDescriptor.SIBLING_MERGE_BEHAVIOR_BY_SIBLING_MERGE_KEY
            )
        if sibling_merge_key is not None and sibling_merge_behavior != (
            perfetto.TrackDescriptor.SIBLING_MERGE_BEHAVIOR_BY_SIBLING_MERGE_KEY
        ):
            raise ValueError("sibling merge keys require BY_SIBLING_MERGE_KEY")

        track_uuid = self._next_uuid()
        descriptor = self.trace.packet.add().track_descriptor
        descriptor.uuid = track_uuid
        descriptor.parent_uuid = parent_uuid
        descriptor.name = name
        if sibling_merge_behavior is not None:
            descriptor.sibling_merge_behavior = sibling_merge_behavior
        if isinstance(sibling_merge_key, str):
            descriptor.sibling_merge_key = sibling_merge_key
        elif isinstance(sibling_merge_key, int):
            descriptor.sibling_merge_key_int = sibling_merge_key

        self.track_metadata[track_uuid] = {
            "type": "track",
            "name": name,
            "parent": parent_uuid,
            "sibling_merge_behavior": sibling_merge_behavior,
            "sibling_merge_key": sibling_merge_key,
        }
        return track_uuid

    def add_merged_track_lane(
        self,
        name: str,
        sibling_merge_key: Union[str, int],
        parent_uuid: Optional[int] = None,
    ) -> int:
        """Add one backing lane merged with eligible lanes sharing its key."""
        return self.add_track(
            name,
            parent_uuid,
            sibling_merge_key=sibling_merge_key,
        )

    def _add_track_event(
        self,
        track_uuid: int,
        timestamp: int,
        event_type: Optional[int],
        name: Optional[str] = None,
        *,
        timestamp_clock_id: Optional[int] = None,
    ):
        """Create a packet with a populated track event."""
        packet = self.trace.packet.add()
        packet.timestamp = timestamp
        if timestamp_clock_id is not None:
            packet.timestamp_clock_id = timestamp_clock_id
        if event_type is not None:
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

    def _wrap_track_event(self, packet) -> TrackEventWrapper:
        return TrackEventWrapper(
            packet.track_event,
            packet=packet,
            interning_state=self._interning_state,
            max_depth=self._annotation_max_depth,
        )

    def begin_slice(
        self,
        track_uuid: int,
        name: str,
        timestamp: int,
        *,
        categories: Sequence[str] = (),
        timestamp_clock_id: Optional[int] = None,
    ) -> TrackEventWrapper:
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
            timestamp_clock_id=timestamp_clock_id,
        )
        wrapper = self._wrap_track_event(event)
        wrapper.add_categories(*categories)
        return wrapper

    def end_slice(
        self,
        track_uuid: int,
        timestamp: int,
        *,
        timestamp_clock_id: Optional[int] = None,
    ) -> None:
        """
        End a duration slice event.

        Args:
            track_uuid: Track containing the slice
            timestamp: Timestamp in nanoseconds
        """
        self._add_track_event(
            track_uuid,
            timestamp,
            perfetto.TrackEvent.TYPE_SLICE_END,
            timestamp_clock_id=timestamp_clock_id,
        )

    def add_instant_event(
        self,
        track_uuid: int,
        name: str,
        timestamp: int,
        *,
        categories: Sequence[str] = (),
        timestamp_clock_id: Optional[int] = None,
    ) -> TrackEventWrapper:
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
            timestamp_clock_id=timestamp_clock_id,
        )
        wrapper = self._wrap_track_event(event)
        wrapper.add_categories(*categories)
        return wrapper

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

    def update_counter(
        self,
        track_uuid: int,
        value: float,
        timestamp: int,
        *,
        timestamp_clock_id: Optional[int] = None,
    ) -> TrackEventWrapper:
        """
        Update a counter value.

        Args:
            track_uuid: Counter track UUID
            value: New counter value
            timestamp: Timestamp in nanoseconds

        Returns:
            TrackEventWrapper for adding categories and annotations
        """
        event = self._add_track_event(
            track_uuid,
            timestamp,
            perfetto.TrackEvent.TYPE_COUNTER,
            timestamp_clock_id=timestamp_clock_id,
        )

        if isinstance(value, int):
            event.track_event.counter_value = value
        else:
            event.track_event.double_counter_value = value
        return self._wrap_track_event(event)

    def add_flow(
        self,
        track_uuid: int,
        name: str,
        timestamp: int,
        flow_id: int,
        terminating: bool = False,
        *,
        categories: Sequence[str] = (),
        timestamp_clock_id: Optional[int] = None,
    ) -> TrackEventWrapper:
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
        event = self.add_instant_event(
            track_uuid,
            name,
            timestamp,
            categories=categories,
            timestamp_clock_id=timestamp_clock_id,
        )

        if terminating:
            event.event.terminating_flow_ids.append(flow_id)
        else:
            event.event.flow_ids.append(flow_id)

        return event

    def add_legacy_event(
        self,
        track_uuid: int,
        name: str,
        timestamp: int,
        legacy: LegacyEvent,
        *,
        categories: Sequence[str] = (),
        timestamp_clock_id: Optional[int] = None,
    ) -> TrackEventWrapper:
        """Add an uncommon Chrome legacy phase without losing legacy fields."""
        packet = self._add_track_event(
            track_uuid,
            timestamp,
            None,
            name,
            timestamp_clock_id=timestamp_clock_id,
        )
        target = packet.track_event.legacy_event
        target.phase = legacy.phase_value()
        for name in (
            "duration_us",
            "thread_duration_us",
            "thread_instruction_delta",
            "id_scope",
            "use_async_tts",
            "bind_id",
            "bind_to_enclosing",
            "flow_direction",
            "instant_event_scope",
            "pid_override",
            "tid_override",
        ):
            value = getattr(legacy, name)
            if value is not None:
                setattr(target, name, value)
        if legacy.id is not None:
            setattr(target, f"{legacy.id_type}_id", legacy.id)
        wrapper = self._wrap_track_event(packet)
        wrapper.add_categories(*categories)
        return wrapper

    def set_default_timestamp_clock(self, clock_id: int) -> None:
        """Set the per-sequence default clock for future packet timestamps."""
        if not 0 <= clock_id <= 0xFFFF_FFFF:
            raise ValueError("clock_id must fit in uint32")
        packet = self.trace.packet.add()
        packet.trusted_packet_sequence_id = self.trusted_packet_sequence_id
        packet.trace_packet_defaults.timestamp_clock_id = clock_id
        self._default_timestamp_clock_id = clock_id

    def add_clock_snapshot(
        self,
        readings: Sequence[ClockReading],
        *,
        primary_trace_clock: Optional[int] = None,
    ) -> None:
        """Relate custom/relative producer clocks to builtin clock domains."""
        if not readings:
            raise ValueError("a clock snapshot requires at least one reading")
        if primary_trace_clock is not None and not 0 <= primary_trace_clock <= 63:
            raise ValueError("primary_trace_clock must be a builtin clock ID")
        packet = self.trace.packet.add()
        packet.trusted_packet_sequence_id = self.trusted_packet_sequence_id
        snapshot = packet.clock_snapshot
        if primary_trace_clock is not None:
            snapshot.primary_trace_clock = primary_trace_clock
        for reading in readings:
            if (
                primary_trace_clock == reading.clock_id
                and reading.unit_multiplier_ns is not None
            ):
                raise ValueError(
                    "unit_multiplier_ns is not supported on the primary trace clock"
                )
            clock = snapshot.clocks.add()
            clock.clock_id = reading.clock_id
            clock.timestamp = reading.timestamp
            if reading.is_incremental is not None:
                clock.is_incremental = reading.is_incremental
            if reading.unit_multiplier_ns is not None:
                clock.unit_multiplier_ns = reading.unit_multiplier_ns

    def _add_frame_timeline_event(self, timestamp: int):
        """Create a FrameTimelineEvent packet."""
        packet = self.trace.packet.add()
        packet.timestamp = timestamp
        packet.trusted_packet_sequence_id = self.trusted_packet_sequence_id
        return packet.frame_timeline_event

    def add_frame_timeline_expected_surface_start(
        self,
        timestamp: int,
        *,
        cookie: int,
        token: int,
        display_frame_token: int,
        pid: Optional[int] = None,
        layer_name: Optional[str] = None,
    ) -> None:
        """Add an ExpectedSurfaceFrameStart FrameTimelineEvent packet."""
        event = self._add_frame_timeline_event(timestamp)
        frame = event.expected_surface_frame_start
        frame.cookie = cookie
        frame.token = token
        frame.display_frame_token = display_frame_token
        frame.pid = self.pid if pid is None else pid
        if layer_name is not None:
            frame.layer_name = layer_name

    def add_frame_timeline_actual_surface_start(
        self,
        timestamp: int,
        *,
        cookie: int,
        token: int,
        display_frame_token: int,
        pid: Optional[int] = None,
        layer_name: Optional[str] = None,
        present_type: Optional[int] = None,
        on_time_finish: Optional[bool] = None,
        gpu_composition: Optional[bool] = None,
        jank_type: Optional[int] = None,
        prediction_type: Optional[int] = None,
        is_buffer: Optional[bool] = None,
        jank_severity_type: Optional[int] = None,
        present_delay_millis: Optional[float] = None,
        vsync_resynced_jitter_millis: Optional[float] = None,
        jank_severity_score: Optional[float] = None,
        jank_type_experimental: Optional[int] = None,
        present_type_experimental: Optional[int] = None,
        jank_debug_metadata: Optional[float] = None,
        latched_fence_state: Optional[int] = None,
        animation_time_millis: Optional[float] = None,
    ) -> None:
        """Add an ActualSurfaceFrameStart FrameTimelineEvent packet."""
        event = self._add_frame_timeline_event(timestamp)
        frame = event.actual_surface_frame_start
        frame.cookie = cookie
        frame.token = token
        frame.display_frame_token = display_frame_token
        frame.pid = self.pid if pid is None else pid
        if layer_name is not None:
            frame.layer_name = layer_name
        if present_type is not None:
            frame.present_type = present_type
        if on_time_finish is not None:
            frame.on_time_finish = on_time_finish
        if gpu_composition is not None:
            frame.gpu_composition = gpu_composition
        if jank_type is not None:
            frame.jank_type = jank_type
        if prediction_type is not None:
            frame.prediction_type = prediction_type
        if is_buffer is not None:
            frame.is_buffer = is_buffer
        if jank_severity_type is not None:
            frame.jank_severity_type = jank_severity_type
        if present_delay_millis is not None:
            frame.present_delay_millis = present_delay_millis
        if vsync_resynced_jitter_millis is not None:
            frame.vsync_resynced_jitter_millis = vsync_resynced_jitter_millis
        if jank_severity_score is not None:
            frame.jank_severity_score = jank_severity_score
        if jank_type_experimental is not None:
            frame.jank_type_experimental = jank_type_experimental
        if present_type_experimental is not None:
            frame.present_type_experimental = present_type_experimental
        if jank_debug_metadata is not None:
            frame.jank_debug_metadata = jank_debug_metadata
        if latched_fence_state is not None:
            frame.latched_fence_state = latched_fence_state
        if animation_time_millis is not None:
            frame.animation_time_millis = animation_time_millis

    def add_frame_timeline_expected_display_start(
        self,
        timestamp: int,
        *,
        cookie: int,
        token: int,
        pid: Optional[int] = None,
    ) -> None:
        """Add an ExpectedDisplayFrameStart FrameTimelineEvent packet."""
        event = self._add_frame_timeline_event(timestamp)
        frame = event.expected_display_frame_start
        frame.cookie = cookie
        frame.token = token
        frame.pid = self.pid if pid is None else pid

    def add_frame_timeline_actual_display_start(
        self,
        timestamp: int,
        *,
        cookie: int,
        token: int,
        pid: Optional[int] = None,
        present_type: Optional[int] = None,
        on_time_finish: Optional[bool] = None,
        gpu_composition: Optional[bool] = None,
        jank_type: Optional[int] = None,
        prediction_type: Optional[int] = None,
        jank_severity_type: Optional[int] = None,
        present_delay_millis: Optional[float] = None,
        jank_severity_score: Optional[float] = None,
        jank_type_experimental: Optional[int] = None,
        present_type_experimental: Optional[int] = None,
        jank_debug_metadata: Optional[float] = None,
        latched_unsignaled_count: Optional[int] = None,
        addressable_unsignaled_latch_count: Optional[int] = None,
    ) -> None:
        """Add an ActualDisplayFrameStart FrameTimelineEvent packet."""
        event = self._add_frame_timeline_event(timestamp)
        frame = event.actual_display_frame_start
        frame.cookie = cookie
        frame.token = token
        frame.pid = self.pid if pid is None else pid
        if present_type is not None:
            frame.present_type = present_type
        if on_time_finish is not None:
            frame.on_time_finish = on_time_finish
        if gpu_composition is not None:
            frame.gpu_composition = gpu_composition
        if jank_type is not None:
            frame.jank_type = jank_type
        if prediction_type is not None:
            frame.prediction_type = prediction_type
        if jank_severity_type is not None:
            frame.jank_severity_type = jank_severity_type
        if present_delay_millis is not None:
            frame.present_delay_millis = present_delay_millis
        if jank_severity_score is not None:
            frame.jank_severity_score = jank_severity_score
        if jank_type_experimental is not None:
            frame.jank_type_experimental = jank_type_experimental
        if present_type_experimental is not None:
            frame.present_type_experimental = present_type_experimental
        if jank_debug_metadata is not None:
            frame.jank_debug_metadata = jank_debug_metadata
        if latched_unsignaled_count is not None:
            frame.latched_unsignaled_count = latched_unsignaled_count
        if addressable_unsignaled_latch_count is not None:
            frame.addressable_unsignaled_latch_count = (
                addressable_unsignaled_latch_count
            )

    def end_frame_timeline(self, timestamp: int, cookie: int) -> None:
        """Add a FrameTimelineEvent FrameEnd packet."""
        event = self._add_frame_timeline_event(timestamp)
        event.frame_end.cookie = cookie

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
