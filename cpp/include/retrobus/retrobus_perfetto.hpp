// retrobus_perfetto.hpp - Header-only C++ library for creating Perfetto traces
// Copyright (c) 2024 - MIT License

#pragma once

#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <limits>
#include <memory>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

// Include protobuf headers - users must provide these
#include <google/protobuf/message.h>

// Generated protobuf headers - users must generate these from perfetto.proto
#include "perfetto.pb.h"

namespace retrobus {

// Forward declarations
class TrackEventWrapper;
class AnnotationBuilder;
class AnnotationArrayBuilder;

using FrameTimelinePresentType =
    perfetto::protos::FrameTimelineEvent::PresentType;
using FrameTimelinePredictionType =
    perfetto::protos::FrameTimelineEvent::PredictionType;
using FrameTimelineJankSeverityType =
    perfetto::protos::FrameTimelineEvent::JankSeverityType;
using FrameTimelineLatchedFenceState = perfetto::protos::FrameTimelineEvent::
    ActualSurfaceFrameStart::LatchedFenceState;
using SiblingMergeBehavior =
    perfetto::protos::TrackDescriptor::SiblingMergeBehavior;

struct SourceLocation {
  std::string file_name;
  std::string function_name;
  std::optional<uint32_t> line_number;
};

struct StackMapping {
  std::vector<std::string> path;
  std::optional<std::string> build_id;
  std::optional<uint64_t> exact_offset;
  std::optional<uint64_t> start_offset;
  std::optional<uint64_t> start;
  std::optional<uint64_t> end;
  std::optional<uint64_t> load_bias;
};

struct StackFrame {
  std::optional<std::string> function_name;
  std::optional<StackMapping> mapping;
  std::optional<uint64_t> rel_pc;
  std::optional<std::string> source_path;
  std::optional<uint32_t> line_number;
  std::optional<perfetto::protos::Frame::Kind> kind;
  std::optional<std::string> kind_string;
};

struct InlineFrame {
  std::string function_name;
  std::optional<std::string> source_file;
  std::optional<uint32_t> line_number;
};

struct ClockReading {
  uint32_t clock_id = 0;
  uint64_t timestamp = 0;
  std::optional<bool> is_incremental;
  std::optional<uint64_t> unit_multiplier_ns;
};

enum class LegacyIdType { kUnscoped, kLocal, kGlobal };

struct LegacyEvent {
  int32_t phase = 0;
  std::optional<int64_t> duration_us;
  std::optional<int64_t> thread_duration_us;
  std::optional<int64_t> thread_instruction_delta;
  std::optional<uint64_t> id;
  LegacyIdType id_type = LegacyIdType::kUnscoped;
  std::optional<std::string> id_scope;
  std::optional<bool> use_async_tts;
  std::optional<uint64_t> bind_id;
  std::optional<bool> bind_to_enclosing;
  std::optional<perfetto::protos::TrackEvent::LegacyEvent::FlowDirection>
      flow_direction;
  std::optional<perfetto::protos::TrackEvent::LegacyEvent::InstantEventScope>
      instant_event_scope;
  std::optional<int32_t> pid_override;
  std::optional<int32_t> tid_override;
};

struct FrameTimelineExpectedSurfaceFrameStart {
  int64_t cookie = 0;
  int64_t token = 0;
  int64_t display_frame_token = 0;
  std::optional<int32_t> pid;
  std::string layer_name;
};

struct FrameTimelineActualSurfaceFrameStart {
  int64_t cookie = 0;
  int64_t token = 0;
  int64_t display_frame_token = 0;
  std::optional<int32_t> pid;
  std::string layer_name;

  std::optional<FrameTimelinePresentType> present_type;
  std::optional<bool> on_time_finish;
  std::optional<bool> gpu_composition;
  std::optional<int32_t> jank_type;
  std::optional<FrameTimelinePredictionType> prediction_type;
  std::optional<bool> is_buffer;
  std::optional<FrameTimelineJankSeverityType> jank_severity_type;
  std::optional<float> present_delay_millis;
  std::optional<float> vsync_resynced_jitter_millis;
  std::optional<float> jank_severity_score;
  std::optional<int32_t> jank_type_experimental;
  std::optional<FrameTimelinePresentType> present_type_experimental;
  std::optional<float> jank_debug_metadata;
  std::optional<FrameTimelineLatchedFenceState> latched_fence_state;
  std::optional<float> animation_time_millis;
};

struct FrameTimelineExpectedDisplayFrameStart {
  int64_t cookie = 0;
  int64_t token = 0;
  std::optional<int32_t> pid;
};

struct FrameTimelineActualDisplayFrameStart {
  int64_t cookie = 0;
  int64_t token = 0;
  std::optional<int32_t> pid;

  std::optional<FrameTimelinePresentType> present_type;
  std::optional<bool> on_time_finish;
  std::optional<bool> gpu_composition;
  std::optional<int32_t> jank_type;
  std::optional<FrameTimelinePredictionType> prediction_type;
  std::optional<FrameTimelineJankSeverityType> jank_severity_type;
  std::optional<float> present_delay_millis;
  std::optional<float> jank_severity_score;
  std::optional<int32_t> jank_type_experimental;
  std::optional<FrameTimelinePresentType> present_type_experimental;
  std::optional<float> jank_debug_metadata;
  std::optional<int64_t> latched_unsignaled_count;
  std::optional<int64_t> addressable_unsignaled_latch_count;
};

// Utility functions
namespace detail {
// Default values for trace generation
constexpr uint64_t DEFAULT_THREAD_TID = 1000;
constexpr int32_t DEFAULT_PROCESS_PID = 1234;
// Pointer heuristic detection
inline bool is_pointer_key(std::string_view key) {
  // Check suffixes (C++17 compatible)
  const std::array<std::string_view, 5> suffixes = {"_addr", "_address", "_pc",
                                                    "_sp", "_pointer"};
  for (const auto& suffix : suffixes) {
    if (key.size() >= suffix.size() &&
        key.substr(key.size() - suffix.size()) == suffix) {
      return true;
    }
  }

  // Check exact matches
  return key == "pc" || key == "sp" || key == "address";
}

inline void append_key_piece(std::string& key, std::string_view value) {
  key.append(std::to_string(value.size()));
  key.push_back(':');
  key.append(value.data(), value.size());
  key.push_back('|');
}

template <typename T>
inline void append_optional_number(std::string& key,
                                   const std::optional<T>& value) {
  if (value) {
    key.push_back('1');
    key.append(std::to_string(*value));
  } else {
    key.push_back('0');
  }
  key.push_back('|');
}

class InterningState {
 public:
  uint64_t intern_event_category(std::string_view category,
                                 perfetto::protos::TracePacket* packet) {
    mark_incremental_state_needed(packet);
    std::string key(category);
    const auto it = event_categories_.find(key);
    if (it != event_categories_.end()) {
      return it->second;
    }
    const uint64_t iid = next_event_category_iid_++;
    event_categories_.emplace(key, iid);
    auto* entry = packet->mutable_interned_data()->add_event_categories();
    entry->set_iid(iid);
    entry->set_name(key);
    return iid;
  }

