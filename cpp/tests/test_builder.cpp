#include <catch2/catch_test_macros.hpp>
#include <retrobus/retrobus_perfetto.hpp>
#include <filesystem>
#include <fstream>
#include <google/protobuf/text_format.h>

using namespace retrobus;

// Helper function to convert builder output to textproto string
std::string to_textproto(const PerfettoTraceBuilder& builder) {
    auto data = builder.serialize();
    
    perfetto::protos::Trace trace;
    if (!trace.ParseFromArray(data.data(), static_cast<int>(data.size()))) {
        return "ERROR: Failed to parse trace data";
    }
    
    std::string textproto;
    google::protobuf::TextFormat::PrintToString(trace, &textproto);
    return textproto;
}

TEST_CASE("PerfettoTraceBuilder construction", "[builder]") {
    SECTION("Default constructor") {
        PerfettoTraceBuilder builder("TestProcess");
        
        // Should be able to serialize even empty trace
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
    
    SECTION("Custom PID") {
        PerfettoTraceBuilder builder("TestProcess", 5678);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
}

TEST_CASE("Track management", "[builder][tracks]") {
    PerfettoTraceBuilder builder("TestProcess");
    
    SECTION("Add thread") {
        auto thread_id = builder.add_thread("TestThread");
        REQUIRE(thread_id > 0);
        
        // Check metadata
        auto track_name = builder.get_track_name(thread_id);
        REQUIRE(track_name.has_value());
        REQUIRE(track_name.value() == "TestThread");
    }
    
    SECTION("Add multiple threads") {
        auto thread1 = builder.add_thread("Thread1");
        auto thread2 = builder.add_thread("Thread2");
        
        REQUIRE(thread1 != thread2);
        REQUIRE(thread1 > 0);
        REQUIRE(thread2 > 0);
    }
    
    SECTION("Add counter track") {
        auto counter = builder.add_counter_track("Memory", "MB");
        REQUIRE(counter > 0);
        
        auto track_name = builder.get_track_name(counter);
        REQUIRE(track_name.has_value());
        REQUIRE(track_name.value() == "Memory");
    }
    
    SECTION("Get all tracks") {
        auto thread1 = builder.add_thread("Thread1");
        auto thread2 = builder.add_thread("Thread2");
        auto counter = builder.add_counter_track("CPU", "%");
        
        auto tracks = builder.get_all_tracks();
        REQUIRE(tracks.size() == 4); // Process + 3 tracks
        
        // Verify all tracks are present
        bool found_thread1 = false, found_thread2 = false, found_counter = false;
        for (const auto& [uuid, name] : tracks) {
            if (name == "Thread1") found_thread1 = true;
            if (name == "Thread2") found_thread2 = true;
            if (name == "CPU") found_counter = true;
        }
        
        REQUIRE(found_thread1);
        REQUIRE(found_thread2);
        REQUIRE(found_counter);
    }
}

TEST_CASE("Slice events", "[builder][events]") {
    PerfettoTraceBuilder builder("TestProcess");
    auto thread = builder.add_thread("TestThread");
    
    SECTION("Basic slice") {
        builder.begin_slice(thread, "test_function", 1000);
        builder.end_slice(thread, 2000);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
    
    SECTION("Slice with annotations") {
        auto event = builder.begin_slice(thread, "test_function", 1000);
        event.add_annotation("arg1", 42)
             .add_annotation("arg2", 3.14)
             .add_annotation("arg3", true)
             .add_annotation("arg4", "hello");
        
        builder.end_slice(thread, 2000);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
    
    SECTION("Nested slices") {
        builder.begin_slice(thread, "outer", 1000);
        builder.begin_slice(thread, "inner", 1100);
        builder.end_slice(thread, 1200);
        builder.end_slice(thread, 1300);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
}

TEST_CASE("Instant events", "[builder][events]") {
    PerfettoTraceBuilder builder("TestProcess");
    auto thread = builder.add_thread("TestThread");
    
    SECTION("Basic instant event") {
        builder.add_instant_event(thread, "test_event", 1500);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
    
    SECTION("Instant event with annotations") {
        auto event = builder.add_instant_event(thread, "io_operation", 1500);
        event.add_annotation("port", 0x80)
             .add_annotation("value", 0xFF);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
}

TEST_CASE("Flow events", "[builder][events]") {
    PerfettoTraceBuilder builder("TestProcess");
    auto thread1 = builder.add_thread("Thread1");
    auto thread2 = builder.add_thread("Thread2");
    
    SECTION("Basic flow") {
        uint64_t flow_id = 12345;
        
        builder.add_flow(thread1, "Send", 1000, flow_id);
        builder.add_flow(thread2, "Receive", 2000, flow_id, true);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
}

TEST_CASE("Counter updates", "[builder][counters]") {
    PerfettoTraceBuilder builder("TestProcess");
    auto counter = builder.add_counter_track("Memory", "KB");
    
    SECTION("Integer counter values") {
        builder.update_counter(counter, 1024, 1000);
        builder.update_counter(counter, 2048, 2000);
        builder.update_counter(counter, 1536, 3000);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
    
    SECTION("Floating point counter values") {
        builder.update_counter(counter, 1024.5, 1000);
        builder.update_counter(counter, 2048.75, 2000);
        builder.update_counter(counter, 1536.25, 3000);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
}

TEST_CASE("Annotations", "[builder][annotations]") {
    PerfettoTraceBuilder builder("TestProcess");
    auto thread = builder.add_thread("TestThread");
    
    SECTION("Pointer detection") {
        auto event = builder.begin_slice(thread, "test", 1000);
        event.add_annotation("pc", 0x1234)
             .add_annotation("sp", 0x8000)
             .add_annotation("address", 0x5678)
             .add_annotation("data_pointer", 0xABCD)
             .add_annotation("value", 42); // Should not be a pointer
        
        builder.end_slice(thread, 2000);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
    
    SECTION("Variadic annotations") {
        auto event = builder.begin_slice(thread, "test", 1000);
        event.add_annotations(
            "key1", 123,
            "key2", 45.67,
            "key3", true,
            "key4", "value"
        );
        
        builder.end_slice(thread, 2000);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
    
    SECTION("Structured annotations") {
        auto event = builder.begin_slice(thread, "test", 1000);
        
        event.annotation("registers")
            .integer("A", 0x12)
            .integer("B", 0x34)
            .pointer("PC", 0x1234)
            .pointer("SP", 0x8000);
        
        event.annotation("flags")
            .boolean("zero", true)
            .boolean("carry", false)
            .boolean("interrupt", true);
        
        builder.end_slice(thread, 2000);
        
        auto data = builder.serialize();
        REQUIRE(!data.empty());
    }
}

TEST_CASE("Serialization", "[builder][serialization]") {
    PerfettoTraceBuilder builder("TestProcess");
    auto thread = builder.add_thread("TestThread");
    
    // Add some events
    builder.begin_slice(thread, "test", 1000);
    builder.add_instant_event(thread, "event", 1500);
    builder.end_slice(thread, 2000);
    
    SECTION("Serialize to vector") {
        auto data = builder.serialize();
        REQUIRE(!data.empty());
        
        // Verify it's valid protobuf
        perfetto::protos::Trace trace;
        REQUIRE(trace.ParseFromArray(data.data(), static_cast<int>(data.size())));
        REQUIRE(trace.packet_size() > 0);
    }
    
    SECTION("Save to file") {
        std::filesystem::path temp_file = "test_trace.perfetto-trace";
        
        builder.save(temp_file);
        REQUIRE(std::filesystem::exists(temp_file));
        
        // Verify file content
        std::ifstream file(temp_file, std::ios::binary);
        std::vector<char> file_data((std::istreambuf_iterator<char>(file)),
                                     std::istreambuf_iterator<char>());
        
        perfetto::protos::Trace trace;
        REQUIRE(trace.ParseFromArray(file_data.data(), static_cast<int>(file_data.size())));
        REQUIRE(trace.packet_size() > 0);
        
        // Cleanup
        std::filesystem::remove(temp_file);
    }
}

TEST_CASE("Thread safety", "[builder][thread-safety]") {
    PerfettoTraceBuilder builder("TestProcess");
    
    SECTION("Concurrent track creation") {
        std::vector<uint64_t> thread_ids;
        const int num_threads = 10;
        
        // Create threads concurrently (simplified test - not actually concurrent)
        for (int i = 0; i < num_threads; ++i) {
            thread_ids.push_back(builder.add_thread("Thread" + std::to_string(i)));
        }
        
        // All IDs should be unique
        std::set<uint64_t> unique_ids(thread_ids.begin(), thread_ids.end());
        REQUIRE(unique_ids.size() == num_threads);
    }
}

TEST_CASE("Textproto snapshot validation", "[builder][snapshot]") {
    SECTION("Empty trace") {
        PerfettoTraceBuilder builder("TestProcess", 1234);
        
        const char* expected = R"proto(packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 1
    name: "TestProcess"
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
)proto";
        
        REQUIRE(to_textproto(builder) == expected);
    }
    
    SECTION("Single thread") {
        PerfettoTraceBuilder builder("TestProcess", 1234);
        auto thread = builder.add_thread("TestThread");
        
        const char* expected = R"proto(packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 1
    name: "TestProcess"
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 2
    name: "TestThread"
    thread {
      pid: 1234
      tid: 1001
      thread_name: "TestThread"
    }
  }
}
)proto";
        
        REQUIRE(to_textproto(builder) == expected);
    }
    
    SECTION("Basic slice event") {
        PerfettoTraceBuilder builder("TestProcess", 1234);
        auto thread = builder.add_thread("TestThread");
        
        builder.begin_slice(thread, "test_function", 1000);
        builder.end_slice(thread, 2000);
        
        const char* expected = R"proto(packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 1
    name: "TestProcess"
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 2
    name: "TestThread"
    thread {
      pid: 1234
      tid: 1001
      thread_name: "TestThread"
    }
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_SLICE_BEGIN
    track_uuid: 2
    name: "test_function"
  }
}
packet {
  timestamp: 2000
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_SLICE_END
    track_uuid: 2
  }
}
)proto";
        
        REQUIRE(to_textproto(builder) == expected);
    }
    
    SECTION("Instant event") {
        PerfettoTraceBuilder builder("TestProcess", 1234);
        auto thread = builder.add_thread("TestThread");
        
        builder.add_instant_event(thread, "checkpoint", 1500);
        
        const char* expected = R"proto(packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 1
    name: "TestProcess"
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 2
    name: "TestThread"
    thread {
      pid: 1234
      tid: 1001
      thread_name: "TestThread"
    }
  }
}
packet {
  timestamp: 1500
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_INSTANT
    track_uuid: 2
    name: "checkpoint"
  }
}
)proto";
        
        REQUIRE(to_textproto(builder) == expected);
    }
    
    SECTION("Counter track and updates") {
        PerfettoTraceBuilder builder("TestProcess", 1234);
        auto counter = builder.add_counter_track("Memory", "MB");
        
        builder.update_counter(counter, 100, 1000);
        builder.update_counter(counter, 150.5, 2000);
        
        const char* expected = R"proto(packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 1
    name: "TestProcess"
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 2
    name: "Memory (MB)"
    parent_uuid: 1
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_COUNTER
    track_uuid: 2
    counter_value: 100
  }
}
packet {
  timestamp: 2000
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_COUNTER
    track_uuid: 2
    double_counter_value: 150.5
  }
}
)proto";
        
        REQUIRE(to_textproto(builder) == expected);
    }
    
    SECTION("Slice with annotations") {
        PerfettoTraceBuilder builder("TestProcess", 1234);
        auto thread = builder.add_thread("TestThread");
        
        auto event = builder.begin_slice(thread, "test_function", 1000);
        event.add_annotation("arg_int", 42)
             .add_annotation("arg_float", 3.14)
             .add_annotation("arg_bool", true)
             .add_annotation("arg_string", "hello")
             .add_annotation("pc", 0x1234);  // Should be formatted as pointer
        
        builder.end_slice(thread, 2000);
        
        const char* expected = R"proto(packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 1
    name: "TestProcess"
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 2
    name: "TestThread"
    thread {
      pid: 1234
      tid: 1001
      thread_name: "TestThread"
    }
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 1
  track_event {
    debug_annotations {
      int_value: 42
      name: "arg_int"
    }
    debug_annotations {
      double_value: 3.14
      name: "arg_float"
    }
    debug_annotations {
      bool_value: true
      name: "arg_bool"
    }
    debug_annotations {
      string_value: "hello"
      name: "arg_string"
    }
    debug_annotations {
      pointer_value: 4660
      name: "pc"
    }
    type: TYPE_SLICE_BEGIN
    track_uuid: 2
    name: "test_function"
  }
}
packet {
  timestamp: 2000
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_SLICE_END
    track_uuid: 2
  }
}
)proto";
        
        REQUIRE(to_textproto(builder) == expected);
    }
    
    SECTION("Flow events") {
        PerfettoTraceBuilder builder("TestProcess", 1234);
        auto thread1 = builder.add_thread("Producer");
        auto thread2 = builder.add_thread("Consumer");
        
        uint64_t flow_id = 12345;
        
        builder.add_flow(thread1, "Send", 1000, flow_id);
        builder.add_flow(thread2, "Receive", 2000, flow_id, true);
        
        const char* expected = R"proto(packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 1
    name: "TestProcess"
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 2
    name: "Producer"
    thread {
      pid: 1234
      tid: 1001
      thread_name: "Producer"
    }
  }
}
packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 3
    name: "Consumer"
    thread {
      pid: 1234
      tid: 1002
      thread_name: "Consumer"
    }
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_INSTANT
    track_uuid: 2
    name: "Send"
    flow_ids: 12345
  }
}
packet {
  timestamp: 2000
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_INSTANT
    track_uuid: 3
    name: "Receive"
    terminating_flow_ids: 12345
  }
}
)proto";
        
        REQUIRE(to_textproto(builder) == expected);
    }
    
    SECTION("Nested slices") {
        PerfettoTraceBuilder builder("TestProcess", 1234);
        auto thread = builder.add_thread("TestThread");
        
        builder.begin_slice(thread, "outer_function", 1000);
        builder.begin_slice(thread, "inner_function", 1100);
        builder.end_slice(thread, 1200);
        builder.end_slice(thread, 1300);
        
        const char* expected = R"proto(packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 1
    name: "TestProcess"
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 2
    name: "TestThread"
    thread {
      pid: 1234
      tid: 1001
      thread_name: "TestThread"
    }
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_SLICE_BEGIN
    track_uuid: 2
    name: "outer_function"
  }
}
packet {
  timestamp: 1100
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_SLICE_BEGIN
    track_uuid: 2
    name: "inner_function"
  }
}
packet {
  timestamp: 1200
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_SLICE_END
    track_uuid: 2
  }
}
packet {
  timestamp: 1300
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_SLICE_END
    track_uuid: 2
  }
}
)proto";
        
        REQUIRE(to_textproto(builder) == expected);
    }
    
    SECTION("Structured annotations") {
        PerfettoTraceBuilder builder("TestProcess", 1234);
        auto thread = builder.add_thread("TestThread");
        
        auto event = builder.begin_slice(thread, "cpu_instruction", 1000);
        
        event.annotation("registers")
            .integer("A", 0x12)
            .integer("B", 0x34)
            .pointer("PC", 0x1234)
            .pointer("SP", 0x8000);
        
        event.annotation("flags")
            .boolean("zero", true)
            .boolean("carry", false);
        
        builder.end_slice(thread, 1100);
        
        const char* expected = R"proto(packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 1
    name: "TestProcess"
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  trusted_packet_sequence_id: 1
  track_descriptor {
    uuid: 2
    name: "TestThread"
    thread {
      pid: 1234
      tid: 1001
      thread_name: "TestThread"
    }
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 1
  track_event {
    debug_annotations {
      name: "registers"
      dict_entries {
        int_value: 18
        name: "A"
      }
      dict_entries {
        int_value: 52
        name: "B"
      }
      dict_entries {
        pointer_value: 4660
        name: "PC"
      }
      dict_entries {
        pointer_value: 32768
        name: "SP"
      }
    }
    debug_annotations {
      name: "flags"
      dict_entries {
        bool_value: true
        name: "zero"
      }
      dict_entries {
        bool_value: false
        name: "carry"
      }
    }
    type: TYPE_SLICE_BEGIN
    track_uuid: 2
    name: "cpu_instruction"
  }
}
packet {
  timestamp: 1100
  trusted_packet_sequence_id: 1
  track_event {
    type: TYPE_SLICE_END
    track_uuid: 2
  }
}
)proto";
        
        REQUIRE(to_textproto(builder) == expected);
    }
}
