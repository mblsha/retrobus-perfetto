# retrobus-perfetto

A producer-neutral Perfetto trace generation and reconstruction library for
retrocomputer emulators and resource-constrained systems. It provides clean,
CPU-independent host APIs plus an allocation-free target flight recorder.

## Project Structure

This is a multi-language project with implementations in different languages:

- `py/` - Python implementation
- `cpp/` - C++ header-only implementation
- `compact/` - Allocation-free C recorder, C++ RAII wrapper, and `.rbct` format
- `ts/` - TypeScript protobuf bindings (Node/TS, run `npm run gen:proto` in `ts/` to generate)
- `proto/` - Shared protocol buffer definitions
- `tools/` - Analysis tools for Perfetto traces

## Features

- **Simple Builder API**: Medium-level abstraction over Perfetto's protobuf format
- **CPU-Independent**: Designed to work with any retrocomputer architecture
- **Rich Annotations**: Support for debug data, register states, and custom metadata
- **Multiple Track Types**: Threads, counters, and flow events
- **String Interning (default)**: Smaller traces via `TracePacket.interned_data` dictionaries
- **Direct Protobuf**: Uses protobuf directly for maximum control
- **Target Flight Recorder**: Numeric, schema-driven ring records with no
  protobuf, heap allocation, syscall, lock, or event-path I/O
- **Clock Correlation**: Raw wrapping counters, clock generations, and bounded
  host-reference snapshots reconstruct into nanosecond Perfetto timelines
- **Streaming Oracle Indexing**: Query large traces through SQLite without
  whole-trace `ParseFromString`

## Python Installation

```bash
cd py/

# Install from source
pip install .

# For development (includes protoc tools)
pip install -e ".[dev]"
```

## Compact target traces

Small or timing-sensitive targets can record `.rbct` rather than native
protobuf. The producer keeps its event schema; this repository supplies the
format, target writer, validation, conversion, and collision-safe trace merge.

```sh
python tools/compact_schema_header.py producer-schema.json generated/schema.h \
    --prefix example
python tools/compact_trace_to_perfetto.py capture.rbct capture.perfetto-trace \
  --schema producer-schema.json
python tools/compact_trace_profile.py capture.rbct --schema producer-schema.json \
  --output density.json
python tools/merge_perfetto_sources.py capture.perfetto-trace kernel.perfetto-trace \
  --output combined.perfetto-trace
```

The generated header provides schema-safe inline begin/emit functions and dense
v3 semantic commit opcodes. Names and protobuf expansion happen only on the
host. See [`compact/FORMAT.md`](compact/FORMAT.md) for the compatibility
contract, [`compact/README.md`](compact/README.md) for the C/C++ API, and
[`compact/V3_DENSITY_AUDIT.md`](compact/V3_DENSITY_AUDIT.md) for the density and
recovery audit.

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
// C++ API always emits interned string fields.

// Optional: resolve IID-backed names to inline strings for
// string-based debugging/diff tooling.
perfetto::protos::Trace trace;
trace.ParseFromString(builder.serialize());
auto resolved = retrobus::resolve_interned_trace(trace); // returns a copy
retrobus::resolve_interned_trace_inplace(trace);         // mutates in-place
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

## Streaming Oracle Index

For large parity captures, stream one or more trace files into a SQLite index
instead of loading the entire `.perfetto-trace` into a single protobuf object:

```bash
python tools/perfetto_trace_oracle.py index trace.perfetto-trace \
  --index trace.sqlite \
  --verify
```

The `verify` pass also materializes `oracle_invocations`, a compact
invocation-oriented export with function name/address, callsite, frame/VSync,
temporal sequence, entry registers, real-exit registers/`eflags`/`eip`, and
provenance JSON. Producer `trace_provenance` annotations are embedded in that
JSON so compact rows retain executable, manifest, symbol-map, and producer
identity. Split trace chunks are supported by passing multiple input files in
capture order. The output is published atomically, and the command refuses to
use a trace source itself as the SQLite output path.

Only slices tagged as call lifecycle events participate in invocation
verification. Untagged traces remain compatible when calls use the canonical
`Function execution` track; duration slices on Files, VSync, rendering, or
other tracks stay queryable as raw events without becoming function calls.

Opaque protobuf `uint64` identifiers such as track UUIDs and call IDs are stored
as decimal text so their full range is preserved. Address and counter columns
use SQLite integers; unsigned values above `INT64_MAX` retain their bit pattern
using signed two's-complement representation, as recorded in the `metadata`
table.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details.