  uint64_t intern_event_name(std::string_view name,
                             perfetto::protos::TracePacket* packet) {
    mark_incremental_state_needed(packet);

    std::string key(name);
    auto it = event_names_.find(key);
    if (it != event_names_.end()) {
      return it->second;
    }

    const uint64_t iid = next_event_name_iid_++;
    event_names_.emplace(key, iid);

    auto* entry = packet->mutable_interned_data()->add_event_names();
    entry->set_iid(iid);
    entry->set_name(key);
    return iid;
  }

  uint64_t intern_debug_annotation_name(std::string_view name,
                                        perfetto::protos::TracePacket* packet) {
    mark_incremental_state_needed(packet);

    std::string key(name);
    auto it = debug_annotation_names_.find(key);
    if (it != debug_annotation_names_.end()) {
      return it->second;
    }

    const uint64_t iid = next_debug_annotation_name_iid_++;
    debug_annotation_names_.emplace(key, iid);

    auto* entry = packet->mutable_interned_data()->add_debug_annotation_names();
    entry->set_iid(iid);
    entry->set_name(key);
    return iid;
  }

  uint64_t intern_debug_annotation_string_value(
      std::string_view value,
      perfetto::protos::TracePacket* packet) {
    mark_incremental_state_needed(packet);

    std::string key(value);
    auto it = debug_annotation_string_values_.find(key);
    if (it != debug_annotation_string_values_.end()) {
      return it->second;
    }

    const uint64_t iid = next_debug_annotation_string_value_iid_++;
    debug_annotation_string_values_.emplace(key, iid);

    auto* entry =
        packet->mutable_interned_data()->add_debug_annotation_string_values();
    entry->set_iid(iid);
    entry->set_str(key);
    return iid;
  }

  uint64_t intern_source_location(const SourceLocation& location,
                                  perfetto::protos::TracePacket* packet) {
    mark_incremental_state_needed(packet);
    std::string key;
    append_key_piece(key, location.file_name);
    append_key_piece(key, location.function_name);
    append_optional_number(key, location.line_number);
    const auto it = source_locations_.find(key);
    if (it != source_locations_.end()) {
      return it->second;
    }
    const uint64_t iid = next_source_location_iid_++;
    source_locations_.emplace(key, iid);
    auto* entry = packet->mutable_interned_data()->add_source_locations();
    entry->set_iid(iid);
    if (!location.file_name.empty()) {
      entry->set_file_name(location.file_name);
    }
    if (!location.function_name.empty()) {
      entry->set_function_name(location.function_name);
    }
    if (location.line_number) {
      entry->set_line_number(*location.line_number);
    }
    return iid;
  }

  uint64_t intern_build_id(std::string_view value,
                           perfetto::protos::TracePacket* packet) {
    return intern_string_table(value, packet, build_ids_, next_build_id_iid_,
                               &perfetto::protos::InternedData::add_build_ids);
  }

  uint64_t intern_mapping_path(std::string_view value,
                               perfetto::protos::TracePacket* packet) {
    return intern_string_table(
        value, packet, mapping_paths_, next_mapping_path_iid_,
        &perfetto::protos::InternedData::add_mapping_paths);
  }

  uint64_t intern_source_path(std::string_view value,
                              perfetto::protos::TracePacket* packet) {
    return intern_string_table(
        value, packet, source_paths_, next_source_path_iid_,
        &perfetto::protos::InternedData::add_source_paths);
  }

  uint64_t intern_function_name(std::string_view value,
                                perfetto::protos::TracePacket* packet) {
    return intern_string_table(
        value, packet, function_names_, next_function_name_iid_,
        &perfetto::protos::InternedData::add_function_names);
  }

  uint64_t intern_mapping(const StackMapping& mapping,
                          perfetto::protos::TracePacket* packet) {
    mark_incremental_state_needed(packet);
    const std::string key = mapping_key(mapping);
    const auto it = mappings_.find(key);
    if (it != mappings_.end()) {
      return it->second;
    }
    const uint64_t iid = next_mapping_iid_++;
    mappings_.emplace(key, iid);
    auto* entry = packet->mutable_interned_data()->add_mappings();
    entry->set_iid(iid);
    if (mapping.build_id) {
      entry->set_build_id(intern_build_id(*mapping.build_id, packet));
    }
    for (const auto& component : mapping.path) {
      entry->add_path_string_ids(intern_mapping_path(component, packet));
    }
    if (mapping.exact_offset) {
      entry->set_exact_offset(*mapping.exact_offset);
    }
    if (mapping.start_offset) {
      entry->set_start_offset(*mapping.start_offset);
    }
    if (mapping.start) {
      entry->set_start(*mapping.start);
    }
    if (mapping.end) {
      entry->set_end(*mapping.end);
    }
    if (mapping.load_bias) {
      entry->set_load_bias(*mapping.load_bias);
    }
    return iid;
  }

  uint64_t intern_frame(const StackFrame& frame,
                        perfetto::protos::TracePacket* packet) {
    if (frame.mapping && !frame.rel_pc) {
      throw std::invalid_argument("rel_pc is required when mapping is set");
    }
    mark_incremental_state_needed(packet);
    std::string key;
    append_key_piece(key, frame.function_name.value_or(std::string{}));
    key.push_back(frame.function_name ? '1' : '0');
    append_key_piece(key, frame.mapping ? mapping_key(*frame.mapping) : "");
    key.push_back(frame.mapping ? '1' : '0');
    append_optional_number(key, frame.rel_pc);
    append_key_piece(key, frame.source_path.value_or(std::string{}));
    key.push_back(frame.source_path ? '1' : '0');
    append_optional_number(key, frame.line_number);
    if (frame.kind) {
      key.append("e").append(std::to_string(static_cast<int>(*frame.kind)));
    } else if (frame.kind_string) {
      key.push_back('s');
      append_key_piece(key, *frame.kind_string);
    } else {
      key.push_back('0');
    }
    const auto it = frames_.find(key);
    if (it != frames_.end()) {
      return it->second;
    }
    const uint64_t iid = next_frame_iid_++;
    frames_.emplace(key, iid);
    auto* entry = packet->mutable_interned_data()->add_frames();
    entry->set_iid(iid);
    if (frame.function_name) {
      entry->set_function_name_id(
          intern_function_name(*frame.function_name, packet));
    }
    if (frame.mapping) {
      entry->set_mapping_id(intern_mapping(*frame.mapping, packet));
    }
    if (frame.rel_pc) {
      entry->set_rel_pc(*frame.rel_pc);
    }
    if (frame.source_path) {
      entry->set_source_path_iid(
          intern_source_path(*frame.source_path, packet));
    }
    if (frame.line_number) {
      entry->set_line_number(*frame.line_number);
    }
    if (frame.kind_string) {
      entry->set_kind_str(*frame.kind_string);
    } else if (frame.kind) {
      entry->set_kind(*frame.kind);
    }
    return iid;
  }

