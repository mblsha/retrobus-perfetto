# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

retrobus-perfetto is a minimal Perfetto trace generation library for retrocomputer emulators. It provides a CPU-independent API for creating execution traces that can be visualized in the Perfetto UI.

## Key Commands

### Development Setup
```bash
# Install for development (includes protoc tools)
pip install -e ".[dev]"

# Or install dev dependencies from requirements file
pip install -r requirements-dev.txt

# Run tests
pytest

# Run tests with coverage
pytest --cov=retrobus_perfetto --cov-report=xml --cov-report=term

# Run linter
pylint $(git ls-files '*.py')

# Run type checker (uses mypy.ini for configuration)
mypy retrobus_perfetto --config-file mypy.ini

# Build package
python -m build
```

### Building
The protobuf files are automatically compiled during installation via setup.py. Manual compilation if needed:
```bash
python -m grpc_tools.protoc --proto_path=retrobus_perfetto/proto --python_out=retrobus_perfetto/proto perfetto.proto
```

## Architecture

### Core Components
- **PerfettoTraceBuilder** (builder.py): Main API class using builder pattern for trace construction
- **Annotations** (annotations.py): Helper classes for structured metadata
- **Proto files**: perfetto.proto defines the trace format; perfetto_pb2.py is auto-generated

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
- Test files in tests/ directory
- Coverage reports available via pytest-cov

## Important Notes
- The library is CPU-independent - no assumptions about specific architectures
- Direct protobuf usage for maximum control (future may migrate to official SDK)
- Generated traces viewable at ui.perfetto.dev
- CI/CD pipeline includes: pylint, mypy, pytest with coverage, example testing, and package building
- Tests run on Python 3.8, 3.9, 3.10, 3.11, and 3.12
- Type checking configured to handle dynamic protobuf imports (see mypy.ini)
- Package is PEP 561 compliant with type stubs for generated protobuf code