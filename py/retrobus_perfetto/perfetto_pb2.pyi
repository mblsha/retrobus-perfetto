# Type stubs for generated perfetto_pb2 module
from typing import Optional
from google.protobuf import message
from google.protobuf.internal.containers import RepeatedCompositeFieldContainer, RepeatedScalarFieldContainer

class Trace(message.Message):
    @property
    def packet(self) -> RepeatedCompositeFieldContainer[TracePacket]: ...
    def __init__(self) -> None: ...

class TracePacket(message.Message):
    timestamp: int
    track_event: Optional[TrackEvent]
    frame_timeline_event: Optional[FrameTimelineEvent]
    trace_packet_defaults: Optional[TracePacketDefaults]
    track_descriptor: Optional[TrackDescriptor]
    def __init__(self) -> None: ...

class FrameTimelineEvent(message.Message):
    class ExpectedSurfaceFrameStart(message.Message):
        cookie: int
        token: int
        display_frame_token: int
        pid: int
        layer_name: str
        def __init__(self) -> None: ...

    class ActualSurfaceFrameStart(message.Message):
        LATCHED_UNKNOWN: int = 0
        LATCHED_SIGNALED: int = 1
        LATCHED_UNSIGNALED: int = 2
        LATCHED_DELAYED_LATCH_UNSIGNALED: int = 3

        cookie: int
        token: int
        display_frame_token: int
        pid: int
        layer_name: str
        present_type: int
        on_time_finish: bool
        gpu_composition: bool
        jank_type: int
        prediction_type: int
        is_buffer: bool
        jank_severity_type: int
        present_delay_millis: float
        vsync_resynced_jitter_millis: float
        jank_severity_score: float
        jank_type_experimental: int
        present_type_experimental: int
        jank_debug_metadata: float
        latched_fence_state: int
        animation_time_millis: float
        def __init__(self) -> None: ...

    class ExpectedDisplayFrameStart(message.Message):
        cookie: int
        token: int
        pid: int
        def __init__(self) -> None: ...

    class ActualDisplayFrameStart(message.Message):
        cookie: int
        token: int
        pid: int
        present_type: int
        on_time_finish: bool
        gpu_composition: bool
        jank_type: int
        prediction_type: int
        jank_severity_type: int
        present_delay_millis: float
        jank_severity_score: float
        jank_type_experimental: int
        present_type_experimental: int
        jank_debug_metadata: float
        latched_unsignaled_count: int
        addressable_unsignaled_latch_count: int
        def __init__(self) -> None: ...

    class FrameEnd(message.Message):
        cookie: int
        def __init__(self) -> None: ...

    JANK_UNSPECIFIED: int = 0
    JANK_NONE: int = 1
    JANK_SF_SCHEDULING: int = 2
    JANK_PREDICTION_ERROR: int = 4
    JANK_DISPLAY_HAL: int = 8
    JANK_SF_CPU_DEADLINE_MISSED: int = 16
    JANK_SF_GPU_DEADLINE_MISSED: int = 32
    JANK_APP_DEADLINE_MISSED: int = 64
    JANK_BUFFER_STUFFING: int = 128
    JANK_UNKNOWN: int = 256
    JANK_SF_STUFFING: int = 512
    JANK_DROPPED: int = 1024
    JANK_NON_ANIMATING: int = 2048
    JANK_APP_RESYNCED_JITTER: int = 4096
    JANK_DISPLAY_NOT_ON: int = 8192
    JANK_DISPLAY_MODE_CHANGE_IN_PROGRESS: int = 16384
    JANK_DISPLAY_POWER_MODE_CHANGE_IN_PROGRESS: int = 32768

    SEVERITY_UNKNOWN: int = 0
    SEVERITY_NONE: int = 1
    SEVERITY_PARTIAL: int = 2
    SEVERITY_FULL: int = 3

    PRESENT_UNSPECIFIED: int = 0
    PRESENT_ON_TIME: int = 1
    PRESENT_LATE: int = 2
    PRESENT_EARLY: int = 3
    PRESENT_DROPPED: int = 4
    PRESENT_UNKNOWN: int = 5

    PREDICTION_UNSPECIFIED: int = 0
    PREDICTION_VALID: int = 1
    PREDICTION_EXPIRED: int = 2
    PREDICTION_UNKNOWN: int = 3

    @property
    def expected_surface_frame_start(self) -> FrameTimelineEvent.ExpectedSurfaceFrameStart: ...
    @property
    def actual_surface_frame_start(self) -> FrameTimelineEvent.ActualSurfaceFrameStart: ...
    @property
    def expected_display_frame_start(self) -> FrameTimelineEvent.ExpectedDisplayFrameStart: ...
    @property
    def actual_display_frame_start(self) -> FrameTimelineEvent.ActualDisplayFrameStart: ...
    @property
    def frame_end(self) -> FrameTimelineEvent.FrameEnd: ...
    def __init__(self) -> None: ...

