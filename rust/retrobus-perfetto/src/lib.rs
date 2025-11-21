//! Rust bindings for generating Perfetto traces for retrocomputer emulators.
//! This mirrors the Python/C++ `PerfettoTraceBuilder` API while leaning on
//! the `perfetto-writer` crate for protobuf correctness.

mod annotations;
mod builder;

pub use annotations::AnnotationValue;
pub use builder::{PerfettoTraceBuilder, TrackEventBuilder, TrackId};
pub use perfetto_writer::CounterUnit;