  uint64_t intern_callstack(const std::vector<StackFrame>& frames,
                            perfetto::protos::TracePacket* packet) {
    std::vector<uint64_t> frame_iids;
    frame_iids.reserve(frames.size());
    std::string key;
    for (const auto& frame : frames) {
      const uint64_t iid = intern_frame(frame, packet);
      frame_iids.push_back(iid);
      key.append(std::to_string(iid)).push_back('|');
    }
    mark_incremental_state_needed(packet);
    const auto it = callstacks_.find(key);
    if (it != callstacks_.end()) {
      return it->second;
    }
    const uint64_t iid = next_callstack_iid_++;
    callstacks_.emplace(key, iid);
    auto* entry = packet->mutable_interned_data()->add_callstacks();
    entry->set_iid(iid);
    for (const auto frame_iid : frame_iids) {
      entry->add_frame_ids(frame_iid);
    }
    return iid;
  }

 private:
  using AddInternedString =
      perfetto::protos::InternedString* (perfetto::protos::InternedData::*)();

  uint64_t intern_string_table(std::string_view value,
                               perfetto::protos::TracePacket* packet,
                               std::unordered_map<std::string, uint64_t>& table,
                               uint64_t& next_iid,
                               AddInternedString add_entry) {
    mark_incremental_state_needed(packet);
    std::string key(value);
    const auto it = table.find(key);
    if (it != table.end()) {
      return it->second;
    }
    const uint64_t iid = next_iid++;
    table.emplace(key, iid);
    auto* entry = (packet->mutable_interned_data()->*add_entry)();
    entry->set_iid(iid);
    entry->set_str(key);
    return iid;
  }

  static std::string mapping_key(const StackMapping& mapping) {
    std::string key;
    key.push_back(mapping.build_id ? '1' : '0');
    if (mapping.build_id) {
      append_key_piece(key, *mapping.build_id);
    }
    for (const auto& component : mapping.path) {
      append_key_piece(key, component);
    }
    key.push_back(';');
    append_optional_number(key, mapping.exact_offset);
    append_optional_number(key, mapping.start_offset);
    append_optional_number(key, mapping.start);
    append_optional_number(key, mapping.end);
    append_optional_number(key, mapping.load_bias);
    return key;
  }

  void mark_incremental_state_needed(perfetto::protos::TracePacket* packet) {
    uint32_t flags = packet->sequence_flags();
    flags |= perfetto::protos::TracePacket::SEQ_NEEDS_INCREMENTAL_STATE;
    packet->set_sequence_flags(flags);
  }

  std::unordered_map<std::string, uint64_t> event_categories_;
  std::unordered_map<std::string, uint64_t> event_names_;
  std::unordered_map<std::string, uint64_t> debug_annotation_names_;
  std::unordered_map<std::string, uint64_t> debug_annotation_string_values_;
  std::unordered_map<std::string, uint64_t> source_locations_;
  std::unordered_map<std::string, uint64_t> build_ids_;
  std::unordered_map<std::string, uint64_t> mapping_paths_;
  std::unordered_map<std::string, uint64_t> source_paths_;
  std::unordered_map<std::string, uint64_t> function_names_;
  std::unordered_map<std::string, uint64_t> mappings_;
  std::unordered_map<std::string, uint64_t> frames_;
  std::unordered_map<std::string, uint64_t> callstacks_;

  uint64_t next_event_category_iid_{1};
  uint64_t next_event_name_iid_{1};
  uint64_t next_debug_annotation_name_iid_{1};
  uint64_t next_debug_annotation_string_value_iid_{1};
  uint64_t next_source_location_iid_{1};
  uint64_t next_build_id_iid_{1};
  uint64_t next_mapping_path_iid_{1};
  uint64_t next_source_path_iid_{1};
  uint64_t next_function_name_iid_{1};
  uint64_t next_mapping_iid_{1};
  uint64_t next_frame_iid_{1};
  uint64_t next_callstack_iid_{1};
};

struct SequenceInternTables {
  std::unordered_map<uint64_t, std::string> event_categories = {};
  std::unordered_map<uint64_t, std::string> event_names = {};
  std::unordered_map<uint64_t, std::string> debug_annotation_names = {};
  std::unordered_map<uint64_t, std::string> debug_annotation_string_values = {};
  std::unordered_map<uint64_t, perfetto::protos::SourceLocation>
      source_locations = {};
  bool valid = false;

  void clear(const bool mark_valid = false) {
    event_categories.clear();
    event_names.clear();
    debug_annotation_names.clear();
    debug_annotation_string_values.clear();
    source_locations.clear();
    valid = mark_valid;
  }
};

inline std::string make_missing_iid_string(std::string_view kind,
                                           const uint64_t iid) {
  return "<missing " + std::string(kind) + " iid=" + std::to_string(iid) + ">";
}

inline void resolve_debug_annotation_inplace(
    perfetto::protos::DebugAnnotation& annotation,
    const SequenceInternTables& tables) {
  if (annotation.name_field_case() ==
      perfetto::protos::DebugAnnotation::kNameIid) {
    const auto iid = annotation.name_iid();
    const auto it = tables.debug_annotation_names.find(iid);
    annotation.set_name(
        it != tables.debug_annotation_names.end()
            ? it->second
            : make_missing_iid_string("DebugAnnotationName", iid));
  }

  if (annotation.value_case() ==
      perfetto::protos::DebugAnnotation::kStringValueIid) {
    const auto iid = annotation.string_value_iid();
    const auto it = tables.debug_annotation_string_values.find(iid);
    annotation.set_string_value(
        it != tables.debug_annotation_string_values.end()
            ? it->second
            : make_missing_iid_string("DebugAnnotationStringValue", iid));
  }

  for (auto& entry : *annotation.mutable_dict_entries()) {
    resolve_debug_annotation_inplace(entry, tables);
  }
  for (auto& entry : *annotation.mutable_array_values()) {
    resolve_debug_annotation_inplace(entry, tables);
  }
}
}  // namespace detail

// Main trace builder class
class PerfettoTraceBuilder {
 private:
  std::unique_ptr<perfetto::protos::Trace> trace_;
  std::atomic<uint64_t> last_track_uuid_{0};
  std::atomic<uint64_t> last_thread_tid_{detail::DEFAULT_THREAD_TID};
  uint64_t process_uuid_;
  int32_t pid_;
  uint32_t trusted_packet_sequence_id_{1};
  bool emitted_incremental_state_cleared_{false};

  // Metadata tracking
  std::unordered_map<uint64_t, std::string> track_names_;
  std::unordered_map<uint64_t, uint64_t> track_parents_;

  detail::InterningState interning_state_;

  // Helpers to add new packets with consistent initialization
  perfetto::protos::TracePacket* create_packet() {
    auto* packet = trace_->add_packet();
    packet->set_trusted_packet_sequence_id(trusted_packet_sequence_id_);
    if (!emitted_incremental_state_cleared_) {
      packet->set_sequence_flags(
          packet->sequence_flags() |
          perfetto::protos::TracePacket::SEQ_INCREMENTAL_STATE_CLEARED);
      emitted_incremental_state_cleared_ = true;
    }
    return packet;
  }

  perfetto::protos::TracePacket* create_packet(
      uint64_t timestamp_ns,
      std::optional<uint32_t> timestamp_clock_id = std::nullopt) {
    auto* packet = create_packet();
    packet->set_timestamp(timestamp_ns);
    if (timestamp_clock_id) {
      packet->set_timestamp_clock_id(*timestamp_clock_id);
    }
    return packet;
  }

