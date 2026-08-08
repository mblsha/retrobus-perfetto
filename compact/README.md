# Allocation-free compact recorder

`retrobus_compact_trace` is the target-side half of the `.rbct` workflow. It
records completed slices and numeric events into a caller-owned fixed ring and
has no protobuf or operating-system dependency.

Use the Python schema tool once per producer:

```sh
python tools/compact_schema_header.py producer-schema.json generated/trace_schema.h
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
rbct_writer_begin(&trace_writer, read_ticks(), 0, EXAMPLE_TRACE_EVENT_WORK,
                  NULL, 0);
do_work();
rbct_writer_end(&trace_writer, read_ticks());
```

Call `rbct_writer_clock_sync()` at capture boundaries, not for every event.
After the measurement, call `rbct_writer_finalize()` and export exactly
`rbct_writer_size()` bytes beginning at `rbct_writer_data()`. Buffer allocation,
locking, persistence, and transport deliberately remain producer policy.

For C++17 and newer, `retrobus/compact_trace.hpp` adds a non-owning `Writer`
and `TraceScope`. A null or disabled writer does not read the supplied clock.

## Build

```sh
cmake -S compact -B build/compact -DCMAKE_BUILD_TYPE=Release
cmake --build build/compact
ctest --test-dir build/compact --output-on-failure
```

The C implementation is C99 and has no unresolved libc symbols when compiled
normally. Its event path is single-producer; use separate writers for
concurrent producers and merge reconstructed traces on the host.
