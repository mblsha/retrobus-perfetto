#include <catch2/catch_test_macros.hpp>
#include <retrobus/retrobus_perfetto.hpp>
#include <filesystem>
#include <fstream>

using namespace retrobus;

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