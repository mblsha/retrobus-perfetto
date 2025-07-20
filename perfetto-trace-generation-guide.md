# Perfetto Trace Generation Guide

## Overview

Perfetto is a powerful system-wide tracing framework that enables detailed performance analysis and debugging. This guide explains how to generate Perfetto traces programmatically, focusing on the protocol buffer definitions and practical implementation patterns.

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Protocol Buffer Structure](#protocol-buffer-structure)
3. [Implementation Guide](#implementation-guide)
4. [Advanced Features](#advanced-features)
5. [Best Practices](#best-practices)
6. [Use Cases](#use-cases)

## Core Concepts

### What is Perfetto?

Perfetto provides a binary trace format based on Protocol Buffers that captures:
- **Temporal Events**: Function calls, operations with duration
- **Instant Events**: Point-in-time occurrences
- **State Information**: CPU registers, memory values, I/O operations
- **Relationships**: Call stacks, async operations, data flow

### Key Components

1. **Trace**: Container for all trace data
2. **TracePacket**: Individual timestamped data points
3. **Track**: Logical timeline (process, thread, or custom)
4. **TrackEvent**: Events occurring on a track
5. **Annotations**: Additional metadata and debug information

## Protocol Buffer Structure

### Root Structure

```protobuf
Trace {
    repeated TracePacket packets
}
```

### TracePacket Definition

```protobuf
TracePacket {
    uint64 timestamp                    // Nanoseconds by default
    uint32 timestamp_clock_id           // Clock source identifier
    oneof data {
        TrackEvent track_event          // Event data
        TrackDescriptor track_descriptor // Track metadata
    }
}
```

### TrackDescriptor Components

```protobuf
TrackDescriptor {
    uint64 uuid                         // Unique track identifier
    uint64 parent_uuid                  // Parent track (for hierarchy)
    string name                         // Display name
    ProcessDescriptor process           // Process information
    ThreadDescriptor thread             // Thread information
}
```

### TrackEvent Types

```protobuf
TrackEvent {
    Type type                           // Event type
    uint64 track_uuid                   // Associated track
    string name                         // Event name
    repeated DebugAnnotation debug_annotations
}

enum Type {
    TYPE_SLICE_BEGIN = 1               // Start of duration event
    TYPE_SLICE_END = 2                 // End of duration event
    TYPE_INSTANT = 3                   // Point-in-time event
    TYPE_COUNTER = 4                   // Metric value update
}
```

## Implementation Guide

### 1. Initialize Trace Builder

```python
class PerfettoTraceBuilder:
    def __init__(self, process_name):
        self.trace = Trace()
        self.current_timestamp = 0
        self.track_uuids = {}
        
        # Create root process
        self.process_uuid = self.create_process(process_name)
```

### 2. Create Process and Thread Tracks

```python
def create_process(self, name):
    packet = TracePacket()
    track_uuid = generate_uuid()
    
    packet.track_descriptor = TrackDescriptor(
        uuid=track_uuid,
        process=ProcessDescriptor(
            pid=os.getpid(),
            process_name=name
        )
    )
    self.trace.packets.append(packet)
    return track_uuid

def create_thread(self, process_uuid, thread_name):
    packet = TracePacket()
    thread_uuid = generate_uuid()
    
    packet.track_descriptor = TrackDescriptor(
        uuid=thread_uuid,
        parent_uuid=process_uuid,
        thread=ThreadDescriptor(
            pid=os.getpid(),
            tid=threading.get_ident(),
            thread_name=thread_name
        )
    )
    self.trace.packets.append(packet)
    return thread_uuid
```

### 3. Record Duration Events (Slices)

```python
def begin_slice(self, thread_uuid, name, timestamp):
    packet = TracePacket()
    packet.timestamp = timestamp
    packet.track_event = TrackEvent(
        type=TYPE_SLICE_BEGIN,
        track_uuid=thread_uuid,
        name=name
    )
    self.trace.packets.append(packet)
    return packet.track_event

def end_slice(self, thread_uuid, timestamp):
    packet = TracePacket()
    packet.timestamp = timestamp
    packet.track_event = TrackEvent(
        type=TYPE_SLICE_END,
        track_uuid=thread_uuid
    )
    self.trace.packets.append(packet)
```

### 4. Add Instant Events

```python
def add_instant_event(self, thread_uuid, name, timestamp):
    packet = TracePacket()
    packet.timestamp = timestamp
    packet.track_event = TrackEvent(
        type=TYPE_INSTANT,
        track_uuid=thread_uuid,
        name=name
    )
    self.trace.packets.append(packet)
    return packet.track_event
```

### 5. Enrich with Debug Annotations

```python
def add_annotations(self, track_event, data):
    for key, value in data.items():
        annotation = DebugAnnotation(name=key)
        
        if isinstance(value, int):
            annotation.int_value = value
        elif isinstance(value, float):
            annotation.double_value = value
        elif isinstance(value, str):
            annotation.string_value = value
        elif isinstance(value, bool):
            annotation.bool_value = value
        
        track_event.debug_annotations.append(annotation)
```

## Advanced Features

### Flow Events

Connect related events across threads to visualize async operations:

```python
def trace_async_flow(self, flow_id):
    # Origin
    event1 = self.begin_slice(thread1, "Send Request", time1)
    event1.flow_ids.append(flow_id)
    
    # Intermediate
    event2 = self.begin_slice(thread2, "Process", time2)
    event2.flow_ids.append(flow_id)
    
    # Termination
    event3 = self.add_instant_event(thread3, "Complete", time3)
    event3.terminating_flow_ids.append(flow_id)
```

### Counter Tracks

Track metrics over time:

```python
def create_counter_track(self, name, unit):
    counter_uuid = generate_uuid()
    packet = TracePacket()
    packet.track_descriptor = TrackDescriptor(
        uuid=counter_uuid,
        parent_uuid=self.process_uuid,
        name=f"{name} ({unit})"
    )
    self.trace.packets.append(packet)
    return counter_uuid

def update_counter(self, counter_uuid, value, timestamp):
    packet = TracePacket()
    packet.timestamp = timestamp
    packet.track_event = TrackEvent(
        type=TYPE_COUNTER,
        track_uuid=counter_uuid,
        counter_value=value
    )
    self.trace.packets.append(packet)
```

### Nested Annotations

For complex data structures:

```python
def add_dict_annotation(self, track_event, name, dict_data):
    annotation = DebugAnnotation(name=name)
    
    for key, value in dict_data.items():
        entry = DebugAnnotation(
            name=key,
            int_value=value  # or appropriate type
        )
        annotation.dict_entries.append(entry)
    
    track_event.debug_annotations.append(annotation)
```

## Best Practices

### 1. Timestamp Management

- Use monotonic clocks for relative timestamps
- Specify clock domain explicitly
- Maintain timestamp ordering within tracks

### 2. Track Organization

- Create logical thread groupings
- Use parent_uuid for hierarchical organization
- Name tracks descriptively

### 3. Event Granularity

- Balance detail vs. trace size
- Focus on significant operations
- Use instant events for lightweight markers

### 4. Annotation Strategy

- Include relevant context (addresses, values, states)
- Avoid redundant information
- Use structured data for complex annotations

### 5. Memory Efficiency

- Batch packet creation
- Reuse track UUIDs
- Limit string duplication

## Use Cases

### 1. CPU Emulator Tracing

```python
# Track instruction execution
event = builder.begin_slice(cpu_thread, "execute_instruction", timestamp)
builder.add_annotations(event, {
    "pc": program_counter,
    "opcode": instruction_opcode,
    "bank": memory_bank
})
```

### 2. Function Call Profiling

```python
# Track call stack
event = builder.begin_slice(main_thread, function_name, timestamp)
builder.add_dict_annotation(event, "registers", {
    "SP": stack_pointer,
    "return_addr": return_address
})
```

### 3. I/O Operation Monitoring

```python
# Log port operations
event = builder.add_instant_event(io_thread, f"Port {port} OUT", timestamp)
builder.add_annotations(event, {
    "port": port_number,
    "value": output_value
})
```

### 4. Performance Metrics

```python
# Track memory usage
memory_track = builder.create_counter_track("Memory Usage", "MB")
builder.update_counter(memory_track, current_memory_mb, timestamp)
```

## Serialization and Output

```python
# Serialize to binary format
def save_trace(self, filename):
    binary_data = self.trace.SerializeToString()
    with open(filename, 'wb') as f:
        f.write(binary_data)
```

## Visualization

Generated traces can be viewed at [ui.perfetto.dev](https://ui.perfetto.dev) by:
1. Opening the web interface
2. Clicking "Open trace file"
3. Selecting your `.perfetto-trace` file

## Conclusion

Perfetto's flexible protocol buffer format enables detailed system tracing with minimal overhead. By following these patterns, you can create rich traces that provide deep insights into system behavior, performance characteristics, and execution flow.

The key to effective tracing is choosing appropriate granularity and including relevant context without overwhelming the trace with unnecessary detail. Start with high-level events and progressively add detail where needed for your specific debugging or analysis requirements.