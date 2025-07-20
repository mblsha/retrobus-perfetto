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

## Notes

These protocol definitions are shared across all implementations to ensure compatibility.
Do not modify these files unless you intend to update all language implementations.