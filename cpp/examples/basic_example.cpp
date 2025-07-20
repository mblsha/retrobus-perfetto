// basic_example.cpp - Basic usage example of retrobus_perfetto library

#include <retrobus/retrobus_perfetto.hpp>
#include <iostream>

int main() {
    // Create trace builder
    retrobus::PerfettoTraceBuilder builder("Z80 Emulator");
    
    // Add execution contexts
    auto cpu_thread = builder.add_thread("CPU");
    auto io_thread = builder.add_thread("I/O");
    auto memory_track = builder.add_counter_track("Free Memory", "KB");
    
    // Simulate some CPU instructions
    uint64_t timestamp = 1000; // Start at 1µs
    
    // Instruction 1: CALL
    auto call_event = builder.begin_slice(cpu_thread, "CALL", timestamp);
    call_event.add_annotation("pc", 0x1234)
              .add_annotation("opcode", 0xCD)
              .add_annotation("target", 0x5678);
    timestamp += 1000; // 1µs duration
    builder.end_slice(cpu_thread, timestamp);
    
    // Memory update
    builder.update_counter(memory_track, 1024.0, timestamp);
    
    // I/O operation during the call
    auto io_event = builder.add_instant_event(io_thread, "Port Write", timestamp - 500);
    io_event.add_annotation("port", 0x10)
            .add_annotation("value", 0xFF);
    
    // Instruction 2: RET with structured annotations
    timestamp += 100;
    auto ret_event = builder.begin_slice(cpu_thread, "RET", timestamp);
    
    // Add structured register state
    ret_event.annotation("registers")
        .integer("A", 0x42)
        .integer("B", 0x00)
        .integer("C", 0xFF)
        .pointer("PC", 0x5678)
        .pointer("SP", 0x7FFE);
    
    ret_event.annotation("flags")
        .boolean("zero", true)
        .boolean("carry", false)
        .boolean("interrupt", true);
    
    timestamp += 800;
    builder.end_slice(cpu_thread, timestamp);
    
    // Memory update
    builder.update_counter(memory_track, 1020.0, timestamp);
    
    // Flow event example - async I/O
    uint64_t flow_id = 0xABCD;
    timestamp += 500;
    
    // Start flow on CPU thread
    auto flow_start = builder.add_flow(cpu_thread, "DMA Request", timestamp, flow_id);
    flow_start.add_annotation("address", 0x8000)
              .add_annotation("size", 256);
    
    // Complete flow on I/O thread
    timestamp += 2000;
    auto flow_end = builder.add_flow(io_thread, "DMA Complete", timestamp, flow_id, true);
    flow_end.add_annotation("bytes_transferred", 256);
    
    // Save the trace
    std::cout << "Saving trace to example.perfetto-trace\n";
    builder.save("example.perfetto-trace");
    
    // Also demonstrate getting metadata
    std::cout << "\nTrace contains the following tracks:\n";
    for (const auto& [uuid, name] : builder.get_all_tracks()) {
        std::cout << "  Track " << uuid << ": " << name << "\n";
    }
    
    std::cout << "\nTrace saved successfully!\n";
    std::cout << "View it at https://ui.perfetto.dev\n";
    
    return 0;
}