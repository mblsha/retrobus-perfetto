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
    trace_packet_defaults: Optional[TracePacketDefaults]
    track_descriptor: Optional[TrackDescriptor]
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