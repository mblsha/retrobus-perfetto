# retrobus-perfetto Python Implementation

This directory contains the Python implementation of retrobus-perfetto.

## Installation

From the `py/` directory:

```bash
# For development
pip install -e ".[dev]"

# For regular use
pip install .

# From PyPI (once published)
pip install retrobus-perfetto
```

## Development

### Running Tests
```bash
pytest
```

### Running Linter
```bash
ruff check .
```

### Running Type Checker
```bash
mypy retrobus_perfetto --config-file mypy.ini
```

### Building Package
```bash
python -m build
```

## Usage

### Basic Usage

```python
from retrobus_perfetto import PerfettoTraceBuilder

# Create a trace
builder = PerfettoTraceBuilder("MyEmulator")
# ... add events ...
trace_data = builder.serialize()
```

### High-fidelity profiling data

The builder can intern event categories and source/callstack tables, encode
recursive dictionaries and arrays without stringification, create backing lanes
that Perfetto merges into one logical track, preserve uncommon Chrome legacy
payloads, and correlate producer clocks with builtin clocks. See the
[Perfetto fidelity guide](../perfetto-fidelity-guide.md) for APIs, examples,
incremental-state behavior, and the caller-owned path/address redaction policy.

### Compact target captures

```python
from retrobus_perfetto import (
    CompactCodecProfile,
    CompactSchema,
    convert_compact_trace,
    profile_compact_trace,
)

schema = CompactSchema.load("producer-schema.json")
codec = CompactCodecProfile.load("producer-codec.json", schema)
summary = convert_compact_trace(
    "capture.rbct",
    schema,
    "capture.perfetto-trace",
    codec_profile=codec,
)
density = profile_compact_trace("capture.rbct", schema, codec_profile=codec)
```

`CompactTraceReader.iter_items()` validates and yields one bounded chunk at a
time. `read_compact_trace()` collects a complete decoded model when host memory
is not constrained and pre-indexes clock generations and correlation anchors
for efficient timestamp conversion. Both entry points require the exact
external producer schema identified by the capture header. Unfinalized reads
are explicitly best-effort and report retained, successfully decoded records.
Profiled v4 captures additionally require the exact external codec profile
whose SHA-256 is stored in the capture header; literal-only v4 and v1/v2/v3 do
not. `profile_compact_trace()` replays logical records through v1/v2/v3/v4 and
reports byte/bit attribution, density, varint widths, profile hits, and chunk
use.
`CompactTrace.uncorrelated_generations` identifies relative-only generations,
including a wrapped prefix whose original clock anchor was overwritten.
The v4 density model counts the two literal-kind bits on profile misses and
reports both exact committed bits and per-chunk byte-rounded payload use; those
payload figures exclude file/chunk headers and chunk slack, which are reported
separately.

### Direct Proto Access

The package also provides direct access to the generated protobuf modules:

```python
# Import the proto module
from retrobus_perfetto.proto import perfetto_pb2

# Create proto objects directly
trace = perfetto_pb2.Trace()
# ... manipulate trace ...
```

## Project Structure

- `retrobus_perfetto/` - Main package source code
  - `builder.py` - Main trace builder class
  - `annotations.py` - Annotation helper classes
  - `compact.py` - Streaming compact decoder and Perfetto reconstruction
  - `compact_schema.py` - Producer schema validation and C-header generation
  - `merge.py` - Collision-safe multi-source Perfetto merge
  - `proto/` - Generated protobuf files (created during build)
    - `perfetto_pb2.py` - Generated Perfetto protobuf definitions
- `tests/` - Unit tests
- `example.py` - Example usage
- `pyproject.toml` - Package configuration
