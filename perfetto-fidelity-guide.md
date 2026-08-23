# Perfetto fidelity guide

RetroBus intentionally carries a compact subset of the full Perfetto schema.
The subset now includes the fidelity mechanisms most useful to profilers and
trace converters while retaining Perfetto's exact upstream field numbers, wire
types, enum values, and packet-sequence interning rules. The compatibility test
suite compares those fields with a pinned full official Perfetto descriptor and
parses a representative trace through that full schema.

## Schema, builders, and policy are separate layers

- **Schema support** means a producer can represent a value losslessly on the
  wire. `proto/perfetto.proto` is the authority for the compact subset, and the
  generated Python, C++, and TypeScript bindings expose those fields directly.
- **Builder convenience** means the Python and C++ APIs automate IDs, interning,
  packet flags, and common validation. Direct protobuf users can choose other
  producer policies while emitting the same wire format.
- **Security and redaction policy belongs to the caller.** RetroBus does not
  silently remove source paths, build IDs, instruction addresses, pointer
  values, or metadata strings. Producers should redact, hash, omit, or gate
  sensitive values before passing them to the library. The library supplies
  fidelity mechanisms; it does not decide what is safe to disclose.

`DebugAnnotation.string_value` and `pointer_value` predate these additions and
remain supported. The new annotation work is recursive dictionary/array
encoding, type preservation throughout those structures, and interning of
repeated names and string values.

## Event categories

Categories repeat heavily in profiling traces. Interned
`EventCategory` entries keep strings such as `cuda`, `kernel`, and `runtime`
once per packet sequence while events carry small `category_iids` values.
Python event methods accept `categories=(...)` and both Python and C++ expose
`add_category`. Readers resolve categories with the sequence's incremental
state; merges keep each source's dictionaries isolated by remapping its trusted
packet sequence ID.

```python
event = builder.add_instant_event(
    lane, "launch", timestamp, categories=("cuda", "kernel")
)
event.add_category("profile")
```

## Merged sibling tracks for overlapping work

Perfetto can merge several physical backing tracks into one logical nestable
track. This is useful when GPU kernels overlap: assign each concurrent kernel
to a lane where slices remain properly nested, give every lane the same parent
and sibling merge key, and let Trace Processor/UI present a single logical
track.

```python
lane0 = builder.add_merged_track_lane("Kernel lane 0", "cuda-kernels")
lane1 = builder.add_merged_track_lane("Kernel lane 1", "cuda-kernels")
```

The general `add_track` API exposes the official
`SiblingMergeBehavior` enum and either the string or integer merge key. All
eligible siblings must use a compatible behavior and key; the convenience
method selects `SIBLING_MERGE_BEHAVIOR_BY_SIBLING_MERGE_KEY`.

## Recursive structured annotations

Mappings and sequences are encoded recursively through
`DebugAnnotation.dict_entries` and `array_values`; they are never converted to
display strings. Scalars retain their protobuf type:

- `bool` → `bool_value`
- signed `int` → `int_value`
- Python `UInt` / C++ unsigned values → `uint_value`
- `float` → `double_value`
- `str` → `string_value_iid` when interning is enabled
- Python `Pointer` / explicit C++ `add_pointer` → `pointer_value`

This preserves profiler metadata such as CUDA grid and block dimensions,
occupancy, launch flags, and nested per-device properties:

```python
from retrobus_perfetto import Pointer, UInt

event.add_annotations({
    "launch": {
        "grid": [UInt(128), UInt(2), UInt(1)],
        "block": [UInt(32), UInt(4), UInt(1)],
        "occupancy": 0.75,
        "cooperative": True,
        "stream": Pointer(0xFEED),
        "kernel": "vector_add",
    }
})
```

Python validates the entire object graph before changing the protobuf. Cycles,
non-string dictionary keys, unsupported objects, integer overflow, and nesting
beyond `annotation_max_depth` raise explicit errors and leave the event
unchanged. C++'s typed recursive builders cannot form object-graph cycles and
throw on nesting beyond 64 containers.

