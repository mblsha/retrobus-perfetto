use crate::annotations::{apply_annotation, AnnotationError, AnnotationValue};
use anyhow::{bail, Result};
use perfetto_writer::{
    BuiltinClock, ClockReading, Context, InlineFrame, LegacyEvent, SiblingMergeBehavior,
    SiblingMergeKey, SourceLocation, StackFrame,
};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

pub type TrackId = u64;
type Writer = Vec<u8>;
type PwEvent<'a> = perfetto_writer::EventBuilder<'a, Writer>;

#[derive(Debug, Clone)]
pub enum TrackKind {
    Process {
        name: String,
        pid: i32,
    },
    Thread {
        name: String,
        tid: i32,
        parent_uuid: TrackId,
    },
    Counter {
        name: String,
        unit: Option<String>,
        parent_uuid: TrackId,
    },
    Generic {
        name: String,
        parent_uuid: TrackId,
        sibling_merge_behavior: Option<SiblingMergeBehavior>,
        sibling_merge_key: Option<SiblingMergeKey>,
    },
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct TrackOptions {
    pub parent_uuid: Option<TrackId>,
    pub sibling_merge_behavior: Option<SiblingMergeBehavior>,
    pub sibling_merge_key: Option<SiblingMergeKey>,
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
    annotation_max_depth: usize,
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
            annotation_max_depth: 64,
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

    /// Set the maximum number of nested dictionary/array annotation containers.
    pub fn with_annotation_max_depth(mut self, max_depth: usize) -> Self {
        self.annotation_max_depth = max_depth;
        self
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

    fn new_event<'a>(
        &'a mut self,
        track_uuid: TrackId,
        name: Option<&str>,
        timestamp_ns: i64,
    ) -> PwEvent<'a> {
        let mut event = self.ctx.event();
        event.track_uuid(track_uuid);
        event.timestamp_ns(
            u64::try_from(timestamp_ns).expect("Perfetto packet timestamps cannot be negative"),
        );
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

    /// Add a general event track, optionally configuring official sibling merging.
    pub fn add_track(
        &mut self,
        name: impl Into<String>,
        mut options: TrackOptions,
    ) -> Result<TrackId> {
        if options.sibling_merge_key.is_some() {
            match options.sibling_merge_behavior {
                None => {
                    options.sibling_merge_behavior = Some(SiblingMergeBehavior::BySiblingMergeKey);
                }
                Some(SiblingMergeBehavior::BySiblingMergeKey) => {}
                Some(_) => {
                    bail!("sibling merge keys require SiblingMergeBehavior::BySiblingMergeKey")
                }
            }
        }

        let name = name.into();
        let track_uuid = self.next_uuid();
        let parent = options.parent_uuid.unwrap_or(self.process_uuid);
        let mut track = self
            .ctx
            .track()
            .uuid(track_uuid)
            .parent_uuid(parent)
            .name(name.clone());
        if let Some(behavior) = options.sibling_merge_behavior {
            track = track.sibling_merge_behavior(behavior);
        }
        if let Some(key) = &options.sibling_merge_key {
            track = match key {
                SiblingMergeKey::String(key) => track.sibling_merge_key(key.clone()),
                SiblingMergeKey::Integer(key) => track.sibling_merge_key_int(*key),
            };
        }
        track.build();

        self.tracks.insert(
            track_uuid,
            TrackKind::Generic {
                name,
                parent_uuid: parent,
                sibling_merge_behavior: options.sibling_merge_behavior,
                sibling_merge_key: options.sibling_merge_key,
            },
        );
        Ok(track_uuid)
    }

    /// Add a physical lane which Perfetto merges with siblings using `merge_key`.
    pub fn add_merged_track_lane(
        &mut self,
        name: impl Into<String>,
        merge_key: impl Into<SiblingMergeKey>,
    ) -> TrackId {
        self.add_track(
            name,
            TrackOptions {
                sibling_merge_key: Some(merge_key.into()),
                ..Default::default()
            },
        )
        .expect("the merged-track convenience options are valid")
    }

    /// Add a merged physical lane under an explicit parent track.
    pub fn add_merged_track_lane_under(
        &mut self,
        name: impl Into<String>,
        merge_key: impl Into<SiblingMergeKey>,
        parent_uuid: TrackId,
    ) -> TrackId {
        self.add_track(
            name,
            TrackOptions {
                parent_uuid: Some(parent_uuid),
                sibling_merge_key: Some(merge_key.into()),
                ..Default::default()
            },
        )
        .expect("the merged-track convenience options are valid")
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
        let annotation_max_depth = self.annotation_max_depth;
        let mut event = self.new_event(track_uuid, Some(&name), timestamp_ns);
        event.begin();
        TrackEventBuilder::new(event, annotation_max_depth)
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
        let annotation_max_depth = self.annotation_max_depth;
        let mut event = self.new_event(track_uuid, Some(&name), timestamp_ns);
        event.instant();
        TrackEventBuilder::new(event, annotation_max_depth)
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
        let annotation_max_depth = self.annotation_max_depth;
        let mut event = self.new_event(track_uuid, Some(&name), timestamp_ns);
        event.instant();
        if terminating {
            event.terminating_flow_id(flow_id);
        } else {
            event.flow_id(flow_id);
        }
        TrackEventBuilder::new(event, annotation_max_depth)
    }

    /// Add a Chrome legacy event when native slices/instants/counters/flows are insufficient.
    pub fn add_legacy_event<'a>(
        &'a mut self,
        track_uuid: TrackId,
        name: impl Into<String>,
        timestamp_ns: i64,
        legacy: &LegacyEvent,
    ) -> TrackEventBuilder<'a> {
        let name = name.into();
        let annotation_max_depth = self.annotation_max_depth;
        let mut event = self.new_event(track_uuid, Some(&name), timestamp_ns);
        event.legacy(legacy);
        TrackEventBuilder::new(event, annotation_max_depth)
    }

    pub fn set_default_timestamp_clock(&mut self, clock_id: u32) {
        self.ctx.set_default_timestamp_clock(clock_id);
    }

    pub fn add_clock_snapshot(
        &mut self,
        readings: &[ClockReading],
        primary_trace_clock: Option<BuiltinClock>,
    ) -> Result<()> {
        self.ctx.add_clock_snapshot(readings, primary_trace_clock)
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
    annotation_max_depth: usize,
}