 public:
  explicit PerfettoTraceBuilder(std::string_view process_name,
                                int32_t pid = detail::DEFAULT_PROCESS_PID)
      : trace_(std::make_unique<perfetto::protos::Trace>()),
        process_uuid_(++last_track_uuid_),
        pid_(pid) {
    // Add process descriptor
    auto* packet = create_packet();

    auto* desc = packet->mutable_track_descriptor();
    desc->set_uuid(process_uuid_);
    desc->set_name(std::string(process_name));

    auto* process = desc->mutable_process();
    process->set_pid(pid_);
    process->set_process_name(std::string(process_name));

    // Store metadata
    track_names_[process_uuid_] = std::string(process_name);
  }

  ~PerfettoTraceBuilder() = default;

  // Non-copyable, non-moveable (due to atomic members)
  PerfettoTraceBuilder(const PerfettoTraceBuilder&) = delete;
  PerfettoTraceBuilder& operator=(const PerfettoTraceBuilder&) = delete;
  PerfettoTraceBuilder(PerfettoTraceBuilder&&) = delete;
  PerfettoTraceBuilder& operator=(PerfettoTraceBuilder&&) = delete;

  // Track management
  [[nodiscard]] uint64_t add_thread(std::string_view name) {
    uint64_t uuid = ++last_track_uuid_;
    uint64_t tid = ++last_thread_tid_;

    auto* packet = create_packet();

    auto* desc = packet->mutable_track_descriptor();
    desc->set_uuid(uuid);
    desc->set_name(std::string(name));

    auto* thread = desc->mutable_thread();
    thread->set_pid(pid_);
    thread->set_tid(static_cast<int32_t>(tid));
    thread->set_thread_name(std::string(name));

    // Store metadata
    track_names_[uuid] = std::string(name);
    track_parents_[uuid] = process_uuid_;

    return uuid;
  }

  [[nodiscard]] uint64_t add_track(
      std::string_view name,
      std::optional<uint64_t> parent_uuid = std::nullopt,
      std::optional<SiblingMergeBehavior> sibling_merge_behavior = std::nullopt,
      std::optional<std::string_view> sibling_merge_key = std::nullopt,
      std::optional<uint64_t> sibling_merge_key_int = std::nullopt) {
    if (sibling_merge_key && sibling_merge_key_int) {
      throw std::invalid_argument("only one sibling merge key may be set");
    }
    if ((sibling_merge_key || sibling_merge_key_int) &&
        !sibling_merge_behavior) {
      sibling_merge_behavior = perfetto::protos::TrackDescriptor::
          SIBLING_MERGE_BEHAVIOR_BY_SIBLING_MERGE_KEY;
    }
    if ((sibling_merge_key || sibling_merge_key_int) &&
        sibling_merge_behavior !=
            perfetto::protos::TrackDescriptor::
                SIBLING_MERGE_BEHAVIOR_BY_SIBLING_MERGE_KEY) {
      throw std::invalid_argument(
          "sibling merge keys require BY_SIBLING_MERGE_KEY");
    }
    const uint64_t uuid = ++last_track_uuid_;
    auto* descriptor = create_packet()->mutable_track_descriptor();
    descriptor->set_uuid(uuid);
    descriptor->set_parent_uuid(parent_uuid.value_or(process_uuid_));
    descriptor->set_name(std::string(name));
    if (sibling_merge_behavior) {
      descriptor->set_sibling_merge_behavior(*sibling_merge_behavior);
    }
    if (sibling_merge_key) {
      descriptor->set_sibling_merge_key(std::string(*sibling_merge_key));
    } else if (sibling_merge_key_int) {
      descriptor->set_sibling_merge_key_int(*sibling_merge_key_int);
    }
    track_names_[uuid] = std::string(name);
    track_parents_[uuid] = parent_uuid.value_or(process_uuid_);
    return uuid;
  }

  [[nodiscard]] uint64_t add_merged_track_lane(
      std::string_view name,
      std::string_view sibling_merge_key,
      std::optional<uint64_t> parent_uuid = std::nullopt) {
    return add_track(name, parent_uuid, std::nullopt, sibling_merge_key);
  }

  [[nodiscard]] uint64_t add_merged_track_lane(
      std::string_view name,
      uint64_t sibling_merge_key,
      std::optional<uint64_t> parent_uuid = std::nullopt) {
    return add_track(name, parent_uuid, std::nullopt, std::nullopt,
                     sibling_merge_key);
  }

  [[nodiscard]] uint64_t add_counter_track(std::string_view name,
                                           std::string_view unit) {
    uint64_t uuid = ++last_track_uuid_;

    auto* packet = create_packet();

    auto* desc = packet->mutable_track_descriptor();
    desc->set_uuid(uuid);
    desc->set_name(std::string(name));
    desc->set_parent_uuid(process_uuid_);

    // For counters, we just use a regular track descriptor
    // The unit information could be added to the name if needed
    if (!unit.empty()) {
      desc->set_name(std::string(name) + " (" + std::string(unit) + ")");
    }

    // Store metadata
    track_names_[uuid] = std::string(name);
    track_parents_[uuid] = process_uuid_;

    return uuid;
  }

  // Event creation
  [[nodiscard]] TrackEventWrapper begin_slice(
      uint64_t track_uuid,
      std::string_view name,
      uint64_t timestamp_ns,
      std::optional<uint32_t> timestamp_clock_id = std::nullopt);

  void end_slice(uint64_t track_uuid,
                 uint64_t timestamp_ns,
                 std::optional<uint32_t> timestamp_clock_id = std::nullopt) {
    auto* packet = create_packet(timestamp_ns, timestamp_clock_id);

    auto* event = packet->mutable_track_event();
    event->set_type(perfetto::protos::TrackEvent::TYPE_SLICE_END);
    event->set_track_uuid(track_uuid);
  }

  [[nodiscard]] TrackEventWrapper add_instant_event(
      uint64_t track_uuid,
      std::string_view name,
      uint64_t timestamp_ns,
      std::optional<uint32_t> timestamp_clock_id = std::nullopt);

  [[nodiscard]] TrackEventWrapper add_flow(
      uint64_t track_uuid,
      std::string_view name,
      uint64_t timestamp_ns,
      uint64_t flow_id,
      bool terminating = false,
      std::optional<uint32_t> timestamp_clock_id = std::nullopt);

  [[nodiscard]] TrackEventWrapper add_legacy_event(
      uint64_t track_uuid,
      std::string_view name,
      uint64_t timestamp_ns,
      const LegacyEvent& legacy,
      std::optional<uint32_t> timestamp_clock_id = std::nullopt);

  void set_default_timestamp_clock(uint32_t clock_id) {
    auto* packet = create_packet();
    packet->mutable_trace_packet_defaults()->set_timestamp_clock_id(clock_id);
  }

