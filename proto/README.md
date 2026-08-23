# Protocol Buffer Definitions

This directory contains the shared protocol buffer definitions used by all language implementations of retrobus-perfetto.

## Files

- `perfetto.proto` - The Perfetto trace format protocol buffer definition

## Usage

### Python
The Python build process will automatically compile these proto files during installation.
Generated files will be placed in `py/retrobus_perfetto/proto/`.

### C++
Include these proto files in your C++ build system using your preferred method (CMake, Bazel, etc.).

### TypeScript (Node)
The TypeScript bindings are generated via `protobufjs` static modules:

```bash
cd ts
npm install
npm run gen:proto
```

Generated files are placed in `ts/src/proto/`.

## Notes

This is intentionally a compact subset, not a fork of the entire Perfetto
schema. Included fields retain the exact official field numbers, wire types,
oneofs, and enum values. The fidelity subset covers event-category and profiling
interning, structured annotations, sibling track merging, TrackEvent
callstacks/source locations, Chrome legacy payloads, and clock snapshots.

`py/tests/test_official_compat.py` compares those fields with a pinned full
official Perfetto descriptor and parses a representative trace through it. See
[`perfetto-fidelity-guide.md`](../perfetto-fidelity-guide.md) for provenance,
regeneration, and API/policy boundaries.

These definitions are shared across generated Python, C++, and TypeScript
bindings. Do not modify them without auditing readers, merge/index tooling, and
all generated consumers.
