# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

retrobus-perfetto is a minimal Perfetto trace generation library for retrocomputer emulators. It provides a CPU-independent API for creating execution traces that can be visualized in the Perfetto UI.

This is a multi-language project:
- `py/` - Python implementation
- `cpp/` - C++ header-only implementation
- `proto/` - Shared protocol buffer definitions
- `tools/` - Analysis tools for parsing and analyzing Perfetto traces

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
- **C++ CI**: `.github/workflows/cpp-ci.yml` - builds and tests C++ implementation
  - Matrix builds: Ubuntu/macOS × Debug/Release × g++/clang++
  - Runs unit tests with ctest
  - Executes example programs
  - Performs static analysis with clang-tidy and cppcheck
  - Verifies documentation

## C++ Development

### Working Directory
When working on C++ code, operate from the `cpp/` directory.

### Key Commands
```bash
cd cpp/
mkdir build && cd build

# Configure and build
cmake ..
cmake --build .

# Run tests
ctest --output-on-failure
# or
./tests/test_retrobus_perfetto

# Run examples
./examples/basic_example
./examples/cpu_emulator_example

# Build with specific options
cmake .. -DBUILD_TESTS=OFF -DBUILD_EXAMPLES=OFF
cmake .. -DCMAKE_BUILD_TYPE=Release
```

### C++ Implementation Details
- Header-only library in `cpp/include/retrobus/retrobus_perfetto.hpp`
- C++17 required for features like string_view and structured bindings
- Uses CMake FetchContent for Catch2 dependency
- Protobuf files are generated at build time into `build/proto/`
- Thread-safe with atomic counters for UUID generation
- Non-copyable/non-movable due to atomic members

### C++ Build Dependencies
- CMake 3.14+
- C++17 compiler (GCC 7+, Clang 5+, MSVC 2017+)
- Protocol Buffers (protobuf)
- abseil-cpp (required by protobuf)
- Catch2 (fetched automatically for tests)

### Known Build Issues
1. **Abseil linking**: Protobuf depends on abseil. If you get undefined symbols for `absl::lts_*`, ensure abseil libraries are linked:
   - The CMakeLists.txt links: `absl::log`, `absl::log_internal_check_op`, `absl::log_internal_message`, `absl::strings`

2. **C++17 compatibility**: The code avoids C++20 features:
   - Uses manual suffix checking instead of `string_view::ends_with`
   - Explicit move constructor deletion due to atomic members

## Important Notes
- The library is CPU-independent - no assumptions about specific architectures
- Direct protobuf usage for maximum control (future may migrate to official SDK)
- Generated traces viewable at ui.perfetto.dev
- Python CI pipeline includes: pylint, mypy, pytest with coverage, example testing, and package building
- Tests run on Python 3.8, 3.9, 3.10, 3.11, and 3.12
- Type checking configured to handle dynamic protobuf imports (see py/mypy.ini)
- Package is PEP 561 compliant with type stubs for generated protobuf code
- C++ implementation is header-only for easy integration
- Both Python and C++ implementations produce compatible trace files

## Trace Analysis Tools

The `tools/` directory contains standalone Python scripts for analyzing Perfetto traces:

### perfetto_pc_analyzer.py
- Extracts program counter (PC) addresses from CPU emulator traces
- Identifies performance hotspots and frequently executed code
- Can correlate addresses with Binary Ninja for function analysis
- Generates detailed performance reports

### perfetto_trace_parser.py
- Generic Perfetto trace parser for exploring trace contents
- Can extract strings, find patterns, and analyze protobuf structure
- Useful for understanding trace formats and debugging

These tools are designed to work with traces generated by retrobus-perfetto but can be adapted for other Perfetto traces. They require only Python standard library and have no external dependencies.