## Source locations and callstacks

`set_source_location` retains the existing inline form and, by default, interns
locations when writer interning is enabled. Repeated source/function/path
strings use the official `InternedData` tables.

There are two callstack forms:

- `set_inline_callstack` stores already-symbolized function/file/line frames on
  the event. It is straightforward for unique stacks.
- `set_callstack` interns mappings, raw build IDs, path components, source
  paths, function names, frames, and the bottom-to-top callstack. Mapping plus
  relative PC data makes native stacks suitable for symbolization and
  flamegraph-capable aggregation while staying compact when stacks repeat.

```python
from retrobus_perfetto import SourceLocation, StackFrame, StackMapping

mapping = StackMapping(
    path=("usr", "lib", "libcuda.so"),
    build_id=b"\x01\x02build",
    start=0x1000,
    end=0x9000,
)
event.set_source_location(SourceLocation("/src/cuda.cc", "launch", 88))
event.set_callstack([
    StackFrame(function_name="main"),
    StackFrame(
        function_name="launch",
        mapping=mapping,
        rel_pc=0x123,
        source_path="/src/cuda.cc",
        line_number=88,
    ),
])
```

`iter_resolved_track_events` is the lossless reader API: it reports the resolved
event name, categories, source location, mapping/build/path data, and callstack
without forcing native stacks into the less expressive inline representation.
The merge and SQLite oracle-index paths preserve and resolve the same tables.

## Chrome legacy event fidelity

`LegacyEvent` carries the official Chrome phase byte, duration and thread
duration, instruction delta, scoped/unscoped/local/global IDs, async-thread-time
flag, binding ID and enclosing flag, flow direction, instant scope, and PID/TID
overrides. It is intended for converters that must preserve uncommon or
source-specific Chrome JSON semantics exactly.

For common events, prefer native Perfetto concepts:

- Chrome `X`, `B`, and `E` → native slice begin/end events
- `i` → native instant events
- `C` → native counter tracks
- `s`, `t`, and `f` → native Perfetto flow IDs

Native events integrate more directly with Perfetto's track model. Use
`add_legacy_event` when the legacy payload itself is semantically important or
cannot be represented without loss.

## Clock snapshots and timestamp clock IDs

Clock snapshots correlate a producer's custom or relative clock with builtin
monotonic/realtime domains. Custom producer clock IDs start at 64. Emit readings
taken at the same synchronization point, select a per-sequence timestamp clock
through `TracePacketDefaults`, and override individual packets only when their
timestamps use another domain.

```python
from retrobus_perfetto import ClockReading, PerfettoTraceBuilder
from retrobus_perfetto.proto import perfetto_pb2

builder = PerfettoTraceBuilder("producer", timestamp_clock_id=65)
builder.add_clock_snapshot(
    [
        ClockReading(65, producer_ticks, unit_multiplier_ns=10),
        ClockReading(perfetto_pb2.BUILTIN_CLOCK_MONOTONIC, monotonic_ns),
        ClockReading(perfetto_pb2.BUILTIN_CLOCK_REALTIME, realtime_ns),
    ],
    primary_trace_clock=perfetto_pb2.BUILTIN_CLOCK_MONOTONIC,
)
builder.add_instant_event(lane, "relative", producer_timestamp)
```

This supports cross-trace correlation, device/host alignment, and relative
counter reconstruction without rewriting source timestamps. A packet's
explicit `timestamp_clock_id` takes precedence over the sequence default.

## Compatibility and regeneration

`py/tests/test_official_compat.py` compares the selected compact fields with and
parses all capabilities through the official merged Perfetto schema pinned in
`py/tests/fixtures`. Regenerate that descriptor with:

```sh
python3 tools/update_official_perfetto_descriptor.py
```

Python and C++ protobuf code is generated during their supported build flows;
TypeScript static bindings are refreshed with `npm run gen:proto` in `ts/`.
