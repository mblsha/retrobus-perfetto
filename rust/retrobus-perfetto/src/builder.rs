use crate::annotations::{apply_annotation, AnnotationValue};
use anyhow::Result;
use perfetto_writer::Context;
use std::collections::HashMap;
use std::fs;
use std::path::Path;

pub type TrackId = u64;
type Writer = Vec<u8>;
type PwEvent<'a> = perfetto_writer::EventBuilder<'a, Writer>;

#[derive(Debug, Clone)]
pub enum TrackKind {
    Process { name: String, pid: i32 },
    Thread { name: String, tid: i32, parent_uuid: TrackId },
    Counter { name: String, unit: Option<String>, parent_uuid: TrackId },
}

/// Thin wrapper that mirrors the Python/C++ builder API while leaning on `perfetto-writer`
/// for protobuf correctness.
pub struct PerfettoTraceBuilder {
    ctx: Context<Writer>,
    pid: i32,
    process_uuid: TrackId,
    next_uuid: TrackId,
    next_tid: i32,
    tracks: HashMap<TrackId, TrackKind>,
}

impl PerfettoTraceBuilder {
    /// Create a new builder with a top-level process track.
    pub fn new(process_name: impl Into<String>) -> Self {
        let ctx = Context::new(Vec::new());
        let pid = 1234;
        let mut builder = Self {
            ctx,
            pid,
            process_uuid: 0,
            next_uuid: 0,
            next_tid: 1,
            tracks: HashMap::new(),
        };

        let process_name = process_name.into();
        let process_uuid = builder.next_uuid();
        builder
            .ctx
            .track()
            .uuid(process_uuid)
            .name(process_name.clone())
            .build();

        builder.tracks.insert(
            process_uuid,
            TrackKind::Process {
                name: process_name,
                pid,
            },
        );
        builder.process_uuid = process_uuid;
        builder
    }

    /// Override the PID recorded in thread descriptors.
    pub fn with_pid(mut self, pid: i32) -> Self {
        self.pid = pid;
        self
    }

    pub fn process_uuid(&self) -> TrackId {
        self.process_uuid
    }

    fn next_uuid(&mut self) -> TrackId {
        self.next_uuid += 1;
        self.next_uuid
    }

    fn next_tid(&mut self) -> i32 {
        let tid = self.next_tid;
        self.next_tid += 1;
        tid
    }

    fn nanos_to_micros(ts_ns: i64) -> i64 {
        ts_ns.div_euclid(1_000)
    }

