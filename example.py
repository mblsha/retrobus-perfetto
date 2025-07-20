#!/usr/bin/env python3
"""Example usage of retrobus-perfetto package."""

import os
import sys

# Add the package to path for testing before installation
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Since protobuf is generated, import it first
sys.path.insert(0, os.path.join(script_dir, 'retrobus_perfetto', 'proto'))

from retrobus_perfetto import PerfettoTraceBuilder  # pylint: disable=C0413


def main():
    # Create a trace for a simple CPU emulator
    builder = PerfettoTraceBuilder("Example Emulator")

    # Create threads for different components
    cpu_thread = builder.add_thread("CPU")
    io_thread = builder.add_thread("I/O")
    builder.add_thread("Memory")  # Memory thread created but not used in this example

    # Simulate some CPU instructions
    timestamp = 1000  # Start at 1 microsecond

    # Instruction 1: CALL function
    event = builder.begin_slice(cpu_thread, "CALL draw_char", timestamp)
    event.add_annotations({
        "pc": 0x8440,
        "target": 0xBA36,
        "stack_pointer": 0x7FFE
    })

    # Nested function execution
    timestamp += 100
    nested = builder.begin_slice(cpu_thread, "draw_char", timestamp)
    with nested.annotation("parameters") as ann:
        ann.integer("char", 65)  # 'A'
        ann.integer("x", 10)
        ann.integer("y", 5)

    # I/O operation within function
    timestamp += 50
    io_event = builder.add_instant_event(io_thread, "LCD Write", timestamp)
    io_event.add_annotations({
        "port": 0x10,
        "value": 0xFF,
        "description": "Write pixel data"
    })

    # End nested function
    timestamp += 200
    builder.end_slice(cpu_thread, timestamp)

    # End CALL
    timestamp += 50
    builder.end_slice(cpu_thread, timestamp)

    # Memory access counter
    mem_counter = builder.add_counter_track("Memory Access", "ops/sec")
    builder.update_counter(mem_counter, 1000, timestamp)
    timestamp += 1000
    builder.update_counter(mem_counter, 1500, timestamp)

    # Flow example: Async I/O operation
    flow_id = 0x1234
    timestamp += 100

    # Start on CPU thread
    flow_start = builder.add_flow(cpu_thread, "Request I/O", timestamp, flow_id)
    flow_start.add_annotations({"request": "read_key"})

    # Process on I/O thread
    timestamp += 500
    builder.add_flow(io_thread, "Process Key Read", timestamp, flow_id)

    # Complete on CPU thread
    timestamp += 200
    flow_end = builder.add_flow(cpu_thread, "I/O Complete", timestamp, flow_id, terminating=True)
    flow_end.add_annotations({"key_code": 0x41})

    # Save the trace
    output_file = "example.perfetto-trace"
    builder.save(output_file)
    print(f"Trace saved to {output_file}")
    print("Open https://ui.perfetto.dev and load the file to view the trace")


if __name__ == "__main__":
    main()