  void add_clock_snapshot(const std::vector<ClockReading>& readings,
                          std::optional<perfetto::protos::BuiltinClock>
                              primary_trace_clock = std::nullopt) {
    if (readings.empty()) {
      throw std::invalid_argument("a clock snapshot requires a reading");
    }
    auto* snapshot = create_packet()->mutable_clock_snapshot();
    if (primary_trace_clock) {
      snapshot->set_primary_trace_clock(*primary_trace_clock);
    }
    for (const auto& reading : readings) {
      if (reading.unit_multiplier_ns && primary_trace_clock &&
          reading.clock_id == static_cast<uint32_t>(*primary_trace_clock)) {
        throw std::invalid_argument(
            "unit_multiplier_ns is unsupported on the primary trace clock");
      }
      auto* clock = snapshot->add_clocks();
      clock->set_clock_id(reading.clock_id);
      clock->set_timestamp(reading.timestamp);
      if (reading.is_incremental) {
        clock->set_is_incremental(*reading.is_incremental);
      }
      if (reading.unit_multiplier_ns) {
        clock->set_unit_multiplier_ns(*reading.unit_multiplier_ns);
      }
    }
  }

  void add_frame_timeline_expected_surface_start(
      uint64_t timestamp_ns,
      const FrameTimelineExpectedSurfaceFrameStart& frame) {
    auto* packet = create_packet(timestamp_ns);
    auto* event = packet->mutable_frame_timeline_event()
                      ->mutable_expected_surface_frame_start();
    event->set_cookie(frame.cookie);
    event->set_token(frame.token);
    event->set_display_frame_token(frame.display_frame_token);
    event->set_pid(frame.pid.value_or(pid_));
    if (!frame.layer_name.empty()) {
      event->set_layer_name(frame.layer_name);
    }
  }

  void add_frame_timeline_actual_surface_start(
      uint64_t timestamp_ns,
      const FrameTimelineActualSurfaceFrameStart& frame) {
    auto* packet = create_packet(timestamp_ns);
    auto* event = packet->mutable_frame_timeline_event()
                      ->mutable_actual_surface_frame_start();
    event->set_cookie(frame.cookie);
    event->set_token(frame.token);
    event->set_display_frame_token(frame.display_frame_token);
    event->set_pid(frame.pid.value_or(pid_));
    if (!frame.layer_name.empty()) {
      event->set_layer_name(frame.layer_name);
    }
    if (frame.present_type) {
      event->set_present_type(*frame.present_type);
    }
    if (frame.on_time_finish) {
      event->set_on_time_finish(*frame.on_time_finish);
    }
    if (frame.gpu_composition) {
      event->set_gpu_composition(*frame.gpu_composition);
    }
    if (frame.jank_type) {
      event->set_jank_type(*frame.jank_type);
    }
    if (frame.prediction_type) {
      event->set_prediction_type(*frame.prediction_type);
    }
    if (frame.is_buffer) {
      event->set_is_buffer(*frame.is_buffer);
    }
    if (frame.jank_severity_type) {
      event->set_jank_severity_type(*frame.jank_severity_type);
    }
    if (frame.present_delay_millis) {
      event->set_present_delay_millis(*frame.present_delay_millis);
    }
    if (frame.vsync_resynced_jitter_millis) {
      event->set_vsync_resynced_jitter_millis(
          *frame.vsync_resynced_jitter_millis);
    }
    if (frame.jank_severity_score) {
      event->set_jank_severity_score(*frame.jank_severity_score);
    }
    if (frame.jank_type_experimental) {
      event->set_jank_type_experimental(*frame.jank_type_experimental);
    }
    if (frame.present_type_experimental) {
      event->set_present_type_experimental(*frame.present_type_experimental);
    }
    if (frame.jank_debug_metadata) {
      event->set_jank_debug_metadata(*frame.jank_debug_metadata);
    }
    if (frame.latched_fence_state) {
      event->set_latched_fence_state(*frame.latched_fence_state);
    }
    if (frame.animation_time_millis) {
      event->set_animation_time_millis(*frame.animation_time_millis);
    }
  }

  void add_frame_timeline_expected_display_start(
      uint64_t timestamp_ns,
      const FrameTimelineExpectedDisplayFrameStart& frame) {
    auto* packet = create_packet(timestamp_ns);
    auto* event = packet->mutable_frame_timeline_event()
                      ->mutable_expected_display_frame_start();
    event->set_cookie(frame.cookie);
    event->set_token(frame.token);
    event->set_pid(frame.pid.value_or(pid_));
  }

  void add_frame_timeline_actual_display_start(
      uint64_t timestamp_ns,
      const FrameTimelineActualDisplayFrameStart& frame) {
    auto* packet = create_packet(timestamp_ns);
    auto* event = packet->mutable_frame_timeline_event()
                      ->mutable_actual_display_frame_start();
    event->set_cookie(frame.cookie);
    event->set_token(frame.token);
    event->set_pid(frame.pid.value_or(pid_));
    if (frame.present_type) {
      event->set_present_type(*frame.present_type);
    }
    if (frame.on_time_finish) {
      event->set_on_time_finish(*frame.on_time_finish);
    }
    if (frame.gpu_composition) {
      event->set_gpu_composition(*frame.gpu_composition);
    }
    if (frame.jank_type) {
      event->set_jank_type(*frame.jank_type);
    }
    if (frame.prediction_type) {
      event->set_prediction_type(*frame.prediction_type);
    }
    if (frame.jank_severity_type) {
      event->set_jank_severity_type(*frame.jank_severity_type);
    }
    if (frame.present_delay_millis) {
      event->set_present_delay_millis(*frame.present_delay_millis);
    }
    if (frame.jank_severity_score) {
      event->set_jank_severity_score(*frame.jank_severity_score);
    }
    if (frame.jank_type_experimental) {
      event->set_jank_type_experimental(*frame.jank_type_experimental);
    }
    if (frame.present_type_experimental) {
      event->set_present_type_experimental(*frame.present_type_experimental);
    }
    if (frame.jank_debug_metadata) {
      event->set_jank_debug_metadata(*frame.jank_debug_metadata);
    }
    if (frame.latched_unsignaled_count) {
      event->set_latched_unsignaled_count(*frame.latched_unsignaled_count);
    }
    if (frame.addressable_unsignaled_latch_count) {
      event->set_addressable_unsignaled_latch_count(
          *frame.addressable_unsignaled_latch_count);
    }
  }

  void end_frame_timeline(uint64_t timestamp_ns, int64_t cookie) {
    auto* packet = create_packet(timestamp_ns);
    packet->mutable_frame_timeline_event()->mutable_frame_end()->set_cookie(
        cookie);
  }

  void update_counter(
      uint64_t track_uuid,
      double value,
      uint64_t timestamp_ns,
      std::optional<uint32_t> timestamp_clock_id = std::nullopt) {
    auto* packet = create_packet(timestamp_ns, timestamp_clock_id);

    auto* event = packet->mutable_track_event();
    event->set_type(perfetto::protos::TrackEvent::TYPE_COUNTER);
    event->set_track_uuid(track_uuid);

    const double min_int64 =
        static_cast<double>(std::numeric_limits<int64_t>::min());
    const double max_int64 =
        static_cast<double>(std::numeric_limits<int64_t>::max());

    if (std::isfinite(value) && value >= min_int64 && value <= max_int64) {
      const double truncated = std::trunc(value);
      if (truncated == value) {
        event->set_counter_value(static_cast<int64_t>(truncated));
        return;
      }
    }

    event->set_double_counter_value(value);
  }