class ExpectedSurfaceFrameStart(message.Message):
    cookie: int
    token: int
    display_frame_token: int
    pid: int
    layer_name: str
    def __init__(self) -> None: ...

class ActualSurfaceFrameStart(message.Message):
    LATCHED_UNKNOWN: int = 0
    LATCHED_SIGNALED: int = 1
    LATCHED_UNSIGNALED: int = 2
    LATCHED_DELAYED_LATCH_UNSIGNALED: int = 3

    cookie: int
    token: int
    display_frame_token: int
    pid: int
    layer_name: str
    present_type: int
    on_time_finish: bool
    gpu_composition: bool
    jank_type: int
    prediction_type: int
    is_buffer: bool
    jank_severity_type: int
    present_delay_millis: float
    vsync_resynced_jitter_millis: float
    jank_severity_score: float
    jank_type_experimental: int
    present_type_experimental: int
    jank_debug_metadata: float
    latched_fence_state: int
    animation_time_millis: float
    def __init__(self) -> None: ...

class ExpectedDisplayFrameStart(message.Message):
    cookie: int
    token: int
    pid: int
    def __init__(self) -> None: ...

class ActualDisplayFrameStart(message.Message):
    cookie: int
    token: int
    pid: int
    present_type: int
    on_time_finish: bool
    gpu_composition: bool
    jank_type: int
    prediction_type: int
    jank_severity_type: int
    present_delay_millis: float
    jank_severity_score: float
    jank_type_experimental: int
    present_type_experimental: int
    jank_debug_metadata: float
    latched_unsignaled_count: int
    addressable_unsignaled_latch_count: int
    def __init__(self) -> None: ...

class FrameEnd(message.Message):
    cookie: int
    def __init__(self) -> None: ...

class TrackEvent(message.Message):
    TYPE_SLICE_BEGIN: int = 1
    TYPE_SLICE_END: int = 2
    TYPE_INSTANT: int = 3
    TYPE_COUNTER: int = 4
    
    track_uuid: int
    @property
    def categories(self) -> RepeatedScalarFieldContainer[str]: ...
    name: str
    type: int
    @property
    def flow_ids(self) -> RepeatedScalarFieldContainer[int]: ...
    @property
    def terminating_flow_ids(self) -> RepeatedScalarFieldContainer[int]: ...
    @property
    def debug_annotations(self) -> RepeatedCompositeFieldContainer[DebugAnnotation]: ...
    counter_value: Optional[int]
    double_counter_value: Optional[float]
    def __init__(self) -> None: ...

class TracePacketDefaults(message.Message):
    timestamp_clock_id: int
    track_event_defaults: Optional[TrackEventDefaults]
    def __init__(self) -> None: ...

class TrackEventDefaults(message.Message):
    track_uuid: int
    def __init__(self) -> None: ...

class TrackDescriptor(message.Message):
    uuid: int
    name: str
    @property
    def process(self) -> ProcessDescriptor: ...
    @property
    def thread(self) -> ThreadDescriptor: ...
    @property
    def counter(self) -> CounterDescriptor: ...
    def __init__(self) -> None: ...

class ProcessDescriptor(message.Message):
    pid: int
    process_name: str
    def __init__(self) -> None: ...

class ThreadDescriptor(message.Message):
    pid: int
    tid: int
    thread_name: str
    def __init__(self) -> None: ...

class CounterDescriptor(message.Message):
    @property
    def categories(self) -> RepeatedScalarFieldContainer[str]: ...
    unit_name: str
    def __init__(self) -> None: ...

class DebugAnnotation(message.Message):
    name: str
    int_value: Optional[int]
    bool_value: Optional[bool]
    double_value: Optional[float]
    string_value: Optional[str]
    @property
    def nested_value(self) -> NestedValue: ...
    def __init__(self) -> None: ...

class NestedValue(message.Message):
    DICT: int = 2
    
    nested_type: int
    @property
    def dict_entries(self) -> RepeatedCompositeFieldContainer[DictEntry]: ...
    def __init__(self) -> None: ...

class DictEntry(message.Message):
    key: str
    @property
    def value(self) -> DebugAnnotation: ...
    def __init__(self) -> None: ...

class BuiltinClock:
    BUILTIN_CLOCK_BOOTTIME: int = 6
