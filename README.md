# retrobus-perfetto

A minimal Perfetto trace generation library for retrocomputer emulators. This project provides clean, CPU-independent APIs for creating detailed execution traces that can be visualized in the Perfetto UI.

## Project Structure

This is a multi-language project with implementations in different languages:

- `py/` - Python implementation
- `cpp/` - C++ header-only implementation
- `ts/` - TypeScript protobuf bindings (Node/TS)
- `proto/` - Shared protocol buffer definitions
- `tools/` - Analysis tools for Perfetto traces

## Features

- **Simple Builder API**: Medium-level abstraction over Perfetto's protobuf format
- **CPU-Independent**: Designed to work with any retrocomputer architecture
- **Rich Annotations**: Support for debug data, register states, and custom metadata
- **Multiple Track Types**: Threads, counters, and flow events
- **String Interning (default)**: Smaller traces via `TracePacket.interned_data` dictionaries
- **Direct Protobuf**: Uses protobuf directly for maximum control

## Python Installation

```bash
cd py/

# Install from source
pip install .

# For development (includes protoc tools)
pip install -e ".[dev]"
```

## Quick Start (Python)

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

### Interned encoding (Python)

Interning is the default encoding and keeps your public API string-based (users still pass strings; traces store IDs + dictionaries). Opt out with `encoding="inline"`:

```python
from retrobus_perfetto import PerfettoTraceBuilder, resolve_interned_trace
from retrobus_perfetto.proto import perfetto_pb2

builder = PerfettoTraceBuilder("My Emulator")  # default: interned
# builder = PerfettoTraceBuilder("My Emulator", encoding="inline")  # opt out
# ... emit events ...

# Optional: make interned traces readable for string-based tooling
trace = perfetto_pb2.Trace()
trace.ParseFromString(builder.serialize())
resolved = resolve_interned_trace(trace, inplace=False)
```

### Interned encoding (C++)

```cpp
#include <retrobus/retrobus_perfetto.hpp>

retrobus::PerfettoTraceBuilder builder("My Emulator");  // default: interned
// retrobus::PerfettoTraceBuilder builder(
//     "My Emulator",
//     /*pid=*/1234,
//     retrobus::PerfettoTraceBuilder::Encoding::Inline);  // opt out
```

## Documentation

- [Python Implementation](py/README.md)
- [C++ Design Document](cpp-header-only-design.md)
- [TypeScript Protobuf Bindings](ts/README.md)
- [Protocol Buffer Definitions](proto/README.md)
- [Trace Analysis Tools](tools/README.md)

## Viewing Traces

Generated traces can be viewed at [ui.perfetto.dev](https://ui.perfetto.dev):

1. Open the Perfetto UI
2. Click "Open trace file" 
3. Select your `.perfetto-trace` file

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details.
