"""Tests for render-oriented trace preparation."""

import pytest

from retrobus_perfetto import PerfettoTraceBuilder, resolve_interned_trace
from retrobus_perfetto.proto import perfetto_pb2
from retrobus_perfetto.trace_prepare import (
    SYNTHETIC_SPAN_EVENT_NAME,
    SYNTHETIC_SPAN_TRACK_NAME,
    prepare_trace_for_render,
)


def _sample_trace():
    builder = PerfettoTraceBuilder("TestProcess", encoding="interned")
    functions = builder.add_thread("Functions")
    syscalls = builder.add_thread("Syscalls")
    builder.add_instant_event(functions, "enter", 100)
    builder.add_instant_event(syscalls, "interrupt", 250)

    trace = perfetto_pb2.Trace()
    trace.ParseFromString(builder.serialize())
    resolve_interned_trace(trace, inplace=True)
    return trace


def test_prepare_trace_normalizes_and_adds_full_span() -> None:
    trace = _sample_trace()

    bounds = prepare_trace_for_render(trace, perfetto_pb2)

    assert bounds.source_start_ns == 100
    assert bounds.duration_ns == 150

    descriptors = [
        packet.track_descriptor
        for packet in trace.packet
        if packet.HasField("track_descriptor")
    ]
    synthetic = [
        descriptor
        for descriptor in descriptors
        if descriptor.thread.thread_name == SYNTHETIC_SPAN_TRACK_NAME
    ]
    assert len(synthetic) == 1

    synthetic_uuid = synthetic[0].uuid
    synthetic_events = [
        packet
        for packet in trace.packet
        if packet.HasField("track_event")
        and packet.track_event.track_uuid == synthetic_uuid
    ]
    assert [packet.timestamp for packet in synthetic_events] == [0, 150]
    assert synthetic_events[0].track_event.name == SYNTHETIC_SPAN_EVENT_NAME

    real_timestamps = [
        packet.timestamp
        for packet in trace.packet
        if packet.HasField("track_event")
        and packet.track_event.track_uuid != synthetic_uuid
    ]
    assert real_timestamps == [0, 150]


def test_prepare_trace_replaces_existing_synthetic_span() -> None:
    trace = _sample_trace()
    prepare_trace_for_render(trace, perfetto_pb2)

    bounds = prepare_trace_for_render(
        trace,
        perfetto_pb2,
        normalize_start=False,
    )

    assert bounds.source_start_ns == 0
    assert bounds.duration_ns == 150
    synthetic_descriptors = [
        packet
        for packet in trace.packet
        if packet.HasField("track_descriptor")
        and packet.track_descriptor.thread.thread_name == SYNTHETIC_SPAN_TRACK_NAME
    ]
    assert len(synthetic_descriptors) == 1


def test_prepare_trace_rejects_trace_without_events() -> None:
    with pytest.raises(ValueError, match="no timestamped track events"):
        prepare_trace_for_render(perfetto_pb2.Trace(), perfetto_pb2)
