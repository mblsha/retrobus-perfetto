# Retrobus compact trace format (`.rbct`)

Retrobus compact trace is a producer-neutral, bounded flight-recorder format
for targets where emitting native Perfetto protobuf would perturb the workload.
The target records numeric IDs and counter ticks. A host-side schema restores
names, categories, argument types, tracks, and Perfetto packets.

The format is deliberately separate from a producer schema:

- the format version defines the file, chunk, and integer encoding;
- the schema version and SHA-256 identify the meaning of event IDs;
- event IDs are local to one producer and are never a global registry;
- strings and protobuf are absent from the target writer.

All multibyte fixed-width values are little-endian. Variable integers are
unsigned LEB128. Signed schema arguments use ZigZag followed by ULEB128.

## File layout

An `.rbct` image is the exact caller-provided recorder buffer:

```text
160-byte file header
4096-byte chunk 0
4096-byte chunk 1
...
```

The chunks form a ring. Physical chunk order is not chronological after wrap;
readers order valid chunks by their 64-bit sequence number. Unused chunks are
zero. `rbct_writer_finalize()` computes CRCs after measurement and marks the
image finalized. Readers reject a finalized image with a bad CRC. An explicitly
requested crash-image read can recover intact chunk payloads before finalize,
but total overwrite/drop accounting is unavailable and is conservatively
reported as the retained records only.

### File header

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 8 | `RBCTRC1\0` |
| 8 | 2 | format version (`1`) |
| 10 | 2 | file header bytes (`160`) |
| 12 | 2 | chunk header bytes (`48`) |
| 14 | 2 | reserved, zero |
| 16 | 4 | chunk bytes (`4096`) |
| 20 | 8 | clock-rate numerator, ticks per rational second |
| 28 | 8 | clock-rate denominator |
| 36 | 2 | counter width in bits (`1..64`) |
| 38 | 2 | flags: bit 0 finalized, bit 1 ring wrapped |
| 40 | 4 | producer ID |
| 44 | 4 | producer schema version |
| 48 | 32 | SHA-256 of the canonical producer schema |
| 80 | 16 | capture/session ID |
| 96 | 8 | total data records accepted |
| 104 | 8 | data records overwritten in whole chunks |
| 112 | 8 | data records dropped before admission |
| 120 | 8 | total expanded Perfetto events accepted |
| 128 | 8 | expanded events overwritten in whole chunks |
| 136 | 8 | usable buffer bytes |
| 144 | 4 | initial clock generation |
| 148 | 4 | default track ID |
| 152 | 4 | CRC32 of the header with this field zero |
| 156 | 4 | reserved, zero |

Clock duration in seconds is `ticks * denominator / numerator`. Integer-Hz
clocks use denominator `1`. A generation change means counter samples on the
two sides must not be extended as one continuous clock.

### Chunk header

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | `RBCK` |
| 4 | 8 | sequence number |
| 12 | 8 | raw counter value used as the first delta base |
| 20 | 4 | clock generation |
| 24 | 4 | default track ID |
| 28 | 2 | used payload bytes |
| 30 | 2 | data-record count |
| 32 | 4 | expanded Perfetto-event count |
| 36 | 2 | clock-sync record count |
| 38 | 2 | reserved, zero |
| 40 | 4 | payload CRC32 |
| 44 | 4 | reserved, zero |

The payload occupies the rest of the 4096-byte chunk. A new chunk resets the
current timestamp to its base and the current track to its default.

## Payload records

IDs `0..251` are encoded directly in one byte. Event IDs at or above 252 use
`0xff` followed by their ULEB128 value. The remaining lead bytes are controls:

| Lead | Record |
| ---: | --- |
| `0xfc` | reserved loss marker |
| `0xfd` | clock synchronization |
| `0xfe` | set current track: ULEB128 track ID |
| `0xff` | extended event ID: ULEB128 event ID |

An event record is:

```text
event ID
timestamp delta in raw counter ticks
duration in raw counter ticks, only for schema kind "slice"
schema-defined numeric arguments
```

The event schema determines the record kind, argument count (at most four), and each argument
encoding. `uint`, `bool`, and identifiers are ULEB128; `sint` is ZigZag
ULEB128; `fixed64` and `float64` are eight little-endian bytes. A completed
slice expands to Perfetto begin/end events. Every other schema kind expands to
one event.

A clock synchronization record is:

```text
0xfd
generation
counter_before
counter_after
reference_timestamp_ns
uncertainty_ns
```

The counter interval brackets acquisition of the reference timestamp. The
host uses its midpoint as the correlation anchor and preserves the uncertainty
as capture metadata. A changed generation starts a new chunk and correlation
segment. A 32-bit counter may wrap; readers extend it using unsigned deltas and
must reject or segment a gap that could contain more than one wrap.

## Producer schema

The canonical JSON schema has this minimum shape:

```json
{
  "format": "retrobus-compact-schema-v1",
  "producer": {"id": 42, "name": "example"},
  "version": 1,
  "process": "Example target",
  "tracks": [
    {"id": 0, "name": "main", "kind": "thread"},
    {"id": 1, "name": "bytes", "kind": "counter", "unit": "bytes"}
  ],
  "events": [
    {
      "id": 1,
      "name": "work",
      "category": "runtime",
      "kind": "slice",
      "arguments": [{"name": "amount", "type": "uint"}]
    },
    {
      "id": 2,
      "name": "bytes",
      "category": "storage",
      "kind": "counter",
      "arguments": [{"name": "value", "type": "uint"}]
    }
  ]
}
```

Supported event kinds are `slice`, `instant`, `counter`, `flow_start`,
`flow_step`, `flow_end`, `async_begin`, and `async_end`. Flow and asynchronous
events name their correlation argument with `correlation_argument`. Schemas
are immutable: do not reuse an event ID or reorder its arguments. Make an
intentional schema-version change instead.

## Resource and safety contract

- Initialization zeros and therefore prefaults the complete usable buffer.
- The recorder performs no allocation, system call, file, socket, lock, or
  checksum work on the event path.
- The caller owns buffer residency, export, permissions, and transport.
- Target records contain no strings. Producers must not encode payloads,
  typed text, credentials, secrets, or host pointers as numeric arguments.
- One writer has one caller at a time. Concurrent producers use separate
  writers/tracks and are merged on the host.
- Kernel scheduling, IRQ, and PM tracing should continue to use native Linux
  tracepoints. Convert and correlate those records rather than putting this
  userspace writer in the kernel.

Redux `.rdxt` version 1 is a predecessor with a producer-specific header and
schema. The Python decoder retains an explicit compatibility path; `.rdxt`
files are never treated as `.rbct` merely by extension.
