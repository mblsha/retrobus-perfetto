# retrobus-perfetto C++ Implementation

This directory contains the C++ header-only implementation of retrobus-perfetto.

## Features

- Header-only library for easy integration
- Modern C++ (C++17) API
- Zero-overhead abstractions with templates
- Thread-safe trace building
- Compatible protobuf format with Python implementation

## Requirements

- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- CMake 3.14 or higher
- Protocol Buffers (protobuf) library
- Catch2 (automatically fetched for tests)

## Building

### Basic Build

```bash
cd cpp
mkdir build && cd build
cmake ..
make
```

### Build Options

```bash
# Disable tests
cmake .. -DBUILD_TESTS=OFF

# Disable examples
cmake .. -DBUILD_EXAMPLES=OFF

# Release build
cmake .. -DCMAKE_BUILD_TYPE=Release

# Install to custom location
cmake .. -DCMAKE_INSTALL_PREFIX=/path/to/install
make install
```

### Running Tests

```bash
cd build
ctest
# or
./tests/test_retrobus_perfetto
```

### Running Examples

```bash
cd build

# Basic example
./examples/basic_example
# Creates example.perfetto-trace

# CPU emulator example
./examples/cpu_emulator_example
# Creates z80_emulation.perfetto-trace
```

## Integration

### Method 1: Header-Only Include

Simply copy `include/retrobus/retrobus_perfetto.hpp` to your project and include it:

```cpp
#include "retrobus_perfetto.hpp"
```

You'll need to:
1. Generate the protobuf files from `../proto/perfetto.proto`
2. Link against protobuf library
3. Ensure C++17 is enabled

### Method 2: CMake FetchContent

```cmake
include(FetchContent)
FetchContent_Declare(
    retrobus_perfetto
    GIT_REPOSITORY https://github.com/yourusername/retrobus-perfetto.git
    GIT_TAG main
    SOURCE_SUBDIR cpp
)
FetchContent_MakeAvailable(retrobus_perfetto)

target_link_libraries(your_target PRIVATE retrobus::perfetto)
```

### Method 3: CMake Find Package

After installing:

```cmake
find_package(retrobus_perfetto REQUIRED)
target_link_libraries(your_target PRIVATE retrobus::perfetto)
```

## Usage Example

```cpp
#include <retrobus/retrobus_perfetto.hpp>

int main() {
    // Create trace builder
    retrobus::PerfettoTraceBuilder builder("My Emulator");
    
    // Add threads
    auto cpu_thread = builder.add_thread("CPU");
    auto io_thread = builder.add_thread("I/O");
    
    // Record CPU instruction
    auto event = builder.begin_slice(cpu_thread, "CALL", 1000);
    event.add_annotation("pc", 0x1234)
         .add_annotation("opcode", 0xCD);
    builder.end_slice(cpu_thread, 2000);
    
    // Record I/O operation
    builder.add_instant_event(io_thread, "Port Write", 1500)
        .add_annotation("port", 0x10)
        .add_annotation("value", 0xFF);
    
    // Save trace
    builder.save("trace.perfetto-trace");
}
```

## API Reference

### PerfettoTraceBuilder

Main builder class for creating traces.

```cpp
// Construction
PerfettoTraceBuilder(std::string_view process_name, int32_t pid = 1234);

// Track management
uint64_t add_thread(std::string_view name);
uint64_t add_counter_track(std::string_view name, std::string_view unit);

// Events
TrackEventWrapper begin_slice(uint64_t track, std::string_view name, uint64_t timestamp_ns);
void end_slice(uint64_t track, uint64_t timestamp_ns);
TrackEventWrapper add_instant_event(uint64_t track, std::string_view name, uint64_t timestamp_ns);
TrackEventWrapper add_flow(uint64_t track, std::string_view name, uint64_t timestamp_ns, 
                           uint64_t flow_id, bool terminating = false);

// Counters
void update_counter(uint64_t track, double value, uint64_t timestamp_ns);

// Output
void save(const std::filesystem::path& path) const;
std::vector<uint8_t> serialize() const;
```

### TrackEventWrapper

Returned from event creation methods to enable annotation chaining.

```cpp
// Add individual annotations
TrackEventWrapper& add_annotation(std::string_view key, int64_t value);
TrackEventWrapper& add_annotation(std::string_view key, double value);
TrackEventWrapper& add_annotation(std::string_view key, bool value);
TrackEventWrapper& add_annotation(std::string_view key, std::string_view value);

// Add pointer (automatically formatted)
TrackEventWrapper& add_pointer(std::string_view key, uint64_t address);

// Structured annotations
AnnotationBuilder annotation(std::string_view name);

// Variadic annotations
template<typename... Args>
TrackEventWrapper& add_annotations(Args&&... args);
```

### AnnotationBuilder

For creating structured/nested annotations.

```cpp
AnnotationBuilder& integer(std::string_view key, int64_t value);
AnnotationBuilder& floating(std::string_view key, double value);
AnnotationBuilder& boolean(std::string_view key, bool value);
AnnotationBuilder& string(std::string_view key, std::string_view value);
AnnotationBuilder& pointer(std::string_view key, uint64_t address);
```

## Performance Notes

- Header-only design enables inlining and optimization
- Uses `std::string_view` to avoid string copies
- Atomic operations for thread-safe UUID generation
- Move semantics prevent unnecessary copies
- Direct protobuf serialization for efficiency

## Differences from Python Version

- Compile-time type safety for annotations
- RAII patterns instead of context managers
- Template-based variadic annotations
- No runtime overhead from dynamic typing
- Explicit timestamp parameters (no defaults)