  // Serialization
  void save(const std::filesystem::path& path) const {
    std::ofstream file(path, std::ios::binary);
    if (!file) {
      throw std::runtime_error("Failed to open file: " + path.string());
    }

    if (!trace_->SerializeToOstream(&file)) {
      throw std::runtime_error("Failed to serialize trace");
    }
  }

  [[nodiscard]] std::vector<uint8_t> serialize() const {
    std::vector<uint8_t> data;
    data.resize(trace_->ByteSizeLong());

    if (!trace_->SerializeToArray(data.data(), static_cast<int>(data.size()))) {
      throw std::runtime_error("Failed to serialize trace");
    }

    return data;
  }

  // Metadata queries
  [[nodiscard]] std::optional<std::string_view> get_track_name(
      uint64_t track_uuid) const {
    auto it = track_names_.find(track_uuid);
    if (it != track_names_.end()) {
      return it->second;
    }
    return std::nullopt;
  }

  [[nodiscard]] std::vector<std::pair<uint64_t, std::string>> get_all_tracks()
      const {
    std::vector<std::pair<uint64_t, std::string>> result;
    result.reserve(track_names_.size());

    for (const auto& [uuid, name] : track_names_) {
      result.emplace_back(uuid, name);
    }

    return result;
  }

 private:
};

// Wrapper for track events to enable annotation chaining
class TrackEventWrapper {
 private:
  friend class PerfettoTraceBuilder;
  perfetto::protos::TracePacket* packet_;
  perfetto::protos::TrackEvent* event_;
  detail::InterningState* interning_state_;

  explicit TrackEventWrapper(perfetto::protos::TracePacket* packet,
                             perfetto::protos::TrackEvent* event,
                             detail::InterningState* interning_state)
      : packet_(packet), event_(event), interning_state_(interning_state) {}

 public:
  // Individual annotation methods
  TrackEventWrapper& add_annotation(std::string_view key, int64_t value) {
    auto* annotation = event_->add_debug_annotations();
    if (interning_state_) {
      annotation->set_name_iid(
          interning_state_->intern_debug_annotation_name(key, packet_));
    } else {
      annotation->set_name(std::string(key));
    }

    // Check if this should be a pointer based on key name
    if (detail::is_pointer_key(key)) {
      annotation->set_pointer_value(static_cast<uint64_t>(value));
    } else {
      annotation->set_int_value(value);
    }

    return *this;
  }

  TrackEventWrapper& add_annotation(std::string_view key, uint64_t value) {
    auto* annotation = event_->add_debug_annotations();
    if (interning_state_) {
      annotation->set_name_iid(
          interning_state_->intern_debug_annotation_name(key, packet_));
    } else {
      annotation->set_name(std::string(key));
    }
    if (detail::is_pointer_key(key)) {
      annotation->set_pointer_value(value);
    } else {
      annotation->set_uint_value(value);
    }
    return *this;
  }

  TrackEventWrapper& add_annotation(std::string_view key, int value) {
    return add_annotation(key, static_cast<int64_t>(value));
  }

  TrackEventWrapper& add_annotation(std::string_view key, double value) {
    auto* annotation = event_->add_debug_annotations();
    if (interning_state_) {
      annotation->set_name_iid(
          interning_state_->intern_debug_annotation_name(key, packet_));
    } else {
      annotation->set_name(std::string(key));
    }
    annotation->set_double_value(value);
    return *this;
  }

  TrackEventWrapper& add_annotation(std::string_view key, bool value) {
    auto* annotation = event_->add_debug_annotations();
    if (interning_state_) {
      annotation->set_name_iid(
          interning_state_->intern_debug_annotation_name(key, packet_));
    } else {
      annotation->set_name(std::string(key));
    }
    annotation->set_bool_value(value);
    return *this;
  }

  TrackEventWrapper& add_annotation(std::string_view key,
                                    std::string_view value) {
    auto* annotation = event_->add_debug_annotations();
    if (interning_state_) {
      annotation->set_name_iid(
          interning_state_->intern_debug_annotation_name(key, packet_));
      annotation->set_string_value_iid(
          interning_state_->intern_debug_annotation_string_value(value,
                                                                 packet_));
    } else {
      annotation->set_name(std::string(key));
      annotation->set_string_value(std::string(value));
    }
    return *this;
  }

  TrackEventWrapper& add_annotation(std::string_view key, const char* value) {
    return add_annotation(key, std::string_view(value));
  }

  // Pointer annotation with automatic formatting
  TrackEventWrapper& add_pointer(std::string_view key, uint64_t address) {
    auto* annotation = event_->add_debug_annotations();
    if (interning_state_) {
      annotation->set_name_iid(
          interning_state_->intern_debug_annotation_name(key, packet_));
    } else {
      annotation->set_name(std::string(key));
    }
    annotation->set_pointer_value(address);
    return *this;
  }

  TrackEventWrapper& add_category(std::string_view category) {
    if (interning_state_) {
      event_->add_category_iids(
          interning_state_->intern_event_category(category, packet_));
    } else {
      event_->add_categories(std::string(category));
    }
    return *this;
  }

  TrackEventWrapper& set_source_location(const SourceLocation& location,
                                         bool intern = true) {
    if (intern && interning_state_) {
      event_->set_source_location_iid(
          interning_state_->intern_source_location(location, packet_));
    } else {
      auto* target = event_->mutable_source_location();
      if (!location.file_name.empty()) {
        target->set_file_name(location.file_name);
      }
      if (!location.function_name.empty()) {
        target->set_function_name(location.function_name);
      }
      if (location.line_number) {
        target->set_line_number(*location.line_number);
      }
    }
    return *this;
  }

  TrackEventWrapper& set_inline_callstack(
      const std::vector<InlineFrame>& frames) {
    auto* callstack = event_->mutable_callstack();
    for (const auto& frame : frames) {
      auto* target = callstack->add_frames();
      target->set_function_name(frame.function_name);
      if (frame.source_file) {
        target->set_source_file(*frame.source_file);
      }
      if (frame.line_number) {
        target->set_line_number(*frame.line_number);
      }
    }
    return *this;
  }

  TrackEventWrapper& set_callstack(const std::vector<StackFrame>& frames) {
    if (!interning_state_) {
      throw std::logic_error("native callstacks require interning");
    }
    event_->set_callstack_iid(
        interning_state_->intern_callstack(frames, packet_));
    return *this;
  }

  // RAII annotation context
  [[nodiscard]] AnnotationBuilder annotation(std::string_view name);

  // Variadic template for multiple annotations
  template <typename... Args>
  TrackEventWrapper& add_annotations(Args&&... args) {
    static_assert(sizeof...(args) % 2 == 0,
                  "Annotations must be key-value pairs");
    add_annotations_impl(std::forward<Args>(args)...);
    return *this;
  }

 private:
  // Base case for recursion
  void add_annotations_impl() {}

