# retrobus-perfetto (Rust)

Thin, idiomatic Rust wrapper around [`perfetto-writer`](https://crates.io/crates/perfetto-writer) that mirrors the Python/C++ `PerfettoTraceBuilder` in this repo. It emits Perfetto-compatible `.perfetto-trace` files for retrocomputer emulator instrumentation.

## Usage

```rust
use retrobus_perfetto::{PerfettoTraceBuilder, AnnotationValue};

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
- `begin_slice` / `end_slice` emit duration spans; `add_instant_event` emits point events.
- `add_counter_track` + `update_counter` for counters.
- `add_flow` to connect events across tracks.
- `TrackEventBuilder` adds annotations with automatic pointer detection (`pc`, `_addr`, `_pointer`, etc.).

## Development

```bash
cargo fmt       # optional
cargo test      # runs unit tests
```

The crate consumes the builder on `serialize`/`save`; create a new builder per trace. Timestamps are expressed in nanoseconds in the API and converted to microseconds for Perfetto.
