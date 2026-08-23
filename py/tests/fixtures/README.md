# Official Perfetto compatibility descriptor

`perfetto-official-ec5d16b1.desc` is a protobuf descriptor set generated from
Perfetto's official merged `perfetto_trace.proto` at commit
`ec5d16b14b743ba6063d720956d6d6af6610fd72`. It lets the Python test suite parse
RetroBus traces with the full upstream schema without a network dependency or a
second checked-in generated language binding.

Regenerate it from the repository root with:

```sh
python3 tools/update_official_perfetto_descriptor.py
```

The generator verifies the pinned source SHA-256 before invoking `protoc`.