    fn new_event<'a>(
        &'a mut self,
        track_uuid: TrackId,
        name: Option<&str>,
        timestamp_ns: i64,
    ) -> PwEvent<'a> {
        let mut event = self.ctx.event();
        event.track_uuid(track_uuid);
        event.timestamp_us(Self::nanos_to_micros(timestamp_ns));
        if let Some(name) = name {
            event.name(name.to_string());
        }
        event
    }

    /// Add a thread track (labels carry over to the Perfetto UI).
    pub fn add_thread(&mut self, name: impl Into<String>) -> TrackId {
        let name = name.into();
        let track_uuid = self.next_uuid();
        let tid = self.next_tid();

        self.ctx
            .track()
            .uuid(track_uuid)
            .parent_uuid(self.process_uuid)
            .pid(self.pid)
            .tid(tid)
            .name(name.clone())
            .build();

        self.tracks.insert(
            track_uuid,
            TrackKind::Thread {
                name,
                tid,
                parent_uuid: self.process_uuid,
            },
        );

        track_uuid
    }

    /// Add a counter track.
    pub fn add_counter_track(
        &mut self,
        name: impl Into<String>,
        unit: Option<&str>,
        parent_uuid: Option<TrackId>,
    ) -> TrackId {
        let name = name.into();
        let track_uuid = self.next_uuid();
        let parent = parent_uuid.unwrap_or(self.process_uuid);
        let display_name = unit
            .map(|u| {
                if u.is_empty() {
                    name.clone()
                } else {
                    format!("{name} ({u})")
                }
            })
            .unwrap_or_else(|| name.clone());

        let mut track = self
            .ctx
            .track()
            .uuid(track_uuid)
            .parent_uuid(parent)
            .name(display_name)
            .counter();

        if let Some(unit) = unit {
            if !unit.is_empty() {
                track = track.unit_name(unit.to_string());
            }
        }

        track.build();

        self.tracks.insert(
            track_uuid,
            TrackKind::Counter {
                name,
                unit: unit.filter(|u| !u.is_empty()).map(|u| u.to_string()),
                parent_uuid: parent,
            },
        );

        track_uuid
    }

    /// Begin a duration slice and return a builder to add annotations or flows.
    pub fn begin_slice<'a>(
        &'a mut self,
        track_uuid: TrackId,
        name: impl Into<String>,
        timestamp_ns: i64,
    ) -> TrackEventBuilder<'a> {
        let name = name.into();
        let mut event = self.new_event(track_uuid, Some(&name), timestamp_ns);
        event.begin();
        TrackEventBuilder::new(event)
    }

    /// End a duration slice.
    pub fn end_slice(&mut self, track_uuid: TrackId, timestamp_ns: i64) {
        let mut event = self.new_event(track_uuid, None, timestamp_ns);
        event.end();
        event.build();
    }

    /// Add an instant event.
    pub fn add_instant_event<'a>(
        &'a mut self,
        track_uuid: TrackId,
        name: impl Into<String>,
        timestamp_ns: i64,
    ) -> TrackEventBuilder<'a> {
        let name = name.into();
        let mut event = self.new_event(track_uuid, Some(&name), timestamp_ns);
        event.instant();
        TrackEventBuilder::new(event)
    }

    /// Add a flow marker to connect spans across tracks.
    pub fn add_flow<'a>(
        &'a mut self,
        track_uuid: TrackId,
        name: impl Into<String>,
        timestamp_ns: i64,
        flow_id: u64,
        terminating: bool,
    ) -> TrackEventBuilder<'a> {
        let name = name.into();
        let mut event = self.new_event(track_uuid, Some(&name), timestamp_ns);
        event.instant();
        if terminating {
            event.terminating_flow_id(flow_id);
        } else {
            event.flow_id(flow_id);
        }
        TrackEventBuilder::new(event)
    }

    /// Update a counter track.
    pub fn update_counter<V: Into<CounterValue>>(
        &mut self,
        track_uuid: TrackId,
        value: V,
        timestamp_ns: i64,
    ) {
        let mut event = self.new_event(track_uuid, None, timestamp_ns);
        event.counter();

        match value.into() {
            CounterValue::Int(v) => event.counter_value(v),
            CounterValue::Double(v) => event.double_counter_value(v),
        }

        event.build();
    }

    /// Serialize the trace to bytes. This consumes the builder.
    pub fn serialize(self) -> Result<Vec<u8>> {
        let mut ctx = self.ctx;
        ctx.flush()?;
        Ok(ctx.into_inner())
    }

    /// Write the trace to a file. This consumes the builder.
    pub fn save(self, path: impl AsRef<Path>) -> Result<()> {
        let bytes = self.serialize()?;
        fs::write(path, bytes)?;
        Ok(())
    }

    pub fn track_info(&self, track_uuid: TrackId) -> Option<&TrackKind> {
        self.tracks.get(&track_uuid)
    }
}

pub enum CounterValue {
    Int(i64),
    Double(f64),
}

impl From<i64> for CounterValue {
    fn from(value: i64) -> Self {
        CounterValue::Int(value)
    }
}

impl From<u64> for CounterValue {
    fn from(value: u64) -> Self {
        if value > i64::MAX as u64 {
            CounterValue::Double(value as f64)
        } else {
            CounterValue::Int(value as i64)
        }
    }
}

impl From<usize> for CounterValue {
    fn from(value: usize) -> Self {
        CounterValue::from(value as u64)
    }
}

