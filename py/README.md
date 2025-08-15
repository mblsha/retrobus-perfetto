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
trace_data = builder.build()
```

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
  - `proto/` - Generated protobuf files (created during build)
    - `perfetto_pb2.py` - Generated Perfetto protobuf definitions
- `tests/` - Unit tests
- `example.py` - Example usage
- `pyproject.toml` - Package configuration