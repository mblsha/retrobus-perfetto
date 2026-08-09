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

### Compact target captures

```python
from retrobus_perfetto import (
    CompactSchema,
    convert_compact_trace,
    profile_compact_trace,
)

schema = CompactSchema.load("producer-schema.json")
summary = convert_compact_trace(
    "capture.rbct",
    schema,
    "capture.perfetto-trace",
)
density = profile_compact_trace("capture.rbct", schema)
```

`CompactTraceReader.iter_items()` validates and yields one bounded chunk at a
time. `read_compact_trace()` collects a complete decoded model when host memory
is not constrained and pre-indexes clock generations and correlation anchors
for efficient timestamp conversion. Both entry points require the exact
external producer schema identified by the capture header. Unfinalized reads
are explicitly best-effort and report retained, successfully decoded records.
`profile_compact_trace()` replays those logical records through v1/v2/v3 and
reports byte attribution, density, varint widths, opcode hits, and chunk use.
`CompactTrace.uncorrelated_generations` identifies relative-only generations,
including a wrapped prefix whose original clock anchor was overwritten.

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