impl<'a> TrackEventBuilder<'a> {
    pub(crate) fn new(event: PwEvent<'a>, annotation_max_depth: usize) -> Self {
        Self {
            event: Some(event),
            annotation_max_depth,
        }
    }

    pub fn add_annotation(
        &mut self,
        name: impl AsRef<str>,
        value: impl Into<AnnotationValue>,
    ) -> &mut Self {
        self.try_add_annotation(name, value)
            .expect("invalid structured debug annotation")
    }

    /// Add an annotation after validating its entire structure without mutation.
    pub fn try_add_annotation(
        &mut self,
        name: impl AsRef<str>,
        value: impl Into<AnnotationValue>,
    ) -> std::result::Result<&mut Self, AnnotationError> {
        let value = value.into();
        value.validate_depth(self.annotation_max_depth)?;
        if let Some(event) = self.event.as_mut() {
            apply_annotation(name.as_ref(), value, event);
        }
        Ok(self)
    }

    pub fn add_annotations<I, K, V>(&mut self, annotations: I) -> &mut Self
    where
        I: IntoIterator<Item = (K, V)>,
        K: AsRef<str>,
        V: Into<AnnotationValue>,
    {
        self.try_add_annotations(annotations)
            .expect("invalid structured debug annotation")
    }

    pub fn try_add_annotations<I, K, V>(
        &mut self,
        annotations: I,
    ) -> std::result::Result<&mut Self, AnnotationError>
    where
        I: IntoIterator<Item = (K, V)>,
        K: AsRef<str>,
        V: Into<AnnotationValue>,
    {
        let annotations: Vec<(String, AnnotationValue)> = annotations
            .into_iter()
            .map(|(name, value)| (name.as_ref().to_owned(), value.into()))
            .collect();
        for (_, value) in &annotations {
            value.validate_depth(self.annotation_max_depth)?;
        }
        if let Some(event) = self.event.as_mut() {
            for (name, value) in annotations {
                apply_annotation(&name, value, event);
            }
        }
        Ok(self)
    }

    pub fn add_category(&mut self, category: impl Into<String>) -> &mut Self {
        if let Some(event) = self.event.as_mut() {
            event.category(category.into());
        }
        self
    }

    /// Attach an interned source location to the event.
    pub fn set_source_location(&mut self, location: &SourceLocation) -> &mut Self {
        if let Some(event) = self.event.as_mut() {
            event.source_location(location, true);
        }
        self
    }

    /// Attach an inline source location instead of using incremental interning.
    pub fn set_inline_source_location(&mut self, location: &SourceLocation) -> &mut Self {
        if let Some(event) = self.event.as_mut() {
            event.source_location(location, false);
        }
        self
    }

    pub fn set_inline_callstack(&mut self, frames: &[InlineFrame]) -> &mut Self {
        if let Some(event) = self.event.as_mut() {
            event.inline_callstack(frames);
        }
        self
    }

    pub fn set_callstack(&mut self, frames: &[StackFrame]) -> &mut Self {
        if let Some(event) = self.event.as_mut() {
            event.callstack(frames);
        }
        self
    }