  // Recursive case
  template <typename Key, typename Value, typename... Rest>
  void add_annotations_impl(Key&& key, Value&& value, Rest&&... rest) {
    add_annotation(std::forward<Key>(key), std::forward<Value>(value));
    add_annotations_impl(std::forward<Rest>(rest)...);
  }
};

// Builder for nested annotations
class AnnotationBuilder {
 private:
  friend class TrackEventWrapper;
  friend class AnnotationArrayBuilder;
  perfetto::protos::DebugAnnotation* annotation_;
  perfetto::protos::TracePacket* packet_;
  detail::InterningState* interning_state_;
  std::size_t depth_;

  AnnotationBuilder(perfetto::protos::DebugAnnotation* annotation,
                    perfetto::protos::TracePacket* packet,
                    detail::InterningState* interning_state,
                    std::size_t depth = 0)
      : annotation_(annotation),
        packet_(packet),
        interning_state_(interning_state),
        depth_(depth) {}

  perfetto::protos::DebugAnnotation* add_entry(std::string_view key) {
    if (annotation_) {
      auto* entry = annotation_->add_dict_entries();
      if (interning_state_) {
        entry->set_name_iid(
            interning_state_->intern_debug_annotation_name(key, packet_));
      } else {
        entry->set_name(std::string(key));
      }
      return entry;
    }
    return nullptr;
  }

 public:
  explicit AnnotationBuilder(perfetto::protos::DebugAnnotation* annotation)
      : AnnotationBuilder(annotation, nullptr, nullptr, 0) {}

  // Typed annotation methods
  AnnotationBuilder& integer(std::string_view key, int64_t value) {
    if (auto* entry = add_entry(key)) {
      entry->set_int_value(value);
    }
    return *this;
  }

  AnnotationBuilder& unsigned_integer(std::string_view key, uint64_t value) {
    if (auto* entry = add_entry(key)) {
      entry->set_uint_value(value);
    }
    return *this;
  }

  AnnotationBuilder& floating(std::string_view key, double value) {
    if (auto* entry = add_entry(key)) {
      entry->set_double_value(value);
    }
    return *this;
  }

  AnnotationBuilder& boolean(std::string_view key, bool value) {
    if (auto* entry = add_entry(key)) {
      entry->set_bool_value(value);
    }
    return *this;
  }

  AnnotationBuilder& string(std::string_view key, std::string_view value) {
    if (auto* entry = add_entry(key)) {
      if (interning_state_) {
        entry->set_string_value_iid(
            interning_state_->intern_debug_annotation_string_value(value,
                                                                   packet_));
      } else {
        entry->set_string_value(std::string(value));
      }
    }
    return *this;
  }

  AnnotationBuilder& pointer(std::string_view key, uint64_t address) {
    if (auto* entry = add_entry(key)) {
      entry->set_pointer_value(address);
    }
    return *this;
  }

  // Nested annotations - creates another level
  [[nodiscard]] AnnotationBuilder nested(std::string_view key) {
    if (depth_ >= 64) {
      throw std::length_error("debug annotation nesting exceeds 64 levels");
    }
    if (auto* entry = add_entry(key)) {
      return AnnotationBuilder(entry, packet_, interning_state_, depth_ + 1);
    }
    return AnnotationBuilder(nullptr, nullptr, nullptr);
  }

  [[nodiscard]] AnnotationArrayBuilder array(std::string_view key);
};

// Builder for recursively nested annotation arrays. Array elements do not have
// names, matching DebugAnnotation.array_values in upstream Perfetto.
class AnnotationArrayBuilder {
 private:
  friend class AnnotationBuilder;
  perfetto::protos::DebugAnnotation* annotation_;
  perfetto::protos::TracePacket* packet_;
  detail::InterningState* interning_state_;
  std::size_t depth_;

  AnnotationArrayBuilder(perfetto::protos::DebugAnnotation* annotation,
                         perfetto::protos::TracePacket* packet,
                         detail::InterningState* interning_state,
                         std::size_t depth)
      : annotation_(annotation),
        packet_(packet),
        interning_state_(interning_state),
        depth_(depth) {}

  perfetto::protos::DebugAnnotation* add_value() {
    return annotation_ ? annotation_->add_array_values() : nullptr;
  }

  void require_nested_depth() const {
    if (depth_ >= 64) {
      throw std::length_error("debug annotation nesting exceeds 64 levels");
    }
  }

 public:
  AnnotationArrayBuilder& integer(int64_t value) {
    if (auto* entry = add_value()) {
      entry->set_int_value(value);
    }
    return *this;
  }

  AnnotationArrayBuilder& unsigned_integer(uint64_t value) {
    if (auto* entry = add_value()) {
      entry->set_uint_value(value);
    }
    return *this;
  }

  AnnotationArrayBuilder& floating(double value) {
    if (auto* entry = add_value()) {
      entry->set_double_value(value);
    }
    return *this;
  }

  AnnotationArrayBuilder& boolean(bool value) {
    if (auto* entry = add_value()) {
      entry->set_bool_value(value);
    }
    return *this;
  }

  AnnotationArrayBuilder& string(std::string_view value) {
    if (auto* entry = add_value()) {
      if (interning_state_) {
        entry->set_string_value_iid(
            interning_state_->intern_debug_annotation_string_value(value,
                                                                   packet_));
      } else {
        entry->set_string_value(std::string(value));
      }
    }
    return *this;
  }

  AnnotationArrayBuilder& pointer(uint64_t value) {
    if (auto* entry = add_value()) {
      entry->set_pointer_value(value);
    }
    return *this;
  }

  [[nodiscard]] AnnotationBuilder dictionary() {
    require_nested_depth();
    return AnnotationBuilder(add_value(), packet_, interning_state_,
                             depth_ + 1);
  }

