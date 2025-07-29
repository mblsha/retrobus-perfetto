#!/usr/bin/env python3
"""
Perfetto Trace Comparator - Compare execution and memory traces from two Perfetto files

This tool compares two Perfetto traces that should represent the same execution,
extracting events from the "Execution" and "Memory_Internal" timelines and comparing
their debug annotations. Memory comparison focuses on offset, value, and pc attributes.

Usage:
    ./perfetto_trace_compare.py <trace1.perfetto> <trace2.perfetto> [--verbose] [--skip-memory]
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Iterator
import difflib

# Import perfetto protobuf definitions
sys.path.append(str(Path(__file__).parent.parent / "py"))
from retrobus_perfetto.proto import perfetto_pb2

class ExecutionEvent:
    """Represents a single execution event with its annotations"""
    def __init__(self, name: str, timestamp: int, annotations: Dict[str, str]):
        self.name = name
        self.timestamp = timestamp
        self.annotations = annotations
    
    def annotation_string(self) -> str:
        """Convert annotations to a deterministic string for comparison"""
        # Sort keys to ensure consistent ordering
        sorted_items = sorted(self.annotations.items())
        return "; ".join(f"{k}={v}" for k, v in sorted_items)
    
    def normalized_annotation_string(self) -> str:
        """Convert annotations to normalized string for comparison (handles hex format differences)"""
        normalized = {}
        for k, v in self.annotations.items():
            # Normalize hex values (remove 0x prefix and uppercase)
            if isinstance(v, str) and v.startswith("0x"):
                # Convert "0x0F10C2" to "F10C2" (remove leading zeros)
                normalized[k] = v[2:].upper().lstrip("0") or "0"
            else:
                normalized[k] = v
        sorted_items = sorted(normalized.items())
        return "; ".join(f"{k}={v}" for k, v in sorted_items)

class MemoryEvent:
    """Represents a single memory event with its annotations"""
    def __init__(self, name: str, timestamp: int, annotations: Dict[str, str]):
        self.name = name
        self.timestamp = timestamp
        self.annotations = annotations
    
    def annotation_string(self) -> str:
        """Convert annotations to a deterministic string for comparison"""
        # Sort keys to ensure consistent ordering
        sorted_items = sorted(self.annotations.items())
        return "; ".join(f"{k}={v}" for k, v in sorted_items)

class PerfettoTraceComparator:
    """Compares two Perfetto traces focusing on execution and memory events"""
    
    def __init__(self, trace1_path: Path, trace2_path: Path):
        self.trace1_path = trace1_path
        self.trace2_path = trace2_path
        self.trace1_events: List[ExecutionEvent] = []
        self.trace2_events: List[ExecutionEvent] = []
    
    def load_trace(self, trace_path: Path) -> perfetto_pb2.Trace:
        """Load a Perfetto trace from file"""
        trace = perfetto_pb2.Trace()
        with open(trace_path, 'rb') as f:
            trace.ParseFromString(f.read())
        return trace
    
    def extract_execution_events(self, trace: perfetto_pb2.Trace) -> List[ExecutionEvent]:
        """Extract all Exec@ events from the Execution thread"""
        events = []
        
        # First, build a map of track UUIDs to track names
        track_names = {}
        for packet in trace.packet:
            if packet.HasField('track_descriptor'):
                track_names[packet.track_descriptor.uuid] = packet.track_descriptor.name
        
        # Find the Execution thread UUID
        execution_uuid = None
        
        # First try to find by name
        for uuid, name in track_names.items():
            if name == "Execution":
                execution_uuid = uuid
                break
        
        # If not found by name, try to find by event content
        if not execution_uuid:
            # Sample events from each track to find Exec@ events
            track_samples = {}
            for packet in trace.packet:
                if packet.HasField('track_event') and packet.track_event.HasField('name'):
                    uuid = packet.track_event.track_uuid
                    if uuid not in track_samples:
                        track_samples[uuid] = []
                    if len(track_samples[uuid]) < 10:
                        track_samples[uuid].append(packet.track_event.name)
            
            # Find track with Exec@ events
            for uuid, samples in track_samples.items():
                if any(name.startswith("Exec@") for name in samples):
                    execution_uuid = uuid
                    print(f"  Note: Found Exec@ events on track {uuid} (thread name: '{track_names.get(uuid, 'unnamed')}')")
                    break
        
        if not execution_uuid:
            raise ValueError("No 'Execution' thread or Exec@ events found in trace")
        
        # Extract events from the Execution thread
        for packet in trace.packet:
            if packet.HasField('track_event'):
                event = packet.track_event
                
                # Check if this event is on the Execution thread
                if event.track_uuid != execution_uuid:
                    continue
                
                # Check if this is an instant event (not slice begin/end)
                if event.type != perfetto_pb2.TrackEvent.TYPE_INSTANT:
                    continue
                
                # Get event name
                event_name = event.name if event.HasField('name') else ""
                
                # Filter for Exec@ events
                if not event_name.startswith("Exec@"):
                    continue
                
                # Extract annotations
                annotations = {}
                for annotation in event.debug_annotations:
                    # Handle different annotation value types
                    ann_name = annotation.name if annotation.HasField('name') else ""
                    
                    if annotation.HasField('string_value'):
                        ann_value = annotation.string_value
                    elif annotation.HasField('int_value'):
                        ann_value = str(annotation.int_value)
                    elif annotation.HasField('uint_value'):
                        ann_value = str(annotation.uint_value)
                    elif annotation.HasField('bool_value'):
                        ann_value = str(annotation.bool_value).lower()
                    elif annotation.HasField('double_value'):
                        ann_value = str(annotation.double_value)
                    elif annotation.HasField('pointer_value'):
                        ann_value = f"0x{annotation.pointer_value:X}"
                    else:
                        ann_value = "<unknown>"
                    
                    if ann_name:
                        annotations[ann_name] = ann_value
                
                events.append(ExecutionEvent(
                    name=event_name,
                    timestamp=packet.timestamp,
                    annotations=annotations
                ))
        
        # Sort by timestamp to ensure correct ordering
        events.sort(key=lambda e: e.timestamp)
        return events
    
    def extract_memory_internal_events(self, trace: perfetto_pb2.Trace) -> List[MemoryEvent]:
        """Extract all events from the Memory_Internal thread"""
        events = []
        
        # First, build a map of track UUIDs to track names
        track_names = {}
        for packet in trace.packet:
            if packet.HasField('track_descriptor'):
                track_names[packet.track_descriptor.uuid] = packet.track_descriptor.name
        
        # Debug: print track info if verbose
        if len(track_names) < 20:  # Only print if reasonable number
            has_named_tracks = any(name for name in track_names.values())
            if not has_named_tracks:
                print(f"  Note: Found {len(track_names)} unnamed tracks")
        
        # Find the Memory_Internal thread UUID
        memory_internal_uuid = None
        
        for uuid, name in track_names.items():
            if name == "Memory_Internal":
                memory_internal_uuid = uuid
                break
        
        if not memory_internal_uuid:
            # Check if track 5 has memory events (based on common pattern)
            if 5 in track_names:
                # Quick check for events on track 5
                sample_count = 0
                for packet in trace.packet:
                    if packet.HasField('track_event') and packet.track_event.track_uuid == 5:
                        if packet.track_event.type == perfetto_pb2.TrackEvent.TYPE_INSTANT:
                            sample_count += 1
                            if sample_count >= 10:
                                break
                
                if sample_count > 0:
                    memory_internal_uuid = 5
                else:
                    return []
            else:
                return []
        
        # Extract ALL events from the Memory_Internal thread
        for packet in trace.packet:
            if packet.HasField('track_event'):
                event = packet.track_event
                
                # Check if this event is on the Memory_Internal thread
                if event.track_uuid != memory_internal_uuid:
                    continue
                
                # Check if this is an instant event (not slice begin/end)
                if event.type != perfetto_pb2.TrackEvent.TYPE_INSTANT:
                    continue
                
                # Get event name
                event_name = event.name if event.HasField('name') else ""
                
                # Extract annotations
                annotations = {}
                for annotation in event.debug_annotations:
                    # Handle different annotation value types
                    ann_name = annotation.name if annotation.HasField('name') else ""
                    
                    if annotation.HasField('string_value'):
                        ann_value = annotation.string_value
                    elif annotation.HasField('int_value'):
                        ann_value = str(annotation.int_value)
                    elif annotation.HasField('uint_value'):
                        ann_value = str(annotation.uint_value)
                    elif annotation.HasField('bool_value'):
                        ann_value = str(annotation.bool_value).lower()
                    elif annotation.HasField('double_value'):
                        ann_value = str(annotation.double_value)
                    elif annotation.HasField('pointer_value'):
                        ann_value = f"0x{annotation.pointer_value:X}"
                    else:
                        ann_value = "<unknown>"
                    
                    if ann_name:
                        annotations[ann_name] = ann_value
                
                events.append(MemoryEvent(
                    name=event_name,
                    timestamp=packet.timestamp,
                    annotations=annotations
                ))
        
        # Sort by timestamp to ensure correct ordering
        events.sort(key=lambda e: e.timestamp)
        return events
    
    def extract_memory_external_events(self, trace: perfetto_pb2.Trace) -> List[MemoryEvent]:
        """Extract all events from the Memory_External thread"""
        events = []
        
        # First, build a map of track UUIDs to track names
        track_names = {}
        for packet in trace.packet:
            if packet.HasField('track_descriptor'):
                track_names[packet.track_descriptor.uuid] = packet.track_descriptor.name
        
        # Debug: print track info if verbose
        if len(track_names) < 20:  # Only print if reasonable number
            has_named_tracks = any(name for name in track_names.values())
            if not has_named_tracks:
                print(f"  Note: Found {len(track_names)} unnamed tracks")
        
        # Find the Memory_External thread UUID
        memory_external_uuid = None
        
        for uuid, name in track_names.items():
            if name == "Memory_External":
                memory_external_uuid = uuid
                break
        
        if not memory_external_uuid:
            # Check if track 6 has memory events (based on common pattern)
            if 6 in track_names:
                # Quick check for events on track 6
                sample_count = 0
                for packet in trace.packet:
                    if packet.HasField('track_event') and packet.track_event.track_uuid == 6:
                        if packet.track_event.type == perfetto_pb2.TrackEvent.TYPE_INSTANT:
                            sample_count += 1
                            if sample_count >= 10:
                                break
                
                if sample_count > 0:
                    memory_external_uuid = 6
                else:
                    return []
            else:
                return []
        
        # Extract ALL events from the Memory_External thread
        for packet in trace.packet:
            if packet.HasField('track_event'):
                event = packet.track_event
                
                # Check if this event is on the Memory_External thread
                if event.track_uuid != memory_external_uuid:
                    continue
                
                # Check if this is an instant event (not slice begin/end)
                if event.type != perfetto_pb2.TrackEvent.TYPE_INSTANT:
                    continue
                
                # Get event name
                event_name = event.name if event.HasField('name') else ""
                
                # Extract annotations
                annotations = {}
                for annotation in event.debug_annotations:
                    # Handle different annotation value types
                    ann_name = annotation.name if annotation.HasField('name') else ""
                    
                    if annotation.HasField('string_value'):
                        ann_value = annotation.string_value
                    elif annotation.HasField('int_value'):
                        ann_value = str(annotation.int_value)
                    elif annotation.HasField('uint_value'):
                        ann_value = str(annotation.uint_value)
                    elif annotation.HasField('bool_value'):
                        ann_value = str(annotation.bool_value).lower()
                    elif annotation.HasField('double_value'):
                        ann_value = str(annotation.double_value)
                    elif annotation.HasField('pointer_value'):
                        ann_value = f"0x{annotation.pointer_value:X}"
                    else:
                        ann_value = "<unknown>"
                    
                    if ann_name:
                        annotations[ann_name] = ann_value
                
                events.append(MemoryEvent(
                    name=event_name,
                    timestamp=packet.timestamp,
                    annotations=annotations
                ))
        
        # Sort by timestamp to ensure correct ordering
        events.sort(key=lambda e: e.timestamp)
        return events
    
    def normalize_memory_events(self, events: List[MemoryEvent]) -> List[MemoryEvent]:
        """Normalize memory events by breaking down multi-byte events into single-byte events"""
        normalized = []
        
        for event in events:
            annotations = event.annotations
            
            # Check if this is a multi-byte event
            if 'size' in annotations and int(annotations.get('size', '1')) > 1:
                # Multi-byte event - break it down
                size = int(annotations['size'])
                base_addr = annotations.get('address', annotations.get('addr', '0x0'))
                if base_addr.startswith('0x'):
                    base_addr = int(base_addr, 16)
                else:
                    base_addr = int(base_addr)
                
                # Extract value
                value_str = annotations.get('value', '0x0')
                if value_str.startswith('0x'):
                    value = int(value_str, 16)
                else:
                    value = int(value_str)
                
                # Break down into bytes (little-endian)
                for i in range(size):
                    byte_value = (value >> (i * 8)) & 0xFF
                    byte_addr = base_addr + i
                    
                    # Create normalized single-byte event
                    byte_annotations = {
                        'addr': f"0x{byte_addr:06X}",
                        'value': f"0x{byte_value:02X}"
                    }
                    
                    # Copy other attributes
                    if 'pc' in annotations:
                        byte_annotations['pc'] = annotations['pc']
                    
                    normalized.append(MemoryEvent(
                        name=event.name,
                        timestamp=event.timestamp,
                        annotations=byte_annotations
                    ))
            else:
                # Single-byte event - just normalize attribute names
                norm_annotations = {}
                
                # Normalize address attribute
                if 'address' in annotations:
                    norm_annotations['addr'] = annotations['address']
                elif 'addr' in annotations:
                    norm_annotations['addr'] = annotations['addr']
                
                # Copy value and pc
                if 'value' in annotations:
                    norm_annotations['value'] = annotations['value']
                if 'pc' in annotations:
                    norm_annotations['pc'] = annotations['pc']
                
                normalized.append(MemoryEvent(
                    name=event.name,
                    timestamp=event.timestamp,
                    annotations=norm_annotations
                ))
        
        return normalized
    
    def compare_events(self) -> Iterator[Tuple[int, Optional[ExecutionEvent], Optional[ExecutionEvent], Optional[str]]]:
        """
        Compare events from both traces, yielding differences.
        
        Yields:
            (index, event1, event2, error_message)
        """
        max_len = max(len(self.trace1_events), len(self.trace2_events))
        
        for i in range(max_len):
            event1 = self.trace1_events[i] if i < len(self.trace1_events) else None
            event2 = self.trace2_events[i] if i < len(self.trace2_events) else None
            
            # Check for length mismatch
            if event1 is None:
                yield (i, event1, event2, "Trace 1 ended but Trace 2 has more events")
                return
            elif event2 is None:
                yield (i, event1, event2, "Trace 2 ended but Trace 1 has more events")
                return
            
            # Compare event names
            if event1.name != event2.name:
                yield (i, event1, event2, f"Event name mismatch: '{event1.name}' vs '{event2.name}'")
                return
            
            # Compare annotations
            ann_str1 = event1.annotation_string()
            ann_str2 = event2.annotation_string()
            
            if ann_str1 != ann_str2:
                yield (i, event1, event2, "Annotation mismatch")
                return
    
    def compare_memory_events(self, event_list1: List[MemoryEvent], event_list2: List[MemoryEvent], 
                            memory_type: str = "Memory") -> Iterator[Tuple[int, Optional[MemoryEvent], Optional[MemoryEvent], Optional[str]]]:
        """
        Compare memory events from both traces.
        
        Args:
            event_list1: Memory events from trace 1
            event_list2: Memory events from trace 2
            memory_type: Type of memory for error messages (e.g., "Memory_Internal", "Memory_External")
        
        Yields:
            (index, event1, event2, error_message)
        """
        max_len = max(len(event_list1), len(event_list2))
        
        for i in range(max_len):
            event1 = event_list1[i] if i < len(event_list1) else None
            event2 = event_list2[i] if i < len(event_list2) else None
            
            # Check for length mismatch
            if event1 is None:
                yield (i, event1, event2, f"Trace 1 ended but Trace 2 has more {memory_type} events")
                return
            elif event2 is None:
                yield (i, event1, event2, f"Trace 2 ended but Trace 1 has more {memory_type} events")
                return
            
            # Get key attributes based on memory type
            if memory_type == "Memory_Internal":
                # Memory_Internal uses 'offset'
                addr_key = 'offset'
                addr1 = event1.annotations.get(addr_key, 'N/A')
                addr2 = event2.annotations.get(addr_key, 'N/A')
            else:
                # Memory_External uses 'addr'
                addr_key = 'addr'
                addr1 = event1.annotations.get(addr_key, 'N/A')
                addr2 = event2.annotations.get(addr_key, 'N/A')
            
            value1 = event1.annotations.get('value', 'N/A')
            value2 = event2.annotations.get('value', 'N/A')
            pc1 = event1.annotations.get('pc', 'N/A')
            pc2 = event2.annotations.get('pc', 'N/A')
            
            # Check if key attributes match
            if addr1 != addr2:
                yield (i, event1, event2, f"{memory_type} {addr_key} mismatch: '{addr1}' vs '{addr2}'")
                return
            
            if value1 != value2:
                yield (i, event1, event2, f"{memory_type} value mismatch at {addr_key} {addr1}: '{value1}' vs '{value2}'")
                return
            
            if pc1 != pc2:
                yield (i, event1, event2, f"PC mismatch for {memory_type} write at {addr_key} {addr1}: '{pc1}' vs '{pc2}'")
                return
    
    def run_comparison(self, verbose: bool = False, skip_memory: bool = False) -> bool:
        """
        Run the full comparison process.
        
        Returns:
            True if traces match, False otherwise
        """
        print(f"Loading trace 1: {self.trace1_path}")
        trace1 = self.load_trace(self.trace1_path)
        self.trace1_events = self.extract_execution_events(trace1)
        print(f"  Found {len(self.trace1_events)} Exec@ events")
        
        print(f"Loading trace 2: {self.trace2_path}")
        trace2 = self.load_trace(self.trace2_path)
        self.trace2_events = self.extract_execution_events(trace2)
        print(f"  Found {len(self.trace2_events)} Exec@ events")
        
        print("\nComparing execution traces...")
        
        # Compare execution events
        execution_match = True
        for i, event1, event2, error in self.compare_events():
            if error:
                print(f"\n❌ Difference found at event #{i}:")
                print(f"   Error: {error}")
                
                # Show execution flow context (up to 5 previous PCs)
                print("\n   Execution flow context:")
                context_size = min(5, i)
                for j in range(i - context_size, i + 1):
                    if j >= 0 and j < len(self.trace1_events):
                        pc1 = self.trace1_events[j].annotations.get('pc', 'N/A')
                        pc2 = self.trace2_events[j].annotations.get('pc', 'N/A') if j < len(self.trace2_events) else 'N/A'
                        op1 = self.trace1_events[j].annotations.get('opcode', 'N/A')
                        op2 = self.trace2_events[j].annotations.get('opcode', 'N/A') if j < len(self.trace2_events) else 'N/A'
                        marker = " -> " if j == i else "    "
                        # Show PC and opcode, marking differences
                        pc_match = pc1 == pc2
                        op_match = op1 == op2
                        print(f"   {marker}Event #{j}: PC={pc1} opcode={op1} {'✓' if pc_match and op_match else '✗' if not pc_match or not op_match else ''}")
                
                if event1:
                    print(f"\n   Trace 1 - {event1.name}:")
                    print(f"   {event1.annotation_string()}")
                
                if event2:
                    print(f"\n   Trace 2 - {event2.name}:")
                    print(f"   {event2.annotation_string()}")
                
                # Show detailed diff if annotation mismatch
                if "Annotation mismatch" in error and event1 and event2:
                    print("\n   Detailed differences:")
                    lines1 = event1.annotation_string().split("; ")
                    lines2 = event2.annotation_string().split("; ")
                    
                    for line in difflib.unified_diff(lines1, lines2, fromfile="Trace 1", tofile="Trace 2", lineterm=""):
                        print(f"   {line}")
                
                execution_match = False
                break
            
            if verbose and i % 1000 == 0:
                print(f"  Compared {i} events...")
        
        if execution_match:
            print(f"\n✅ Execution traces match! ({len(self.trace1_events)} events compared)")
        
        # Compare memory events if requested (always run unless explicitly skipped)
        if not skip_memory:
            overall_memory_match = True
            
            # Compare Memory_Internal events
            print("\nExtracting Memory_Internal events...")
            trace1_memory_internal = self.extract_memory_internal_events(trace1)
            print(f"  Trace 1: Found {len(trace1_memory_internal)} Memory_Internal events")
            
            trace2_memory_internal = self.extract_memory_internal_events(trace2)
            print(f"  Trace 2: Found {len(trace2_memory_internal)} Memory_Internal events")
            
            if len(trace1_memory_internal) > 0 or len(trace2_memory_internal) > 0:
                print("\nComparing Memory_Internal events...")
                
                memory_internal_match = True
                for i, event1, event2, error in self.compare_memory_events(trace1_memory_internal, trace2_memory_internal, "Memory_Internal"):
                    if error:
                        print(f"\n❌ Memory_Internal difference found at event #{i}:")
                        print(f"   Error: {error}")
                        
                        # Show context of previous memory writes
                        print("\n   Previous memory writes:")
                        context_size = min(5, i)
                        for j in range(i - context_size, i + 1):
                            if j >= 0 and j < len(trace1_memory_internal):
                                offset1 = trace1_memory_internal[j].annotations.get('offset', 'N/A')
                                value1 = trace1_memory_internal[j].annotations.get('value', 'N/A')
                                pc1 = trace1_memory_internal[j].annotations.get('pc', 'N/A')
                                
                                offset2 = 'N/A'
                                value2 = 'N/A'
                                pc2 = 'N/A'
                                if j < len(trace2_memory_internal):
                                    offset2 = trace2_memory_internal[j].annotations.get('offset', 'N/A')
                                    value2 = trace2_memory_internal[j].annotations.get('value', 'N/A')
                                    pc2 = trace2_memory_internal[j].annotations.get('pc', 'N/A')
                                
                                marker = " -> " if j == i else "    "
                                match = offset1 == offset2 and value1 == value2 and pc1 == pc2
                                print(f"   {marker}Event #{j}: offset={offset1} value={value1} pc={pc1} {'✓' if match else '✗'}")
                        
                        if event1:
                            print(f"\n   Trace 1 - {event1.name}:")
                            print(f"   {event1.annotation_string()}")
                        
                        if event2:
                            print(f"\n   Trace 2 - {event2.name}:")
                            print(f"   {event2.annotation_string()}")
                        
                        memory_internal_match = False
                        overall_memory_match = False
                        break
                    
                    if verbose and i % 1000 == 0:
                        print(f"  Compared {i} Memory_Internal events...")
                
                if memory_internal_match:
                    print(f"\n✅ Memory_Internal traces match! ({len(trace1_memory_internal)} events compared)")
            else:
                print("\n  No Memory_Internal events to compare")
            
            # Compare Memory_External events
            print("\nExtracting Memory_External events...")
            trace1_memory_external_raw = self.extract_memory_external_events(trace1)
            print(f"  Trace 1: Found {len(trace1_memory_external_raw)} Memory_External events (raw)")
            
            trace2_memory_external_raw = self.extract_memory_external_events(trace2)
            print(f"  Trace 2: Found {len(trace2_memory_external_raw)} Memory_External events (raw)")
            
            if len(trace1_memory_external_raw) > 0 or len(trace2_memory_external_raw) > 0:
                # Normalize multi-byte events into single-byte events
                print("\nNormalizing Memory_External events...")
                trace1_memory_external = self.normalize_memory_events(trace1_memory_external_raw)
                trace2_memory_external = self.normalize_memory_events(trace2_memory_external_raw)
                print(f"  Trace 1: {len(trace1_memory_external)} normalized events")
                print(f"  Trace 2: {len(trace2_memory_external)} normalized events")
                
                print("\nComparing Memory_External events...")
                
                memory_external_match = True
                for i, event1, event2, error in self.compare_memory_events(trace1_memory_external, trace2_memory_external, "Memory_External"):
                    if error:
                        print(f"\n❌ Memory_External difference found at event #{i}:")
                        print(f"   Error: {error}")
                        
                        # Show context of previous memory writes
                        print("\n   Previous memory writes:")
                        context_size = min(5, i)
                        for j in range(i - context_size, i + 1):
                            if j >= 0 and j < len(trace1_memory_external):
                                addr1 = trace1_memory_external[j].annotations.get('addr', 'N/A')
                                value1 = trace1_memory_external[j].annotations.get('value', 'N/A')
                                pc1 = trace1_memory_external[j].annotations.get('pc', 'N/A')
                                
                                addr2 = 'N/A'
                                value2 = 'N/A'
                                pc2 = 'N/A'
                                if j < len(trace2_memory_external):
                                    addr2 = trace2_memory_external[j].annotations.get('addr', 'N/A')
                                    value2 = trace2_memory_external[j].annotations.get('value', 'N/A')
                                    pc2 = trace2_memory_external[j].annotations.get('pc', 'N/A')
                                
                                marker = " -> " if j == i else "    "
                                match = addr1 == addr2 and value1 == value2 and pc1 == pc2
                                print(f"   {marker}Event #{j}: addr={addr1} value={value1} pc={pc1} {'✓' if match else '✗'}")
                        
                        if event1:
                            print(f"\n   Trace 1 - {event1.name}:")
                            print(f"   {event1.annotation_string()}")
                        
                        if event2:
                            print(f"\n   Trace 2 - {event2.name}:")
                            print(f"   {event2.annotation_string()}")
                        
                        memory_external_match = False
                        overall_memory_match = False
                        break
                    
                    if verbose and i % 1000 == 0:
                        print(f"  Compared {i} Memory_External events...")
                
                if memory_external_match:
                    print(f"\n✅ Memory_External traces match! ({len(trace1_memory_external)} events compared)")
            else:
                print("\n  No Memory_External events to compare")
            
            return execution_match and overall_memory_match
        else:
            # Memory comparison was skipped
            return execution_match

def main():
    parser = argparse.ArgumentParser(
        description="Compare two Perfetto traces for execution and memory differences"
    )
    parser.add_argument("trace1", type=Path, help="First Perfetto trace file")
    parser.add_argument("trace2", type=Path, help="Second Perfetto trace file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show progress during comparison")
    parser.add_argument("--skip-memory", action="store_true", help="Skip memory event comparison")
    
    args = parser.parse_args()
    
    # Validate input files
    if not args.trace1.exists():
        print(f"Error: Trace file not found: {args.trace1}")
        sys.exit(1)
    
    if not args.trace2.exists():
        print(f"Error: Trace file not found: {args.trace2}")
        sys.exit(1)
    
    # Run comparison
    comparator = PerfettoTraceComparator(args.trace1, args.trace2)
    
    try:
        matches = comparator.run_comparison(args.verbose, args.skip_memory)
        sys.exit(0 if matches else 1)
    except Exception as e:
        print(f"\nError during comparison: {e}")
        sys.exit(2)

if __name__ == '__main__':
    main()