    pub fn timestamp_clock_id(&mut self, clock_id: u32) -> &mut Self {
        if let Some(event) = self.event.as_mut() {
            event.timestamp_clock_id(clock_id);
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
    use crate::{
        AnnotationValue, FlowDirection, FrameKind, InstantEventScope, LegacyId, StackMapping,
    };
    use perfetto_protos::trace::Trace;
    use pretty_assertions::assert_eq;
    use protobuf::descriptor::FileDescriptorSet;
    use protobuf::reflect::FileDescriptor;
    use protobuf::Message;
    use std::fs;
    use std::path::Path;

    fn parse_trace(bytes: &[u8]) -> Trace {
        Trace::parse_from_bytes(bytes).expect("valid trace")
    }

    fn parse_with_pinned_official_descriptor(bytes: &[u8]) -> String {
        let descriptor_path = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../py/tests/fixtures/perfetto-official-ec5d16b1.desc");
        let descriptor_set = FileDescriptorSet::parse_from_bytes(
            &fs::read(descriptor_path).expect("read pinned official descriptor"),
        )
        .expect("parse pinned official descriptor");
        let descriptors = FileDescriptor::new_dynamic_fds(descriptor_set.file, &[])
            .expect("build official descriptors");
        let trace_descriptor = descriptors
            .iter()
            .find_map(|descriptor| descriptor.message_by_full_name(".perfetto.protos.Trace"))
            .expect("official Trace descriptor");
        trace_descriptor
            .parse_from_bytes(bytes)
            .expect("trace parses with official Perfetto protobuf")
            .to_string()
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

        let cpu_td = trace
            .packet
            .iter()
            .find(|p| p.has_track_descriptor() && p.track_descriptor().uuid() == thread_track)
            .expect("cpu track")
            .track_descriptor();
        assert_eq!(cpu_td.thread.thread_name(), "CPU");
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
        let flow_count = trace.packet.iter().filter(|p| p.has_track_event()).count();
        assert_eq!(flow_count, 2);
    }

    #[test]
    fn fidelity_features_parse_with_official_perfetto() {
        let mut builder = PerfettoTraceBuilder::new("Profiler");
        builder.set_default_timestamp_clock(65);
        builder
            .add_clock_snapshot(
                &[
                    ClockReading {
                        clock_id: 65,
                        timestamp: 1_000,
                        is_incremental: Some(true),
                        unit_multiplier_ns: Some(10),
                    },
                    ClockReading {
                        clock_id: BuiltinClock::BUILTIN_CLOCK_MONOTONIC as u32,
                        timestamp: 20_000,
                        is_incremental: None,
                        unit_multiplier_ns: None,
                    },
                    ClockReading {
                        clock_id: BuiltinClock::BUILTIN_CLOCK_REALTIME as u32,
                        timestamp: 30_000,
                        is_incremental: None,
                        unit_multiplier_ns: None,
                    },
                ],
                Some(BuiltinClock::BUILTIN_CLOCK_MONOTONIC),
            )
            .expect("valid clock snapshot");

        let lane0 = builder.add_merged_track_lane("Kernel lane 0", "kernels");
        let lane1 = builder.add_merged_track_lane("Kernel lane 1", "kernels");

        let mapping = StackMapping {
            path: vec!["usr".into(), "lib".into(), "libcuda.so".into()],
            build_id: Some(b"build-id".to_vec()),
            start: Some(0x1000),
            end: Some(0x9000),
            ..Default::default()
        };
        let frames = vec![
            StackFrame {
                function_name: Some("main".into()),
                source_path: Some("/src/main.rs".into()),
                line_number: Some(7),
                kind: Some(FrameKind::Native),
                ..Default::default()
            },
            StackFrame {
                function_name: Some("launch_kernel".into()),
                mapping: Some(mapping),
                rel_pc: Some(0x123),
                source_path: Some("/src/cuda.rs".into()),
                line_number: Some(88),
                kind_string: Some("cuda".into()),
                ..Default::default()
            },
        ];
        let source = SourceLocation {
            file_name: "/src/cuda.rs".into(),
            function_name: Some("launch_kernel".into()),
            line_number: Some(88),
        };
        let launch = AnnotationValue::dictionary(vec![
            (
                "grid".into(),
                AnnotationValue::array(vec![
                    AnnotationValue::UInt(128),
                    AnnotationValue::UInt(2),
                    AnnotationValue::UInt(1),
                ]),
            ),
            ("occupancy".into(), AnnotationValue::Double(0.75)),
            ("cooperative".into(), AnnotationValue::Bool(true)),
            ("stream".into(), AnnotationValue::pointer(0xfeed)),
            ("kernel".into(), AnnotationValue::Str("vector_add".into())),
        ]);

        builder
            .add_instant_event(lane0, "sample", 100)
            .add_category("cuda")
            .add_category("kernel")
            .try_add_annotation("launch", launch)
            .expect("valid recursive annotation")
            .set_source_location(&source)
            .set_callstack(&frames)
            .finish();
        builder
            .add_instant_event(lane1, "inline", 110)
            .set_inline_source_location(&source)
            .set_inline_callstack(&[
                InlineFrame {
                    function_name: "outer".into(),
                    source_file: None,
                    line_number: None,
                },
                InlineFrame {
                    function_name: "inner".into(),
                    source_file: Some("/src/cuda.rs".into()),
                    line_number: Some(88),
                },
            ])
            .finish();

        let legacy = LegacyEvent {
            phase: i32::from(b'X'),
            duration_us: Some(20),
            thread_duration_us: Some(10),
            thread_instruction_delta: Some(7),
            id: Some(LegacyId::Global(0x123)),
            id_scope: Some("scope".into()),
            use_async_tts: Some(true),
            bind_id: Some(0x456),
            bind_to_enclosing: Some(true),
            flow_direction: Some(FlowDirection::FLOW_INOUT),
            instant_event_scope: Some(InstantEventScope::SCOPE_PROCESS),
            pid_override: Some(10),
            tid_override: Some(11),
        };
        builder
            .add_legacy_event(lane0, "legacy", 120, &legacy)
            .timestamp_clock_id(BuiltinClock::BUILTIN_CLOCK_REALTIME as u32)
            .finish();

        let bytes = builder.serialize().expect("serialize");
        let text = parse_with_pinned_official_descriptor(&bytes);
        for expected in [
            "event_categories {",
            "category_iids: 1",
            "dict_entries {",
            "array_values {",
            "pointer_value: 65261",
            "sibling_merge_behavior: SIBLING_MERGE_BEHAVIOR_BY_SIBLING_MERGE_KEY",
            "sibling_merge_key: \"kernels\"",
            "source_location_iid: 1",
            "source_location {",
            "callstack_iid: 1",
            "callstack {",
            "function_names {",
            "mapping_paths {",
            "source_paths {",
            "mappings {",
            "frames {",
            "callstacks {",
            "legacy_event {",
            "phase: 88",
            "global_id: 291",
            "clock_snapshot {",
            "timestamp_clock_id: 65",
            "timestamp_clock_id: 1",
        ] {
            assert!(text.contains(expected), "missing {expected:?} in:\n{text}");
        }
    }

    #[test]
    fn structured_annotation_depth_errors_are_atomic() {
        let mut builder = PerfettoTraceBuilder::new("Depth").with_annotation_max_depth(1);
        let track = builder.add_thread("CPU");
        let too_deep = AnnotationValue::dictionary(vec![(
            "nested".into(),
            AnnotationValue::array(vec![AnnotationValue::Bool(true)]),
        )]);
        let mut event = builder.add_instant_event(track, "sample", 100);
        let error = match event.try_add_annotation("metadata", too_deep) {
            Err(error) => error,
            Ok(_) => panic!("nested annotation should exceed the configured depth"),
        };
        assert_eq!(error, AnnotationError::DepthExceeded { max_depth: 1 });
        event.add_annotation("survived", true).finish();
        drop(event);

        let trace = parse_trace(&builder.serialize().expect("serialize"));
        let event = trace
            .packet
            .iter()
            .find(|packet| packet.has_track_event())
            .expect("track event")
            .track_event();
        assert_eq!(event.debug_annotations.len(), 1);
        assert!(event.debug_annotations[0].has_bool_value());
    }

    #[test]
    fn sibling_merge_options_reject_mismatched_behavior() {
        let mut builder = PerfettoTraceBuilder::new("Tracks");
        let error = builder
            .add_track(
                "invalid",
                TrackOptions {
                    sibling_merge_behavior: Some(SiblingMergeBehavior::None),
                    sibling_merge_key: Some("key".into()),
                    ..Default::default()
                },
            )
            .expect_err("invalid merge options");
        assert!(error.to_string().contains("BySiblingMergeKey"));
    }

    #[test]
    fn clock_snapshots_validate_primary_clock_rules() {
        let mut builder = PerfettoTraceBuilder::new("Clocks");
        assert!(builder.add_clock_snapshot(&[], None).is_err());
        assert!(builder
            .add_clock_snapshot(
                &[ClockReading {
                    clock_id: BuiltinClock::BUILTIN_CLOCK_MONOTONIC as u32,
                    timestamp: 10,
                    is_incremental: None,
                    unit_multiplier_ns: Some(2),
                }],
                Some(BuiltinClock::BUILTIN_CLOCK_MONOTONIC),
            )
            .is_err());
    }
}
