# Allocation-free compact recorder

`retrobus_compact_trace` is the target-side half of the `.rbct` workflow. It
records completed slices and numeric events into a caller-owned fixed ring and
has no protobuf or operating-system dependency.

Use the Python schema tool once per producer:

```sh
python tools/compact_schema_header.py producer-schema.json generated/trace_schema.h \
    --prefix example
```

Initialize a buffer before entering the measured workload:

```c
#include <retrobus/compact_trace.h>
#include "trace_schema.h"

static union {
    uint32_t alignment;
    unsigned char bytes[RBCT_FILE_HEADER_BYTES + 64 * RBCT_CHUNK_BYTES];
} trace_buffer;
static rbct_scope_t trace_scopes[16];
static rbct_writer_t trace_writer;

static void start_trace(void) {
    rbct_config_t config = {0};
    config.clock_rate_numerator = 3686400;
    config.clock_rate_denominator = 1;
    config.clock_width_bits = 32;
    config.producer_id = EXAMPLE_TRACE_PRODUCER_ID;
    config.schema_version = EXAMPLE_TRACE_SCHEMA_VERSION;
    for (unsigned i = 0; i < 32; ++i)
        config.schema_sha256[i] = EXAMPLE_TRACE_SCHEMA_SHA256[i];
    rbct_writer_init(&trace_writer, trace_buffer.bytes, sizeof(trace_buffer.bytes),
                     trace_scopes, 16, &config);
}
```

The caller supplies timestamps, normally one mapped hardware-counter load:

```c
EXAMPLE_TRACE_BEGIN_WORK(&trace_writer, read_ticks(),
                         EXAMPLE_TRACE_TRACK_MAIN, 42);
do_work();
rbct_writer_end(&trace_writer, read_ticks());
```

The generated `..._TRACE_BEGIN_...` and `..._TRACE_EMIT_...` functions bind each
event to its schema-defined record shape and argument encodings; prefer them to
the generic writer calls. For `fixed64` and `float64`, pass the exact 64-bit wire
bits.

Call `rbct_writer_clock_sync()` at capture boundaries, before the first data
record in that clock generation, not for every event.
Its reference timestamp must use Perfetto's BOOTTIME clock domain.
Within one clock generation, serialized observations and completed scopes must
be separated by less than half the hardware-counter range. End all open scopes
before changing clock generation, and advance the generation by one modulo
`2^32` for each change.
`rbct_writer_end()` retains the open scope when validation fails so the caller
can retry; `rbct_writer_cancel()` explicitly discards the innermost scope.
After the measurement, call `rbct_writer_finalize()` and export exactly
`rbct_writer_size()` bytes beginning at `rbct_writer_data()`. Buffer allocation,
locking, persistence, and transport deliberately remain producer policy.
The four-byte-aligned buffer size must equal `RBCT_FILE_HEADER_BYTES` plus an integral number of
`RBCT_CHUNK_BYTES`; initialization rejects trailing partial chunks. The writer,
buffer, scope storage, and configuration must not overlap.

New captures use static-profile format v4. Train a profile outside the measured
target from representative captures, then generate its read-only target tables:

```sh
python tools/compact_codec_profile.py capture-a.rbct capture-b.rbct \
    --schema producer-schema.json --entry-limit 247 \
    --output generated/trace-codec.json \
    --c-header generated/trace_codec.h --c-prefix example_codec
```

Set `config.codec_profile = &EXAMPLE_CODEC_PROFILE` after including that header.
The writer retains only the profile pointer and two model-state bits. A hot tuple
uses a constant-time two-multiply perfect-hash lookup and appends a short static
Huffman code; all misses use a lossless schema-shaped literal. The file binds
the exact external profile by SHA-256. Leaving `codec_profile` null selects a
literal-only v4 stream that needs no external profile.

V4 publishes the payload bit cursor and record count with one aligned atomic
32-bit store after the publication barrier. Best-effort crash recovery therefore
returns exactly a prefix of committed records without a per-record marker.
Generated emitters provide one-byte ordinary identities on escape paths; the
generic begin/emit APIs remain valid through an extended semantic identity.

ARMv7+, AArch64, RISC-V, and x86 receive a built-in store-publication barrier.
Other targets, including ARMv5, must define
`RBCT_PLATFORM_PUBLISH_BARRIER()` when a snapshot can race the writer, or
quiesce and synchronize the writer before copying. Platforms whose snapshot is
not coherent with ordinary stores must also supply the appropriate persistence
or cache-flush policy.

A 4048-byte payload contains 32,384 profile bits. The resource regression fills
it with 32,383 slices when the first tuple costs two bits and steady state costs
one. Real density must be reported from corpus replay; historical host-clock
Redux profiles are explicitly diagnostic and must not be used as production
PXA profiles. The checksum-pinned implemented-wire replay, including the two
literal-kind bits on every miss and separate payload/container totals, is in
[`V4_CODEC_AUDIT.md`](V4_CODEC_AUDIT.md). The writer object remains capped at
144 bytes on 64-bit targets
and 120 bytes on 32-bit targets, while each scope remains at 88 bytes.
The complete ARMv5TE soft-float `-Os -ffixed-r9` writer currently measures
8360 bytes of text with 168 bytes maximum reported stack and no undefined
symbols. CI gates it at 8500 bytes and 192 bytes respectively. The added text
implements profile validation, CHD lookup, bit publication, and literal escape;
the generated 128/247-entry profile occupies 936/1768 bytes of read-only ARM
ROM including its hash-bound descriptor. The old 7000-byte text gate has not
been restored; the 8500-byte budget requires explicit acceptance.

Bit packing weakens arbitrary-corruption isolation for live, unchecksummed
snapshots: a valid-looking corrupt code can disrupt the remainder of one chunk.
It does not weaken interrupted-write publication. Finalized CRCs detect
corruption, and chunk boundaries provide restart points every 4096 bytes.

Chunk reuse invalidates the leading magic byte before changing any retained
contents, then publishes that byte last after the replacement header is ready.
The ring-wrapped flag is set as soon as live overwrite begins. Finalization
similarly publishes the header CRC before setting the finalized bit, so crash
recovery never observes that bit as an early commit marker.

For C++17 and newer, `retrobus/compact_trace.hpp` adds a non-owning `Writer`
and `TraceScope`. A null or disabled writer does not read the supplied clock.
`TraceScope::cancel()` explicitly abandons an active scope. If an end timestamp
is invalid during destruction, the wrapper cancels the retained C scope so RAII
cannot leave the writer permanently unfinalizable; `Writer::status()` preserves
the failed end status.

## Build

```sh
cmake -S compact -B build/compact -DCMAKE_BUILD_TYPE=Release
cmake --build build/compact
ctest --test-dir build/compact --output-on-failure
```

Pure C consumers can avoid requiring a C++ compiler:

```sh
cmake -S compact -B build/compact-c -DRBCT_BUILD_CPP=OFF
cmake --build build/compact-c
```

The C implementation is C99. Its CMake target applies freestanding, no-builtin,
and no-stack-protector options on GCC and Clang, and disables security cookies and
runtime-backed compiler intrinsics while omitting default-runtime-library
directives under MSVC, so the resulting target library has no implicit runtime
dependency. Equivalent flags are required when compiling the source directly.
Its event path is
single-producer; use separate writers for concurrent producers and merge
reconstructed traces on the host.
Cross-generation rational-clock consistency is intentionally checked by the
host reader rather than with multiword arithmetic in the target recorder.