  [[nodiscard]] AnnotationArrayBuilder array() {
    require_nested_depth();
    return AnnotationArrayBuilder(add_value(), packet_, interning_state_,
                                  depth_ + 1);
  }
};

inline AnnotationArrayBuilder AnnotationBuilder::array(std::string_view key) {
  if (depth_ >= 64) {
    throw std::length_error("debug annotation nesting exceeds 64 levels");
  }
  return AnnotationArrayBuilder(add_entry(key), packet_, interning_state_,
                                depth_ + 1);
}

// Implementation of deferred methods
inline TrackEventWrapper PerfettoTraceBuilder::begin_slice(
    uint64_t track_uuid,
    std::string_view name,
    uint64_t timestamp_ns,
    std::optional<uint32_t> timestamp_clock_id) {
  auto* packet = create_packet(timestamp_ns, timestamp_clock_id);

  auto* event = packet->mutable_track_event();
  event->set_type(perfetto::protos::TrackEvent::TYPE_SLICE_BEGIN);
  event->set_track_uuid(track_uuid);
  event->set_name_iid(interning_state_.intern_event_name(name, packet));

  return TrackEventWrapper(packet, event, &interning_state_);
}

inline TrackEventWrapper PerfettoTraceBuilder::add_instant_event(
    uint64_t track_uuid,
    std::string_view name,
    uint64_t timestamp_ns,
    std::optional<uint32_t> timestamp_clock_id) {
  auto* packet = create_packet(timestamp_ns, timestamp_clock_id);

  auto* event = packet->mutable_track_event();
  event->set_type(perfetto::protos::TrackEvent::TYPE_INSTANT);
  event->set_track_uuid(track_uuid);
  event->set_name_iid(interning_state_.intern_event_name(name, packet));

  return TrackEventWrapper(packet, event, &interning_state_);
}

inline TrackEventWrapper PerfettoTraceBuilder::add_flow(
    uint64_t track_uuid,
    std::string_view name,
    uint64_t timestamp_ns,
    uint64_t flow_id,
    bool terminating,
    std::optional<uint32_t> timestamp_clock_id) {
  auto* packet = create_packet(timestamp_ns, timestamp_clock_id);

  auto* event = packet->mutable_track_event();
  event->set_type(perfetto::protos::TrackEvent::TYPE_INSTANT);
  event->set_track_uuid(track_uuid);
  event->set_name_iid(interning_state_.intern_event_name(name, packet));

  if (terminating) {
    event->add_terminating_flow_ids(flow_id);
  } else {
    event->add_flow_ids(flow_id);
  }

  return TrackEventWrapper(packet, event, &interning_state_);
}

inline TrackEventWrapper PerfettoTraceBuilder::add_legacy_event(
    uint64_t track_uuid,
    std::string_view name,
    uint64_t timestamp_ns,
    const LegacyEvent& legacy,
    std::optional<uint32_t> timestamp_clock_id) {
  auto* packet = create_packet(timestamp_ns, timestamp_clock_id);
  auto* event = packet->mutable_track_event();
  event->set_track_uuid(track_uuid);
  event->set_name_iid(interning_state_.intern_event_name(name, packet));
  auto* target = event->mutable_legacy_event();
  target->set_phase(legacy.phase);
  if (legacy.duration_us) {
    target->set_duration_us(*legacy.duration_us);
  }
  if (legacy.thread_duration_us) {
    target->set_thread_duration_us(*legacy.thread_duration_us);
  }
  if (legacy.thread_instruction_delta) {
    target->set_thread_instruction_delta(*legacy.thread_instruction_delta);
  }
  if (legacy.id) {
    switch (legacy.id_type) {
      case LegacyIdType::kUnscoped:
        target->set_unscoped_id(*legacy.id);
        break;
      case LegacyIdType::kLocal:
        target->set_local_id(*legacy.id);
        break;
      case LegacyIdType::kGlobal:
        target->set_global_id(*legacy.id);
        break;
    }
  }
  if (legacy.id_scope) {
    target->set_id_scope(*legacy.id_scope);
  }
  if (legacy.use_async_tts) {
    target->set_use_async_tts(*legacy.use_async_tts);
  }
  if (legacy.bind_id) {
    target->set_bind_id(*legacy.bind_id);
  }
  if (legacy.bind_to_enclosing) {
    target->set_bind_to_enclosing(*legacy.bind_to_enclosing);
  }
  if (legacy.flow_direction) {
    target->set_flow_direction(*legacy.flow_direction);
  }
  if (legacy.instant_event_scope) {
    target->set_instant_event_scope(*legacy.instant_event_scope);
  }
  if (legacy.pid_override) {
    target->set_pid_override(*legacy.pid_override);
  }
  if (legacy.tid_override) {
    target->set_tid_override(*legacy.tid_override);
  }
  return TrackEventWrapper(packet, event, &interning_state_);
}

inline AnnotationBuilder TrackEventWrapper::annotation(std::string_view name) {
  auto* annotation = event_->add_debug_annotations();
  if (interning_state_) {
    annotation->set_name_iid(
        interning_state_->intern_debug_annotation_name(name, packet_));
    return AnnotationBuilder(annotation, packet_, interning_state_);
  }
  annotation->set_name(std::string(name));
  return AnnotationBuilder(annotation);
}

// Resolve interned IDs to inline strings in-place (for debugging/diff tooling).
inline void resolve_interned_trace_inplace(perfetto::protos::Trace& trace) {
  std::unordered_map<uint32_t, detail::SequenceInternTables>
      tables_by_sequence = {};

  for (auto& packet : *trace.mutable_packet()) {
    const auto flags = packet.sequence_flags();
    detail::SequenceInternTables* tables = nullptr;
    const bool has_valid_sequence_id =
        packet.has_trusted_packet_sequence_id() &&
        packet.trusted_packet_sequence_id() != 0;

    if (has_valid_sequence_id) {
      auto& sequence_tables =
          tables_by_sequence[packet.trusted_packet_sequence_id()];
      tables = &sequence_tables;

      if (packet.previous_packet_dropped()) {
        tables->clear(false);
      }

      if ((flags &
           perfetto::protos::TracePacket::SEQ_INCREMENTAL_STATE_CLEARED) != 0) {
        tables->clear(true);
      }

      if (packet.has_interned_data()) {
        const auto& interned = packet.interned_data();
        for (const auto& entry : interned.event_categories()) {
          tables->event_categories[entry.iid()] = entry.name();
        }
        for (const auto& entry : interned.event_names()) {
          tables->event_names[entry.iid()] = entry.name();
        }
        for (const auto& entry : interned.debug_annotation_names()) {
          tables->debug_annotation_names[entry.iid()] = entry.name();
        }
        for (const auto& entry : interned.debug_annotation_string_values()) {
          tables->debug_annotation_string_values[entry.iid()] = entry.str();
        }
        for (const auto& entry : interned.source_locations()) {
          tables->source_locations[entry.iid()] = entry;
        }
      }
    }

    if (!packet.has_track_event()) {
      continue;
    }
    if (!tables) {
      continue;
    }

    const bool needs_state =
        (flags & perfetto::protos::TracePacket::SEQ_NEEDS_INCREMENTAL_STATE) !=
        0;
    if (needs_state && !tables->valid) {
      continue;
    }

    auto* event = packet.mutable_track_event();
    if (event->name_field_case() == perfetto::protos::TrackEvent::kNameIid) {
      const auto iid = event->name_iid();
      const auto it = tables->event_names.find(iid);
      event->set_name(it != tables->event_names.end()
                          ? it->second
                          : detail::make_missing_iid_string("EventName", iid));
    }

    if (event->category_iids_size() != 0) {
      for (const auto iid : event->category_iids()) {
        const auto it = tables->event_categories.find(iid);
        event->add_categories(
            it != tables->event_categories.end()
                ? it->second
                : detail::make_missing_iid_string("EventCategory", iid));
      }
      event->clear_category_iids();
    }

    if (event->source_location_field_case() ==
        perfetto::protos::TrackEvent::kSourceLocationIid) {
      const auto iid = event->source_location_iid();
      const auto it = tables->source_locations.find(iid);
      if (it != tables->source_locations.end()) {
        event->mutable_source_location()->CopyFrom(it->second);
      }
    }

    for (auto& annotation : *event->mutable_debug_annotations()) {
      detail::resolve_debug_annotation_inplace(annotation, *tables);
    }
  }
}

// Return a copy with interned IDs resolved to inline strings.
[[nodiscard]] inline perfetto::protos::Trace resolve_interned_trace(
    const perfetto::protos::Trace& trace) {
  auto resolved = trace;
  resolve_interned_trace_inplace(resolved);
  return resolved;
}

}  // namespace retrobus
