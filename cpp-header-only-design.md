# C++ Header-Only Design for retrobus-perfetto

## Overview

This document outlines the design for a header-only C++ version of the retrobus-perfetto library, providing a modern C++ API for creating Perfetto traces for retrocomputer emulators.

## Design Goals

- **Header-only**: Single header include for easy integration
- **Modern C++**: Leverage C++17/20 features for safety and expressiveness
- **Zero-overhead**: Template-based design with compile-time optimizations
- **Type-safe**: Strong typing for annotations and API usage
- **Fluent API**: Method chaining for intuitive trace building

## Architecture

### Core API Structure

```cpp
// retrobus_perfetto.hpp
#pragma once

#include <atomic>
#include <filesystem>
#include <memory>
#include <string_view>
#include <unordered_map>
#include <vector>

// Forward declarations for protobuf types
namespace perfetto::protos {
    class Trace;
    class TrackEvent;
    class DebugAnnotation;
}

namespace retrobus {

// Forward declarations
class TrackEventWrapper;
class AnnotationBuilder;

class PerfettoTraceBuilder {
private:
    std::unique_ptr<perfetto::protos::Trace> trace_;
    std::atomic<uint64_t> last_track_uuid_{0};
    std::atomic<uint64_t> last_thread_tid_{1000};
    uint64_t process_uuid_;
    int32_t pid_;
    
    // Metadata tracking
    std::unordered_map<uint64_t, std::string> track_names_;
    std::unordered_map<uint64_t, uint64_t> track_parents_;
    
public:
    explicit PerfettoTraceBuilder(std::string_view process_name, int32_t pid = 1234);
    ~PerfettoTraceBuilder() = default;
    
    // Non-copyable, moveable
    PerfettoTraceBuilder(const PerfettoTraceBuilder&) = delete;
    PerfettoTraceBuilder& operator=(const PerfettoTraceBuilder&) = delete;
    PerfettoTraceBuilder(PerfettoTraceBuilder&&) = default;
    PerfettoTraceBuilder& operator=(PerfettoTraceBuilder&&) = default;
    
    // Track management
    [[nodiscard]] auto add_thread(std::string_view name) -> uint64_t;
    [[nodiscard]] auto add_counter_track(std::string_view name, std::string_view unit) -> uint64_t;
    
    // Event creation - returns wrapper for annotation chaining
    [[nodiscard]] auto begin_slice(uint64_t track_uuid, std::string_view name, uint64_t timestamp_ns) 
        -> TrackEventWrapper;
    
    void end_slice(uint64_t track_uuid, uint64_t timestamp_ns);
    
    [[nodiscard]] auto add_instant_event(uint64_t track_uuid, std::string_view name, uint64_t timestamp_ns)
        -> TrackEventWrapper;
    
    [[nodiscard]] auto add_flow(uint64_t track_uuid, std::string_view name, uint64_t timestamp_ns,
                                 uint64_t flow_id, bool terminating = false) -> TrackEventWrapper;
    
    void update_counter(uint64_t track_uuid, double value, uint64_t timestamp_ns);
    
    // Serialization
    void save(const std::filesystem::path& path) const;
    [[nodiscard]] std::vector<uint8_t> serialize() const;
    
    // Metadata queries
    [[nodiscard]] auto get_track_name(uint64_t track_uuid) const -> std::optional<std::string_view>;
    [[nodiscard]] auto get_all_tracks() const -> std::vector<std::pair<uint64_t, std::string>>;
};

class TrackEventWrapper {
private:
    friend class PerfettoTraceBuilder;
    perfetto::protos::TrackEvent* event_;
    
    explicit TrackEventWrapper(perfetto::protos::TrackEvent* event) : event_(event) {}
    
public:
    // Variadic template for type-safe annotations
    template<typename... Args>
    auto add_annotations(Args&&... args) -> TrackEventWrapper&;
    
    // Individual annotation methods
    auto add_annotation(std::string_view key, int64_t value) -> TrackEventWrapper&;
    auto add_annotation(std::string_view key, double value) -> TrackEventWrapper&;
    auto add_annotation(std::string_view key, bool value) -> TrackEventWrapper&;
    auto add_annotation(std::string_view key, std::string_view value) -> TrackEventWrapper&;
    
    // RAII annotation context
    [[nodiscard]] auto annotation(std::string_view name) -> AnnotationBuilder;
    
    // Pointer annotation with automatic formatting
    auto add_pointer(std::string_view key, uint64_t address) -> TrackEventWrapper&;
};

class AnnotationBuilder {
private:
    perfetto::protos::DebugAnnotation* annotation_;
    
public:
    explicit AnnotationBuilder(perfetto::protos::DebugAnnotation* annotation) 
        : annotation_(annotation) {}
    
    // Typed annotation methods
    auto integer(std::string_view key, int64_t value) -> AnnotationBuilder&;
    auto floating(std::string_view key, double value) -> AnnotationBuilder&;
    auto boolean(std::string_view key, bool value) -> AnnotationBuilder&;
    auto string(std::string_view key, std::string_view value) -> AnnotationBuilder&;
    auto pointer(std::string_view key, uint64_t address) -> AnnotationBuilder&;
    
    // Nested annotations
    [[nodiscard]] auto nested(std::string_view key) -> AnnotationBuilder;
};

// Utility functions
namespace detail {
    // Type trait for annotation value detection
    template<typename T>
    struct is_annotation_value : std::false_type {};
    
    template<>
    struct is_annotation_value<int64_t> : std::true_type {};
    
    template<>
    struct is_annotation_value<double> : std::true_type {};
    
    template<>
    struct is_annotation_value<bool> : std::true_type {};
    
    template<>
    struct is_annotation_value<std::string_view> : std::true_type {};
    
    // Pointer heuristic detection
    inline bool is_pointer_key(std::string_view key) {
        return key.ends_with("_addr") || 
               key.ends_with("_address") || 
               key.ends_with("_pc") || 
               key.ends_with("_sp") || 
               key.ends_with("_pointer") ||
               key == "pc" || 
               key == "sp" || 
               key == "address";
    }
}

// Template implementation for variadic annotations
template<typename... Args>
auto TrackEventWrapper::add_annotations(Args&&... args) -> TrackEventWrapper& {
    static_assert(sizeof...(args) % 2 == 0, "Annotations must be key-value pairs");
    add_annotations_impl(std::forward<Args>(args)...);
    return *this;
}

} // namespace retrobus
```

