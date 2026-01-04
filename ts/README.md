# retrobus-perfetto (TypeScript protobuf)

This package provides TypeScript-friendly protobuf bindings for `proto/perfetto.proto`
using `protobufjs` static modules. It is intended to mirror the schema used by the
Python/C++ implementations so Node/TS tooling can emit and parse Perfetto traces.

## Install & generate

```bash
cd ts
npm install
npm run gen:proto
```

Generated files land in `ts/src/proto/` (gitignored):
- `perfetto_pb.js` (ES module)
- `perfetto_pb.d.ts` (TypeScript types)

Run `npm run gen:proto` before tests or when updating `proto/perfetto.proto`.

## Usage

```ts
import { perfetto } from "retrobus-perfetto-proto";

const Trace = perfetto.protos.Trace;
const trace = Trace.create({
  packet: []
});

const bytes = Trace.encode(trace).finish();
```

Notes:
- The module exports the named `perfetto` namespace from the generated static module.
- Regenerate after `proto/perfetto.proto` changes.
