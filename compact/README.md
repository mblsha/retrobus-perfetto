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

static unsigned char trace_buffer[RBCT_FILE_HEADER_BYTES + 64 * RBCT_CHUNK_BYTES];
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
    rbct_writer_init(&trace_writer, trace_buffer, sizeof(trace_buffer),
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
The buffer size must equal `RBCT_FILE_HEADER_BYTES` plus an integral number of
`RBCT_CHUNK_BYTES`; initialization rejects trailing partial chunks. The writer,
buffer, scope storage, and configuration must not overlap.

New captures use framed format v2. Each record body is copied before its
one-byte publication marker, so best-effort crash recovery does not
mistake zero-filled slack for event ID zero. ARMv7+, AArch64, RISC-V, and x86
receive a built-in store-publication barrier. Other targets, including ARMv5,
must define `RBCT_PLATFORM_PUBLISH_BARRIER()` when a snapshot can race the
writer, or quiesce and synchronize the writer before copying. Platforms whose
snapshot is not coherent with ordinary stores must also supply the appropriate
persistence or cache-flush policy.

The marker also carries timestamp deltas zero and one. For event IDs `0..21`, a
same-track event with one of those deltas and no duration or stored arguments is
encoded entirely in that marker. A 4096-byte chunk therefore retains 4048
minimal events—twice the density of the unframed v1 stream. Other delta-zero and
delta-one events omit the timestamp field but retain a one-byte frame around
their body. The resource regression test locks in the 4048-event capacity and
caps the writer object at 136 bytes on 64-bit targets and 112 bytes on 32-bit
targets; CI also caps the ARMv5TE `-Os` text and reported function-stack
footprints.

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
and no-stack-protector options on GCC and Clang, and omits security-cookie and
default-runtime-library directives under MSVC, so the resulting target library
has no implicit runtime dependency. Equivalent flags are required when compiling
the source directly. Its event path is single-producer; use separate writers for
concurrent producers and merge reconstructed traces on the host.
Cross-generation rational-clock consistency is intentionally checked by the
host reader rather than with multiword arithmetic in the target recorder.
