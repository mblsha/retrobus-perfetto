//! Rust bindings for generating Perfetto traces for retrocomputer emulators.
//! This mirrors the Python/C++ `PerfettoTraceBuilder` API while leaning on
//! the `perfetto-writer` crate for protobuf correctness.

mod annotations;
mod builder;
mod reentrant;

pub use annotations::{AnnotationError, AnnotationValue};
pub use builder::{PerfettoTraceBuilder, TrackEventBuilder, TrackId, TrackKind, TrackOptions};
pub use perfetto_writer::{
    BuiltinClock, ClockReading, CounterUnit, FlowDirection, FrameKind, InlineFrame,
    InstantEventScope, LegacyEvent, LegacyId, SiblingMergeBehavior, SiblingMergeKey,
    SourceLocation, StackFrame, StackMapping,
};
pub use reentrant::{ReentrantGuard, ReentrantHandle};
