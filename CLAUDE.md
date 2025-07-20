# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

retrobus-perfetto is a minimal Perfetto trace generation library for retrocomputer emulators. It provides a CPU-independent API for creating execution traces that can be visualized in the Perfetto UI.

This is a multi-language project:
- `py/` - Python implementation
- `cpp/` - C++ implementation (planned)
- `proto/` - Shared protocol buffer definitions

## Python Development

### Working Directory
When working on Python code, operate from the `py/` directory.

### Key Commands
```bash
cd py/

# Install for development (includes protoc tools)
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=retrobus_perfetto --cov-report=xml --cov-report=term

# Run linter
pylint $(git ls-files '*.py' | grep "^py/")

# Run type checker (uses mypy.ini for configuration)
mypy retrobus_perfetto --config-file mypy.ini

# Build package
python -m build
```

### Building
The protobuf files are automatically compiled during installation. The build process:
1. Reads proto files from `../proto/`
2. Generates Python files in `py/retrobus_perfetto/proto/`

Manual compilation if needed:
```bash
cd py/
python -m grpc_tools.protoc --proto_path=../proto --python_out=retrobus_perfetto/proto ../proto/perfetto.proto
```

## Architecture

### Core Components (Python)
- **PerfettoTraceBuilder** (py/retrobus_perfetto/builder.py): Main API class using builder pattern for trace construction
- **Annotations** (py/retrobus_perfetto/annotations.py): Helper classes for structured metadata
- **Proto files**: proto/perfetto.proto defines the trace format; generated files go to py/retrobus_perfetto/proto/

### Key Design Patterns
1. **Builder Pattern**: Fluent API for constructing traces
2. **Track-based Architecture**: Process tracks contain thread tracks and counter tracks
3. **Event Types**: Slices (duration), Instant (point-in-time), Flows (cross-thread), Counters (metrics)
4. **Time Handling**: All timestamps in nanoseconds

### Annotation System
- Automatic type detection for int, bool, float, string
- Heuristic pointer detection (fields named "pc", "address", "pointer" formatted as hex)
- Nested annotation groups for structured data

## Testing Approach
- Uses pytest with mocked protobuf dependencies to avoid compilation requirements during testing
- Test files in py/tests/ directory
- Coverage reports available via pytest-cov

## CI/CD
- **Python CI**: `.github/workflows/python-ci.yml` - runs when py/ or proto/ changes
- **C++ CI**: `.github/workflows/cpp-ci.yml` - placeholder for future C++ tests

## Important Notes
- The library is CPU-independent - no assumptions about specific architectures
- Direct protobuf usage for maximum control (future may migrate to official SDK)
- Generated traces viewable at ui.perfetto.dev
- Python CI pipeline includes: pylint, mypy, pytest with coverage, example testing, and package building
- Tests run on Python 3.8, 3.9, 3.10, 3.11, and 3.12
- Type checking configured to handle dynamic protobuf imports (see py/mypy.ini)
- Package is PEP 561 compliant with type stubs for generated protobuf code