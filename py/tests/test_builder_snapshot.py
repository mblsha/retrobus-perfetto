"""Snapshot tests for PerfettoTraceBuilder using real protobuf."""

from google.protobuf import text_format
from retrobus_perfetto.proto import perfetto_pb2
from retrobus_perfetto import PerfettoTraceBuilder


def to_textproto(builder):
    """Convert builder output to textproto string."""
    data = builder.serialize()
    trace = perfetto_pb2.Trace()
    trace.ParseFromString(data)
    return text_format.MessageToString(trace)


class TestBuilderSnapshots:
    """Snapshot tests using real protobuf."""
    
    def test_empty_trace(self):
        """Test empty trace with only process descriptor."""
        builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
        
        expected = """packet {
  track_descriptor {
    uuid: 1
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
"""
        assert to_textproto(builder) == expected
    
    def test_single_thread(self):
        """Test trace with a single thread."""
        builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
        builder.add_thread("TestThread")
        
        expected = """packet {
  track_descriptor {
    uuid: 1
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  track_descriptor {
    uuid: 2
    thread {
      pid: 1234
      tid: 1
      thread_name: "TestThread"
    }
    parent_uuid: 1
  }
}
"""
        assert to_textproto(builder) == expected
    
    def test_basic_slice_event(self):
        """Test basic slice (duration) event."""
        builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
        thread = builder.add_thread("TestThread")
        
        builder.begin_slice(thread, "test_function", 1000)
        builder.end_slice(thread, 2000)
        
        expected = """packet {
  track_descriptor {
    uuid: 1
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  track_descriptor {
    uuid: 2
    thread {
      pid: 1234
      tid: 1
      thread_name: "TestThread"
    }
    parent_uuid: 1
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_SLICE_BEGIN
    track_uuid: 2
    name: "test_function"
  }
}
packet {
  timestamp: 2000
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_SLICE_END
    track_uuid: 2
  }
}
"""
        assert to_textproto(builder) == expected
    
    def test_instant_event(self):
        """Test instant (point-in-time) event."""
        builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
        thread = builder.add_thread("TestThread")
        
        builder.add_instant_event(thread, "checkpoint", 1500)
        
        expected = """packet {
  track_descriptor {
    uuid: 1
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  track_descriptor {
    uuid: 2
    thread {
      pid: 1234
      tid: 1
      thread_name: "TestThread"
    }
    parent_uuid: 1
  }
}
packet {
  timestamp: 1500
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_INSTANT
    track_uuid: 2
    name: "checkpoint"
  }
}
"""
        assert to_textproto(builder) == expected
    
    def test_counter_track_and_updates(self):
        """Test counter track with value updates."""
        builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
        counter = builder.add_counter_track("Memory", "MB")
        
        builder.update_counter(counter, 100, 1000)
        builder.update_counter(counter, 150.5, 2000)
        
        expected = """packet {
  track_descriptor {
    uuid: 1
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  track_descriptor {
    uuid: 2
    name: "Memory (MB)"
    parent_uuid: 1
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_COUNTER
    track_uuid: 2
    counter_value: 100
  }
}
packet {
  timestamp: 2000
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_COUNTER
    track_uuid: 2
    double_counter_value: 150.5
  }
}
"""
        assert to_textproto(builder) == expected
    
    def test_slice_with_annotations(self):
        """Test slice event with various annotation types."""
        builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
        thread = builder.add_thread("TestThread")
        
        event = builder.begin_slice(thread, "test_function", 1000)
        event.add_annotations({
            "arg_int": 42,
            "arg_float": 3.14,
            "arg_bool": True,
            "arg_string": "hello",
            "pc": 0x1234  # Should be formatted as pointer
        })
        
        builder.end_slice(thread, 2000)
        
        expected = """packet {
  track_descriptor {
    uuid: 1
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  track_descriptor {
    uuid: 2
    thread {
      pid: 1234
      tid: 1
      thread_name: "TestThread"
    }
    parent_uuid: 1
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 291
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
      int_value: 4660
      name: "pc"
    }
    type: TYPE_SLICE_BEGIN
    track_uuid: 2
    name: "test_function"
  }
}
packet {
  timestamp: 2000
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_SLICE_END
    track_uuid: 2
  }
}
"""
        assert to_textproto(builder) == expected
    
    def test_flow_events(self):
        """Test flow events connecting different threads."""
        builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
        thread1 = builder.add_thread("Producer")
        thread2 = builder.add_thread("Consumer")
        
        flow_id = 12345
        
        builder.add_flow(thread1, "Send", 1000, flow_id)
        builder.add_flow(thread2, "Receive", 2000, flow_id, terminating=True)
        
        expected = """packet {
  track_descriptor {
    uuid: 1
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  track_descriptor {
    uuid: 2
    thread {
      pid: 1234
      tid: 1
      thread_name: "Producer"
    }
    parent_uuid: 1
  }
}
packet {
  track_descriptor {
    uuid: 3
    thread {
      pid: 1234
      tid: 2
      thread_name: "Consumer"
    }
    parent_uuid: 1
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_INSTANT
    track_uuid: 2
    name: "Send"
    flow_ids: 12345
  }
}
packet {
  timestamp: 2000
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_INSTANT
    track_uuid: 3
    name: "Receive"
    terminating_flow_ids: 12345
  }
}
"""
        assert to_textproto(builder) == expected
    
    def test_nested_slices(self):
        """Test nested slice events."""
        builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
        thread = builder.add_thread("TestThread")
        
        builder.begin_slice(thread, "outer_function", 1000)
        builder.begin_slice(thread, "inner_function", 1100)
        builder.end_slice(thread, 1200)
        builder.end_slice(thread, 1300)
        
        expected = """packet {
  track_descriptor {
    uuid: 1
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  track_descriptor {
    uuid: 2
    thread {
      pid: 1234
      tid: 1
      thread_name: "TestThread"
    }
    parent_uuid: 1
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_SLICE_BEGIN
    track_uuid: 2
    name: "outer_function"
  }
}
packet {
  timestamp: 1100
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_SLICE_BEGIN
    track_uuid: 2
    name: "inner_function"
  }
}
packet {
  timestamp: 1200
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_SLICE_END
    track_uuid: 2
  }
}
packet {
  timestamp: 1300
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_SLICE_END
    track_uuid: 2
  }
}
"""
        assert to_textproto(builder) == expected
    
    def test_structured_annotations(self):
        """Test structured annotations with nested groups."""
        builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
        thread = builder.add_thread("TestThread")
        
        event = builder.begin_slice(thread, "cpu_instruction", 1000)
        
        with event.annotation("registers") as regs:
            regs.integer("A", 0x12)
            regs.integer("B", 0x34)
            regs.string("PC", "0x1234")  # Pointers stored as hex strings
            regs.string("SP", "0x8000")
        
        with event.annotation("flags") as flags:
            flags.bool("zero", True)
            flags.bool("carry", False)
        
        builder.end_slice(thread, 1100)
        
        expected = """packet {
  track_descriptor {
    uuid: 1
    process {
      pid: 1234
      process_name: "TestProcess"
    }
  }
}
packet {
  track_descriptor {
    uuid: 2
    thread {
      pid: 1234
      tid: 1
      thread_name: "TestThread"
    }
    parent_uuid: 1
  }
}
packet {
  timestamp: 1000
  trusted_packet_sequence_id: 291
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
        string_value: "0x1234"
        name: "PC"
      }
      dict_entries {
        string_value: "0x8000"
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
  trusted_packet_sequence_id: 291
  track_event {
    type: TYPE_SLICE_END
    track_uuid: 2
  }
}
"""
        assert to_textproto(builder) == expected
    
    def test_multiple_threads(self):
        """Test trace with multiple threads."""
        builder = PerfettoTraceBuilder("TestProcess", encoding="inline")
        
        threads = []
        for i in range(3):
            threads.append(builder.add_thread(f"Thread{i}"))
        
        # Add events to different threads
        builder.add_instant_event(threads[0], "event0", 1000)
        builder.add_instant_event(threads[1], "event1", 1100)
        builder.add_instant_event(threads[2], "event2", 1200)
        
        # Verify structure
        textproto = to_textproto(builder)
        
        # Should have process + 3 threads + 3 events = 7 packets
        assert textproto.count("packet {") == 7
        assert "Thread0" in textproto
        assert "Thread1" in textproto
        assert "Thread2" in textproto
        assert "event0" in textproto
        assert "event1" in textproto
        assert "event2" in textproto
