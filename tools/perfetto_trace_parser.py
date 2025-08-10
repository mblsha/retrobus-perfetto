#!/usr/bin/env python3
"""
Generic Perfetto Trace Parser - Extract structured data from Perfetto protobuf traces

This tool provides utilities for parsing Perfetto traces without requiring the full
Perfetto SDK. It can extract common patterns and data from CPU emulator traces.

Usage:
    ./perfetto_trace_parser.py <trace_file> --pattern pc --format hex
    ./perfetto_trace_parser.py <trace_file> --dump-strings
    ./perfetto_trace_parser.py <trace_file> --find-pattern "instruction"
"""

import struct
import argparse
from collections import Counter
from pathlib import Path


class PerfettoTraceParser:
    """Generic parser for Perfetto trace files"""
    
    def __init__(self, trace_file):
        self.trace_file = Path(trace_file)
        self.data = None
        
    def load(self):
        """Load trace file into memory"""
        print(f"Loading {self.trace_file} ({self.trace_file.stat().st_size:,} bytes)...")
        with open(self.trace_file, 'rb') as f:
            self.data = f.read()
        return len(self.data)
    
    def read_varint(self, pos):
        """Read a protobuf varint from data starting at pos"""
        result = 0
        shift = 0
        while pos < len(self.data):
            byte = self.data[pos]
            pos += 1
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result, pos
    
    def find_strings(self, min_length=4):
        """Extract all strings from the trace"""
        strings = []
        current = []
        
        for byte in self.data:
            if 32 <= byte <= 126:  # Printable ASCII
                current.append(chr(byte))
            else:
                if len(current) >= min_length:
                    strings.append(''.join(current))
                current = []
        
        if len(current) >= min_length:
            strings.append(''.join(current))
        
        return strings
    
    def find_pattern_context(self, pattern, context_bytes=20):
        """Find a pattern and return surrounding context"""
        contexts = []
        
        if isinstance(pattern, str):
            pattern = pattern.encode()
        
        pos = 0
        while True:
            pos = self.data.find(pattern, pos)
            if pos == -1:
                break
            
            start = max(0, pos - context_bytes)
            end = min(len(self.data), pos + len(pattern) + context_bytes)
            
            contexts.append({
                'position': pos,
                'pattern': pattern,
                'before': self.data[start:pos],
                'after': self.data[pos + len(pattern):end]
            })
            
            pos += 1
        
        return contexts
    
    def extract_numbers(self, pattern_before, num_bytes, endian='<'):
        """Extract numbers that appear after a specific pattern"""
        numbers = Counter()
        
        if isinstance(pattern_before, str):
            pattern_before = pattern_before.encode()
        
        pos = 0
        while True:
            pos = self.data.find(pattern_before, pos)
            if pos == -1:
                break
            
            num_start = pos + len(pattern_before)
            if num_start + num_bytes <= len(self.data):
                num_data = self.data[num_start:num_start + num_bytes]
                
                if num_bytes == 1:
                    num = struct.unpack('B', num_data)[0]
                elif num_bytes == 2:
                    num = struct.unpack(f'{endian}H', num_data)[0]
                elif num_bytes == 4:
                    num = struct.unpack(f'{endian}I', num_data)[0]
                elif num_bytes == 8:
                    num = struct.unpack(f'{endian}Q', num_data)[0]
                else:
                    # For 3 bytes or other sizes
                    num = int.from_bytes(num_data, byteorder='little' if endian == '<' else 'big')
                
                numbers[num] += 1
            
            pos += 1
        
        return numbers
    
    def analyze_protobuf_structure(self):
        """Basic protobuf structure analysis"""
        field_types = Counter()
        field_numbers = Counter()
        
        pos = 0
        while pos < len(self.data) - 1:
            try:
                # Try to read a varint (field header)
                field_header, new_pos = self.read_varint(pos)
                if new_pos > pos:
                    field_number = field_header >> 3
                    wire_type = field_header & 0x7
                    
                    if 0 < field_number < 1000:  # Reasonable field number
                        field_numbers[field_number] += 1
                        field_types[wire_type] += 1
                    
                    pos = new_pos
                else:
                    pos += 1
            except (IndexError, ValueError):
                pos += 1
        
        return field_numbers, field_types
    
    def hexdump(self, offset, length=256):
        """Generate hexdump of a region"""
        lines = []
        for i in range(0, length, 16):
            if offset + i >= len(self.data):
                break
            
            hex_bytes = ' '.join(f'{b:02x}' for b in self.data[offset+i:offset+i+16])
            ascii_bytes = ''.join(
                chr(b) if 32 <= b <= 126 else '.' 
                for b in self.data[offset+i:offset+i+16]
            )
            
            lines.append(f"{offset+i:08x}  {hex_bytes:<48}  {ascii_bytes}")
        
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Parse and analyze Perfetto trace files"
    )
    parser.add_argument("trace_file", help="Path to Perfetto trace file")
    parser.add_argument("--dump-strings", action="store_true", 
                        help="Dump all strings found in trace")
    parser.add_argument("--find-pattern", help="Find and show context for pattern")
    parser.add_argument("--extract-numbers", help="Pattern before numbers to extract")
    parser.add_argument("--num-bytes", type=int, default=2, 
                        help="Number of bytes for number extraction")
    parser.add_argument("--analyze-proto", action="store_true",
                        help="Analyze protobuf structure")
    parser.add_argument("--hexdump", type=lambda x: int(x, 0),
                        help="Hexdump from offset (hex or decimal)")
    
    args = parser.parse_args()
    
    # Create parser and load trace
    parser = PerfettoTraceParser(args.trace_file)
    parser.load()
    
    # Execute requested operations
    if args.dump_strings:
        print("\nStrings found in trace:")
        print("-" * 60)
        strings = parser.find_strings()
        string_counts = Counter(strings)
        for s, count in string_counts.most_common(50):
            if count > 1:
                print(f"{count:5d}x: {s[:60]}")
            else:
                print(f"     1x: {s[:60]}")
    
    if args.find_pattern:
        print(f"\nSearching for pattern: {args.find_pattern}")
        print("-" * 60)
        contexts = parser.find_pattern_context(args.find_pattern)
        print(f"Found {len(contexts)} occurrences")
        
        for i, ctx in enumerate(contexts[:10]):  # Show first 10
            print(f"\nOccurrence {i+1} at offset 0x{ctx['position']:08x}:")
            print(f"  Before: {ctx['before'].hex()}")
            print(f"  Pattern: {ctx['pattern'].hex()}")
            print(f"  After: {ctx['after'].hex()}")
    
    if args.extract_numbers:
        print(f"\nExtracting {args.num_bytes}-byte numbers after '{args.extract_numbers}'")
        print("-" * 60)
        numbers = parser.extract_numbers(args.extract_numbers, args.num_bytes)
        
        print(f"Found {len(numbers)} unique values")
        print("\nTop 20 most common:")
        for num, count in numbers.most_common(20):
            if args.num_bytes <= 4:
                print(f"  0x{num:0{args.num_bytes*2}x}: {count:6d} times")
            else:
                print(f"  {num}: {count:6d} times")
    
    if args.analyze_proto:
        print("\nProtobuf structure analysis:")
        print("-" * 60)
        field_nums, wire_types = parser.analyze_protobuf_structure()
        
        print("Most common field numbers:")
        for num, count in field_nums.most_common(10):
            print(f"  Field {num}: {count} times")
        
        print("\nWire types:")
        wire_names = {0: "Varint", 1: "64-bit", 2: "Length-delimited", 
                      5: "32-bit", 3: "Start group", 4: "End group"}
        for wtype, count in sorted(wire_types.items()):
            print(f"  Type {wtype} ({wire_names.get(wtype, 'Unknown')}): {count}")
    
    if args.hexdump is not None:
        print(f"\nHexdump from offset 0x{args.hexdump:08x}:")
        print("-" * 60)
        print(parser.hexdump(args.hexdump))


if __name__ == '__main__':
    main()