# retrobus-perfetto (Rust)

Thin, idiomatic Rust wrapper around [`perfetto-writer`](https://crates.io/crates/perfetto-writer) that mirrors the Python/C++ `PerfettoTraceBuilder` in this repo. It emits Perfetto-compatible `.perfetto-trace` files for retrocomputer emulator instrumentation.

## Usage

```rust
use retrobus_perfetto::{AnnotationValue, PerfettoTraceBuilder};

fn main() -> anyhow::Result<()> {
    let mut builder = PerfettoTraceBuilder::new("My Emulator");
    let cpu = builder.add_thread("CPU");
    let counter = builder.add_counter_track("cycles", Some("ticks"), None);

    builder
        .begin_slice(cpu, "execute_instruction", 1_000)
        .add_annotation("pc", 0x1234u64)
        .add_annotation("opcode", 0xCDu64)
        .finish();
    builder.end_slice(cpu, 2_000);
    builder.update_counter(counter, 42u64, 1_500);

    builder.save("trace.perfetto-trace")?;
    Ok(())
}
```

### API highlights
- `PerfettoTraceBuilder::add_thread(name)` creates a thread track under the process.
- `add_track` exposes the official sibling-merge behavior/key contract;
  `add_merged_track_lane` creates backing lanes for overlapping work.
- `begin_slice` / `end_slice` emit duration spans; `add_instant_event` emits point events.
- `add_counter_track` + `update_counter` for counters.
- `add_flow` to connect events across tracks.
- `TrackEventBuilder` adds interned categories, source locations, inline or
  interned native callstacks, and typed recursive annotations.
- `add_legacy_event` preserves uncommon Chrome phases and payloads; common
  slices, instants, counters, and flows should use the native methods above.
- `set_default_timestamp_clock`, per-event `timestamp_clock_id`, and
  `add_clock_snapshot` correlate producer clocks with monotonic/realtime clocks.

Structured annotations use `AnnotationValue::dictionary` and
`AnnotationValue::array`. Rust's owned value tree cannot contain reference
cycles. `try_add_annotation` validates the complete tree against the configured
depth before changing the event; the chaining `add_annotation` convenience
method panics on invalid nesting.

The writer interns repeated category, annotation, source, mapping, frame, and
callstack data on its trusted packet sequence. The published
`perfetto_protos` crate currently predates TrackEvent callstacks and sibling
merge fields, so those newer official fields are carried through protobuf
unknown-field storage with their exact field numbers and wire types. Tests parse
the resulting bytes through the repository's pinned full official Perfetto
descriptor.

## Development

```bash
cargo fmt       # optional
cargo test      # runs unit tests
```

The crate consumes the builder on `serialize`/`save`; create a new builder per
trace. Timestamps are expressed in nanoseconds and emitted as native
`TracePacket.timestamp` values.

## Reentrant tracer handle

When instrumentation can nest (e.g., CPU → memory hook → IRQ hook), use `ReentrantHandle<T>` for a global tracer without deadlocks:

```rust
use retrobus_perfetto::ReentrantHandle;

struct MyTracer;
impl MyTracer {
    fn record(&mut self) {}
}

static TRACER: ReentrantHandle<Option<MyTracer>> = ReentrantHandle::new(None);

fn record_something() {
    TRACER.with_some(|tracer| tracer.record());
}
```
