# Retrobus compact trace format v3 (`.rbct`)

Retrobus compact trace is a producer-neutral, bounded flight-recorder format
for targets where emitting native Perfetto protobuf would perturb the workload.
The target records numeric IDs and counter ticks. A host-side schema restores
names, categories, argument types, tracks, and Perfetto packets.

The format is deliberately separate from a producer schema:

- the format version defines the file, chunk, and integer encoding;
- the schema version and SHA-256 identify the meaning of event IDs;
- event IDs are local to one producer and are never a global registry;
- strings and protobuf are absent from the target writer.

All multibyte fixed-width values are little-endian. Variable integers are the
shortest canonical unsigned LEB128 encoding of a value in `0..2^64-1`; a tenth
byte may contain only bit zero. Signed schema arguments use ZigZag followed by
ULEB128.

Every CRC is CRC-32/ISO-HDLC: reflected polynomial `0xedb88320`, initial value
`0xffffffff`, and final XOR `0xffffffff`. This is the CRC returned by zlib.

## File layout

An `.rbct` image is the exact usable recorder buffer. Writers reject buffer
sizes that are not exactly one header plus an integral number of chunks:

```text
160-byte file header
4096-byte chunk 0
4096-byte chunk 1
...
```

The chunks form a ring. Physical chunk order is not chronological after wrap;
readers order valid chunks by their 64-bit sequence number. Unused chunks are
zero. Versions 2 and 3 also require the payload slack after each valid chunk's
`used` cursor to be zero.
`rbct_writer_finalize()` computes CRCs after measurement, publishes the final
header CRC, and commits the image by setting the finalized bit last. Versions 2
and 3 protect both payloads and chunk headers, and readers reject a finalized
image in either version without both protections. Readers
remain compatible with finalized version 1 images that protect payloads only.

An explicitly requested crash-image read is best-effort. Version 2 scans
transactional record frames. Version 3 scans nonzero committed opcodes. Neither
trusts the two-byte payload cursor or count fields, which may lag publication;
both retain only the completely published record prefix. In a committed older
chunk, zero ends that chunk's slack and scanning continues with the next chunk;
in the newest chunk, zero ends the capture. An invalid, truncated, malformed,
or noncanonical record stops the capture because the single writer cannot have
committed a later record first.
Total overwrite/drop accounting is unavailable and is conservatively reported
as the retained records only. The target writer invokes
`RBCT_PLATFORM_PUBLISH_BARRIER()` before each commit opcode, and after an
invalidation marker when later writes must not pass it. Built-in hardware store
barriers cover
ARMv7+, AArch64, and RISC-V; x86 uses its store-ordering guarantee plus a
compiler barrier under GCC, Clang, and MSVC. MSVC ARM builds use a hardware
barrier. Other targets, including ARMv5, default to compiler ordering and must
override the macro when a snapshot can race the writer. Non-coherent
persistence additionally requires a platform-specific snapshot or cache-flush
policy. A snapshot taken after the writer is quiesced must use the platform's
normal synchronization primitive before copying the buffer.
Passing the recovery option never relaxes validation of an image whose finalized
header and CRC are intact. Recovery input must be a stable snapshot; the host
rejects a file that changes between its header and payload passes.

### File header

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 8 | `RBCTRC3\0` |
| 8 | 2 | format version (`3`) |
| 10 | 2 | file header bytes (`160`) |
| 12 | 2 | chunk header bytes (`48`) |
| 14 | 2 | reserved, zero |
| 16 | 4 | chunk bytes (`4096`) |
| 20 | 8 | clock-rate numerator, ticks per rational second |
| 28 | 8 | clock-rate denominator |
| 36 | 2 | counter width in bits (`1..64`) |
| 38 | 2 | flags: bit 0 finalized, bit 1 ring wrapped, bit 2 chunk-header CRCs |
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

The ring-wrapped flag is sticky and is published when the writer first begins
overwriting a chunk, so it is meaningful in both live and finalized images.
The finalized flag is the file-header commit marker: it is published only after
the final header CRC is complete.

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
| 44 | 4 | chunk-header CRC32, or zero when file-header flag bit 2 is clear |