impl From<f64> for CounterValue {
    fn from(value: f64) -> Self {
        CounterValue::Double(value)
    }
}

impl From<f32> for CounterValue {
    fn from(value: f32) -> Self {
        CounterValue::Double(value as f64)
    }
}

/// Wrapper around `perfetto-writer`'s event builder that auto-builds on drop.
pub struct TrackEventBuilder<'a> {
    event: Option<PwEvent<'a>>,
}

impl<'a> TrackEventBuilder<'a> {
    pub(crate) fn new(event: PwEvent<'a>) -> Self {
        Self { event: Some(event) }
    }

    pub fn add_annotation(
        &mut self,
        name: impl AsRef<str>,
        value: impl Into<AnnotationValue>,
    ) -> &mut Self {
        if let Some(event) = self.event.as_mut() {
            apply_annotation(name.as_ref(), value.into(), event);
        }
        self
    }

    pub fn add_annotations<I, K, V>(&mut self, annotations: I) -> &mut Self
    where
        I: IntoIterator<Item = (K, V)>,
        K: AsRef<str>,
        V: Into<AnnotationValue>,
    {
        if let Some(event) = self.event.as_mut() {
            for (name, value) in annotations {
                apply_annotation(name.as_ref(), value.into(), event);
            }
        }
        self
    }

    pub fn flow_id(&mut self, id: u64) -> &mut Self {
        if let Some(event) = self.event.as_mut() {
            event.flow_id(id);
        }
        self
    }

    pub fn terminating_flow_id(&mut self, id: u64) -> &mut Self {
        if let Some(event) = self.event.as_mut() {
            event.terminating_flow_id(id);
        }
        self
    }

    pub fn finish(&mut self) {
        if let Some(event) = self.event.take() {
            event.build();
        }
    }
}

impl Drop for TrackEventBuilder<'_> {
    fn drop(&mut self) {
        if let Some(event) = self.event.take() {
            event.build();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use perfetto_protos::trace::Trace;
    use pretty_assertions::assert_eq;
    use protobuf::Message;

    fn parse_trace(bytes: &[u8]) -> Trace {
        Trace::parse_from_bytes(bytes).expect("valid trace")
    }

    #[test]
    fn creates_process_and_thread_tracks() {
        let mut builder = PerfettoTraceBuilder::new("TestProcess").with_pid(42);
        let thread_track = builder.add_thread("CPU");
        let counter_track = builder.add_counter_track("cycles", Some("ticks"), None);

        builder
            .begin_slice(thread_track, "execute", 1_000)
            .add_annotation("pc", 0x1000u64)
            .add_annotation("opcode", 0xCDu16 as i64)
            .finish();
        builder.end_slice(thread_track, 2_000);
        builder.update_counter(counter_track, 10u64, 1_500);

        let bytes = builder.serialize().expect("serialize");
        let trace = parse_trace(&bytes);

        // Expect: init packet + process + thread + counter + begin + end + counter update
        assert!(trace.packet.len() >= 6);

        let names: Vec<String> = trace
            .packet
            .iter()
            .filter(|p| p.has_track_descriptor())
            .map(|p| p.track_descriptor().name().to_string())
            .collect();
        assert!(names.contains(&"TestProcess".to_string()));
        assert!(names.iter().any(|n| n.contains("cycles")));
    }

    #[test]
    fn flow_events_and_annotations() {
        let mut builder = PerfettoTraceBuilder::new("FlowTest");
        let thread = builder.add_thread("CPU");

        builder
            .add_flow(thread, "start", 10_000, 99, false)
            .add_annotation("address", 0xDEAD_BEEFu64)
            .finish();
        builder
            .add_flow(thread, "end", 20_000, 99, true)
            .add_annotation("ok", true)
            .finish();

        let bytes = builder.serialize().expect("serialize");
        let trace = parse_trace(&bytes);
        let flow_count = trace
            .packet
            .iter()
            .filter(|p| p.has_track_event())
            .count();
        assert_eq!(flow_count, 2);
    }
}
