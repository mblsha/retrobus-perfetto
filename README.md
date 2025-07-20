# retrobus-perfetto

A minimal Perfetto trace generation library for retrocomputer emulators. This package provides a clean, CPU-independent API for creating detailed execution traces that can be visualized in the Perfetto UI.

## Features

- **Simple Builder API**: Medium-level abstraction over Perfetto's protobuf format
- **CPU-Independent**: Designed to work with any retrocomputer architecture
- **Rich Annotations**: Support for debug data, register states, and custom metadata
- **Multiple Track Types**: Threads, counters, and flow events
- **Direct Protobuf**: Uses protobuf directly for maximum control (with plans to support official SDK)

## Installation

```bash
# Install from source
pip install -e .

# For development (includes protoc tools)
pip install -e ".[dev]"
```

## Quick Start

```python
from retrobus_perfetto import PerfettoTraceBuilder

# Create a trace builder
builder = PerfettoTraceBuilder("My Emulator")

# Add threads for different components
cpu_thread = builder.add_thread("CPU")
io_thread = builder.add_thread("I/O")

# Record a function call
event = builder.begin_slice(cpu_thread, "execute_instruction", timestamp=1000)
event.add_annotations({
    "pc": 0x1234,
    "opcode": 0xCD,
    "mnemonic": "CALL"
})
builder.end_slice(cpu_thread, timestamp=2000)

# Record an I/O operation
io_event = builder.add_instant_event(io_thread, "Port Write", timestamp=1500)
io_event.add_annotations({
    "port": 0x10,
    "value": 0xFF
})

# Save the trace
builder.save("trace.perfetto-trace")
```

## Advanced Usage

### Counter Tracks

Track metrics over time:

```python
# Create a counter track
memory_track = builder.add_counter_track("Memory Usage", "KB")

# Update values
builder.update_counter(memory_track, 1024, timestamp=1000)
builder.update_counter(memory_track, 1536, timestamp=2000)
```

### Flow Events

Connect related events across threads:

```python
flow_id = 12345

# Start flow on one thread
event1 = builder.add_flow(thread1, "Send Request", timestamp=1000, flow_id=flow_id)

# Continue on another thread
event2 = builder.add_flow(thread2, "Process Request", timestamp=2000, flow_id=flow_id)

# Terminate the flow
event3 = builder.add_flow(thread3, "Complete", timestamp=3000, 
                         flow_id=flow_id, terminating=True)
```

### Detailed Annotations

```python
# Use annotation builder for structured data
event = builder.begin_slice(cpu_thread, "function_call", timestamp=1000)

# Add grouped annotations
with event.annotation("registers") as ann:
    ann.pointer("PC", 0x1234)
    ann.int("A", 42)
    ann.int("B", 0)
    ann.pointer("SP", 0x7FFE)

with event.annotation("flags") as ann:
    ann.bool("zero", True)
    ann.bool("carry", False)
    ann.bool("interrupt", True)

builder.end_slice(cpu_thread, timestamp=2000)
```

## Example: Tracing a CPU Emulator

```python
class EmulatorTracer:
    def __init__(self):
        self.builder = PerfettoTraceBuilder("Z80 Emulator")
        self.cpu_thread = self.builder.add_thread("CPU")
        self.timestamp = 0
    
    def trace_instruction(self, pc, opcode, registers):
        # Each instruction takes 4 cycles (example)
        duration = 4 * 1000  # Convert to nanoseconds
        
        event = self.builder.begin_slice(
            self.cpu_thread, 
            f"Instruction_{hex(opcode)}", 
            self.timestamp
        )
        
        event.add_annotations({
            "pc": pc,
            "opcode": opcode,
            "sp": registers.sp,
            "a": registers.a,
            "bc": registers.bc
        })
        
        self.timestamp += duration
        self.builder.end_slice(self.cpu_thread, self.timestamp)
    
    def save_trace(self, filename):
        self.builder.save(filename)
```

## Viewing Traces

Generated traces can be viewed at [ui.perfetto.dev](https://ui.perfetto.dev):

1. Open the Perfetto UI
2. Click "Open trace file" 
3. Select your `.perfetto-trace` file

## Future Plans

This package currently uses direct protobuf generation for maximum control and compatibility. Future versions may migrate to the official Perfetto Python SDK while maintaining backward compatibility with the current API.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details.