## Usage Examples

### Basic Usage

```cpp
#include <retrobus/perfetto_trace_builder.hpp>

int main() {
    // Create trace builder
    retrobus::PerfettoTraceBuilder builder("Z80 Emulator");
    
    // Add execution contexts
    auto cpu_thread = builder.add_thread("CPU");
    auto io_thread = builder.add_thread("I/O");
    
    // Record a CPU instruction
    builder.begin_slice(cpu_thread, "CALL", 1000)
        .add_annotation("pc", 0x1234)
        .add_annotation("opcode", 0xCD)
        .add_annotation("target", 0x5678);
    builder.end_slice(cpu_thread, 2000);
    
    // Record I/O event
    builder.add_instant_event(io_thread, "Port Write", 1500)
        .add_annotation("port", 0x10)
        .add_annotation("value", 0xFF);
    
    // Save trace
    builder.save("emulator.perfetto-trace");
}
```

### Advanced Annotations

```cpp
// Using annotation builder for structured data
builder.begin_slice(cpu_thread, "interrupt_handler", timestamp)
    .annotation("registers")
        .integer("A", cpu.a)
        .integer("B", cpu.b)
        .integer("C", cpu.c)
        .pointer("PC", cpu.pc)
        .pointer("SP", cpu.sp)
    .annotation("flags")
        .boolean("zero", cpu.flags.z)
        .boolean("carry", cpu.flags.c)
        .boolean("interrupt", cpu.flags.i);
```

### Counter Tracking

```cpp
// Create counter track
auto memory_track = builder.add_counter_track("Free Memory", "KB");

// Update counter values over time
builder.update_counter(memory_track, 1024.0, 1000);
builder.update_counter(memory_track, 768.0, 2000);
builder.update_counter(memory_track, 512.0, 3000);
```

## Implementation Details

### Memory Management
- Use `std::unique_ptr` for trace ownership
- Return lightweight wrappers that don't own memory
- RAII patterns for automatic resource management

### Thread Safety
- `std::atomic` for UUID generation
- Builder can be used from multiple threads
- Individual event creation is thread-safe

### Error Handling
```cpp
// Option 1: Exceptions (default)
try {
    builder.save("trace.perfetto-trace");
} catch (const std::runtime_error& e) {
    // Handle error
}

// Option 2: Expected/Result pattern (with macro)
#ifdef RETROBUS_USE_EXPECTED
    auto result = builder.try_save("trace.perfetto-trace");
    if (!result) {
        // Handle error: result.error()
    }
#endif
```

### Build System Integration

#### CMake FetchContent
```cmake
include(FetchContent)
FetchContent_Declare(
    retrobus_perfetto
    GIT_REPOSITORY https://github.com/user/retrobus-perfetto-cpp.git
    GIT_TAG main
)
FetchContent_MakeAvailable(retrobus_perfetto)

target_link_libraries(myapp PRIVATE retrobus::perfetto)
```

#### Direct Include
```cpp
#include "path/to/retrobus_perfetto.hpp"
```

## Dependencies

- C++17 compatible compiler
- Protobuf library (for perfetto proto definitions)
- Standard library with `<filesystem>` support

## Performance Considerations

1. **Zero-cost abstractions**: Templates resolved at compile time
2. **Move semantics**: Avoid unnecessary copies
3. **String views**: Avoid string allocations where possible
4. **Inline functions**: Most methods can be inlined
5. **Reserve capacity**: Pre-allocate vector space where size is known

## Future Enhancements

1. **C++20 Concepts**: Add concept constraints for better error messages
2. **Coroutine Support**: Async trace writing
3. **Compile-time Validation**: Use `constexpr` for more checks
4. **Custom Allocators**: Support for custom memory allocation
5. **Structured Bindings**: For metadata queries

## Testing Strategy

```cpp
// Example test using Catch2
TEST_CASE("TraceBuilder creates valid traces", "[builder]") {
    retrobus::PerfettoTraceBuilder builder("Test");
    
    auto thread = builder.add_thread("TestThread");
    REQUIRE(thread > 0);
    
    auto data = builder.serialize();
    REQUIRE(!data.empty());
    
    // Verify protobuf can parse it
    perfetto::protos::Trace trace;
    REQUIRE(trace.ParseFromArray(data.data(), data.size()));
}
```

## License

Same as Python version (MIT)