The payload occupies the rest of the 4096-byte chunk. A new chunk resets the
current timestamp to its base and the current track to its default. A clock-sync
record advances the current timestamp to its counter-interval midpoint.
Live writers invalidate the first magic byte before reusing a chunk, populate
the stable header fields and `BCK` suffix, then publish the leading `R` last as
the chunk commit marker. A crash reader ignores chunks whose magic was not
completely published.
When flag bit 2 is set, the chunk-header CRC covers all 48 header bytes with the
field at offset 44 treated as zero. The payload CRC continues to cover exactly
the `used payload bytes`; finalized version 2 and 3 readers also require the
unprotected payload slack to remain zero, making hidden trailing data
non-canonical without narrowing version 1 compatibility.

## Version 3 semantic commit opcodes

Version 3 uses the first byte of each logical record both as its semantic
opcode and as its transactional publication marker. Payloads are zero-filled.
The writer leaves the opcode byte zero, writes the remaining body, executes the
platform publication barrier, and stores the nonzero opcode last.

The exact producer schema determines the opcode map without changing semantic
event IDs:

1. Sort events by semantic ID. The first 251 events receive ordinary opcodes
   `0x01..0xfb` in that order.
2. If ordinary events leave free opcodes below `0xfc`, assign pairs to eligible
   no-stored-argument instants in semantic-ID order. The first opcode in a pair
   means delta zero and the second means delta one.
3. Events without an ordinary opcode use the extended-event control plus their
   semantic ID. Generated emitters use the ordinary and specialized forms; the
   public generic writer API deliberately uses the extended form as a
   schema-independent compatibility fallback.

The control namespace is fixed:

| Opcode | Meaning |
| ---: | --- |
| `0x00` | uncommitted sentinel |
| `0x01..0xfb` | schema-derived ordinary event or specialized instant |
| `0xfc` | reserved loss marker |
| `0xfd` | clock synchronization |
| `0xfe` | tracked-event wrapper |
| `0xff` | extended event |

A same-track ordinary event is:

```text
ordinary schema opcode
timestamp delta ULEB128
duration ULEB128, only for schema kind "slice"
schema-defined arguments
```

A specialized instant is its one-byte schema opcode with no body. An extended
event replaces the ordinary opcode with `0xff`, followed by the semantic event
ID as ULEB128 and then the ordinary body. A track change wraps the complete
event in one transaction:

```text
0xfe
track ID ULEB128
inner ordinary/specialized opcode, or 0xff plus semantic event ID
remaining event body
```

The outer `0xfe` is published last, so a track selection can never be stranded
without its event. A wrapper selecting the current track, a nested control, an
unknown schema opcode, or a specialized opcode with an incompatible schema
shape is invalid. A clock synchronization is `0xfd` followed by its five
fields. No event may exceed 70 total bytes including its committed opcode.

The crash-publication guarantee follows by induction. Before the final opcode
store, a reader reaches zero and returns the preceding fully committed prefix.
After that store, the barrier makes the complete schema-shaped body visible.
The writer never starts a later record first. Updating `used`, counts, and
writer state only afterward therefore cannot expose a partial logical record.
A completely full payload is valid without a trailing zero sentinel.

This guarantee addresses interrupted writes, not arbitrary memory corruption.
Unlike v2's per-record length, an unfinalized v3 corruption that happens to look
like a valid opcode or varint can alter parsing through the rest of that chunk.
The next 4096-byte chunk is the amortized restart point because each chunk resets
timestamp and track state. Finalized payload and header CRCs detect corruption.
Finer live resynchronization would require measured justification for extra
checksums or restart metadata; v3 does not charge every record another byte.

For a direct same-track slice with one-byte delta and duration, v3 uses three
bytes, matching v1 and improving a 4048-byte payload from 1012 v2 records to
1349 v3 records. A specialized no-argument instant with delta zero or one uses
one byte, retaining 4048 records. Argument-bearing events with delta zero or one
are no larger than their v1/v2 representation.

## Version 2 record frames

Each version 2 logical record has this transactional envelope:

```text
uint8 publication marker
record bytes
```

Every ordinary record body is at most 70 bytes. Marker values encode its length
and the two most common event timestamp deltas. The remaining marker space
inlines the smallest events:

| Marker | Body bytes | Event ID | Timestamp delta |
| ---: | ---: | ---: | ---: |
| `1..70` | marker | in body | explicit ULEB128 in the body |
| `71..140` | marker − 70 | in body | implicit `0` |
| `141..210` | marker − 140 | in body | implicit `1` |
| `211..232` | `0` | marker − 211 | implicit `0` |
| `233..254` | `0` | marker − 233 | implicit `1` |
| `255` | — | — | invalid |

The 70-byte bound is exact: track and event controls with maximum `uint32` IDs
use 12 bytes, the half-range-bounded timestamp delta and duration use at most 18,
and four maximum `uint64` ULEB128 arguments use 40.

The inline forms are valid only for event IDs `0..21` on the current track
with no duration or stored arguments; the publication marker is the entire
record. Clock-sync frames use only the explicit `1..70` range. The writer copies
the body before publishing the one-byte marker; supported targets publish byte
stores atomically. A reader stops an unfinalized scan at the first zero, invalid,
oversized, truncated, malformed, or non-canonical frame and never interprets
zero-filled slack as event data. New writers use an implicit marker for event
deltas zero and one; an explicit encoding of either value is non-canonical.
Finalized readers require every byte through the chunk's `used` cursor to be a
complete frame.

A frame contains exactly one event or one clock synchronization. An event frame
may begin with one non-redundant track selection; a clock-sync frame may not.
This keeps every publication unit independently bounded and canonical.

## Logical record semantics

In v1 and v2 bodies, semantic IDs `0..251` are encoded directly in one byte.
Event IDs at or above 252 use `0xff` followed by their ULEB128 value. Their
remaining lead bytes are controls:

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
one event. Host reconstruction preserves `uint` and `fixed64` as Perfetto
`uint_value`, `sint` as `int_value`, `bool` as `bool_value`, and `float64` as
`double_value`; pointer display requires a future explicit semantic schema type.
Nested slices are serialized in completion order. When two nested slices have
identical intervals, the host reverses that order for their begin packets and
keeps completion order for their end packets, preserving the writer's stack.
Slice ends retain their record position relative to same-tick events. A single
zero-duration slice brackets its record position; identical zero-duration
intervals use the same stack rule while their ends retain completion order.
Raw counter intervals distinguish adjacent sub-nanosecond slices that round to
the same Perfetto timestamp, preventing them from becoming falsely nested.

A clock synchronization record is:

```text
0xfd
generation
counter_before
counter_after
reference_timestamp_ns
uncertainty_ns
```

The reference timestamp is nanoseconds in Perfetto's built-in BOOTTIME clock
domain. The counter interval brackets acquisition of that timestamp. The
host uses its midpoint as the correlation anchor and preserves the uncertainty
as capture metadata. When several anchors exist, readers interpolate between
them and use the nominal clock rate only outside their range. Counter anchors
must advance and reference time must not move backwards, including across a
generation transition; reconstructed serialized observations must not move
backwards either. A producer's first synchronization in a generation precedes
that generation's first data record. Once a trace contains an absolute
correlation, every retained generation containing an event normally needs an
anchor. Ring overwrite may remove the first retained generation's anchor while
leaving its later events. In that one case, the host places the unanchored prefix
immediately before the first later absolute observation and preserves its
relative timing; missing anchors anywhere else remain invalid. A changed
generation advances by one modulo `2^32`, starts a new chunk and correlation
segment, and is invalid while a completed-slice scope remains open. Its first
logical record must be the synchronization record that establishes the new
generation.

The target writer enforces bounded counter samples, intervals, and generation
ordering needed for unambiguous serialization. Exact rational clock
correlation, including cross-generation mapped-time monotonicity, is validated
on the host so the freestanding recorder does not need multiword arithmetic
state or code.

In versions 2 and 3, within one generation, the producer must ensure that the
actual time between consecutive serialized observations, every completed-slice
duration, and every clock-sync bracket is strictly less than half the counter
range. Writers and readers reject modulo deltas at or above
`2^(counter_width - 1)`. This rejects ordinary backwards samples and makes a
single wrap unambiguous under the producer contract; the wire representation
cannot detect an exact multiple of the complete counter period, so producers
must synchronize or change generation before that limit.

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
may set `id_argument` to reconstruct the numeric event ID as a Perfetto debug
annotation and may define typed `constant_arguments`. Both are restored solely
on the host and consume no target-buffer bytes. They are useful when an event
ID already carries a dispatch number or when an ABI value is fixed by the
schema. Schemas are immutable: do not reuse an event ID or reorder its stored
arguments. Make an intentional schema-version change instead.

Counter events may use `sint`, finite `float64`, or `uint`; `uint` counter values
are restricted to `0..INT64_MAX` because Perfetto's exact integer counter field
is signed 64-bit. Counter events are valid only on counter tracks, and every
other event kind is valid only on thread tracks. Generated emitters enforce the
track domain, signed counter range, and finite floating-point bit pattern before
calling the opcode-aware writer API.

Flow and asynchronous events may define a `series` string used to pair lifecycle
records; it defaults to the event display name. Each asynchronous series must
contain begin and end event definitions, and each flow series must contain start
and end definitions. Ring overwrite can remove a lifecycle boundary. The host
marks orphan asynchronous ends as truncated instants, closes retained unmatched
boundaries rather than emitting invalid lifecycle state. An orphan flow end
becomes a standalone truncated instant with no flow ID. An orphan flow step
starts a retained lifecycle annotated as having a truncated beginning, allowing
a later retained end to remain connected. A repeated flow start truncates the
prior retained start and receives a new lifecycle ID, so a later end cannot
accidentally terminate both lifecycles.

The schema SHA-256 input is UTF-8 JSON with object keys sorted
lexicographically, array order preserved, no insignificant whitespace, `,` and
`:` separators, and non-ASCII characters emitted directly rather than `\u`
escaped. Finite floating-point values use Python's JSON round-tripping decimal
representation, including a fractional marker for integral floats. Duplicate
object keys, non-string keys, and non-finite numbers are invalid. This is the
byte sequence exposed as `CompactSchema.canonical_json`.

The default generated C prefix combines the normalized producer name, numeric
producer ID, and schema version, so independently generated producer and schema
version headers can coexist.
An explicit `--prefix` replaces that default; a prefix containing no C
identifier characters falls back to `PRODUCER_<id>`. Generated target constants
use the event or track name when it is unique. If multiple IDs intentionally
share a display name, the generator appends the numeric ID to each colliding C
macro; Perfetto continues to show the original shared name. The generated
header also provides a schema-specific inline
`..._TRACE_BEGIN_...` function for each slice and `..._TRACE_EMIT_...` function
for every other event. These functions select the correct record shape,
argument count, and integer encoding. `fixed64` and `float64` parameters are
supplied as their exact 64-bit wire bits.

The generator also derives v3 ordinary and specialized opcode constants from
the schema. That mapping changes only the wire representation selected by
`RBCTRC3`; semantic IDs, argument order, canonical schema JSON, schema hash, and
producer schema version are unchanged. A future format that makes opcode
priority or aliases explicit schema data must change the canonical schema and
use a corresponding producer-schema version rather than silently reinterpreting
an existing hash.

## Resource and safety contract

- Initialization zeros and therefore prefaults the complete usable buffer.
- The recorder performs no allocation, system call, file, socket, lock, or
  checksum work on the event path.
- The caller owns buffer residency, export, permissions, and transport.
- Target records contain no strings. Producers must not encode payloads,
  typed text, credentials, secrets, or host pointers as numeric arguments.
- One writer has one caller at a time. Concurrent producers use separate
  writers/tracks and are merged on the host.
- The writer object, recorder buffer, scope storage, and configuration are
  distinct, non-overlapping caller-owned objects.
- Kernel scheduling, IRQ, and PM tracing should continue to use native Linux
  tracepoints. Convert and correlate those records rather than putting this
  userspace writer in the kernel.

## Version compatibility

Version 1 uses `RBCTRC1\0` and an unframed payload stream. The current reader
accepts canonical output from the original writer, including arbitrary clock
generation identifiers and modulo counter gaps that predate the v2 half-range
contract. Version 2 uses `RBCTRC2\0` and the transactional length/implicit-delta
frames documented above. New writers emit only version 3. Version 1 crash
recovery remains inherently heuristic because it has neither record frames nor
a semantic commit opcode; applications needing trustworthy recovery must
migrate their producer to version 3. The host reader retains v1 and v2 support.
