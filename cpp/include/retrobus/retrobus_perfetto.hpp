// retrobus_perfetto.hpp - Header-only C++ library for creating Perfetto traces
// Copyright (c) 2024 - MIT License

#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <memory>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

// Include protobuf headers - users must provide these
#include <google/protobuf/message.h>

// Generated protobuf headers - users must generate these from perfetto.proto
#include "perfetto.pb.h"

namespace retrobus {

// Forward declarations
class TrackEventWrapper;
class AnnotationBuilder;

// Utility functions
namespace detail {
    // Default values for trace generation
    constexpr uint64_t DEFAULT_THREAD_TID = 1000;
    constexpr int32_t DEFAULT_PROCESS_PID = 1234;
    // Pointer heuristic detection
    inline bool is_pointer_key(std::string_view key) {
        // Check suffixes (C++17 compatible)
        const std::array<std::string_view, 5> suffixes = {"_addr", "_address", "_pc", "_sp", "_pointer"};
        for (const auto& suffix : suffixes) {
            if (key.size() >= suffix.size() && 
                key.substr(key.size() - suffix.size()) == suffix) {
                return true;
            }
        }
        
        // Check exact matches
        return key == "pc" || key == "sp" || key == "address";
    }
} // namespace detail

// Main trace builder class
class PerfettoTraceBuilder {
private:
    std::unique_ptr<perfetto::protos::Trace> trace_;
    std::atomic<uint64_t> last_track_uuid_{0};
    std::atomic<uint64_t> last_thread_tid_{detail::DEFAULT_THREAD_TID};
    uint64_t process_uuid_;
    int32_t pid_;
    uint32_t trusted_packet_sequence_id_{1};
    
    // Metadata tracking
    std::unordered_map<uint64_t, std::string> track_names_;
    std::unordered_map<uint64_t, uint64_t> track_parents_;
    
    // Helpers to add new packets with consistent initialization
    perfetto::protos::TracePacket* create_packet() {
        auto* packet = trace_->add_packet();
        packet->set_trusted_packet_sequence_id(trusted_packet_sequence_id_);
        return packet;
    }

    perfetto::protos::TracePacket* create_packet(uint64_t timestamp_ns) {
        auto* packet = create_packet();
        packet->set_timestamp(timestamp_ns);
        return packet;
    }
    
public:
    explicit PerfettoTraceBuilder(std::string_view process_name, int32_t pid = detail::DEFAULT_PROCESS_PID)
        : trace_(std::make_unique<perfetto::protos::Trace>())
        , process_uuid_(++last_track_uuid_)
        , pid_(pid) {
        
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
    
    [[nodiscard]] uint64_t add_counter_track(std::string_view name, std::string_view unit) {
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
    [[nodiscard]] TrackEventWrapper begin_slice(uint64_t track_uuid, std::string_view name, uint64_t timestamp_ns);
    
    void end_slice(uint64_t track_uuid, uint64_t timestamp_ns) {
        auto* packet = create_packet(timestamp_ns);
        
        auto* event = packet->mutable_track_event();
        event->set_type(perfetto::protos::TrackEvent::TYPE_SLICE_END);
        event->set_track_uuid(track_uuid);
    }
    
    [[nodiscard]] TrackEventWrapper add_instant_event(uint64_t track_uuid, std::string_view name, uint64_t timestamp_ns);
    
    [[nodiscard]] TrackEventWrapper add_flow(uint64_t track_uuid, std::string_view name, uint64_t timestamp_ns,
                                              uint64_t flow_id, bool terminating = false);
    
    void update_counter(uint64_t track_uuid, double value, uint64_t timestamp_ns) {
        auto* packet = create_packet(timestamp_ns);
        
        auto* event = packet->mutable_track_event();
        event->set_type(perfetto::protos::TrackEvent::TYPE_COUNTER);
        event->set_track_uuid(track_uuid);
        
        // Check if it's an integer value
        if (value == static_cast<double>(static_cast<int64_t>(value))) {
            event->set_counter_value(static_cast<int64_t>(value));
        } else {
            event->set_double_counter_value(value);
        }
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
    [[nodiscard]] std::optional<std::string_view> get_track_name(uint64_t track_uuid) const {
        auto it = track_names_.find(track_uuid);
        if (it != track_names_.end()) {
            return it->second;
        }
        return std::nullopt;
    }
    
    [[nodiscard]] std::vector<std::pair<uint64_t, std::string>> get_all_tracks() const {
        std::vector<std::pair<uint64_t, std::string>> result;
        result.reserve(track_names_.size());
        
        for (const auto& [uuid, name] : track_names_) {
            result.emplace_back(uuid, name);
        }
        
        return result;
    }
};

// Wrapper for track events to enable annotation chaining
class TrackEventWrapper {
private:
    friend class PerfettoTraceBuilder;
    perfetto::protos::TrackEvent* event_;
    
    explicit TrackEventWrapper(perfetto::protos::TrackEvent* event) : event_(event) {}
    
public:
    // Individual annotation methods
    TrackEventWrapper& add_annotation(std::string_view key, int64_t value) {
        auto* annotation = event_->add_debug_annotations();
        annotation->set_name(std::string(key));
        
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
        annotation->set_name(std::string(key));
        annotation->set_pointer_value(value);
        return *this;
    }
    
    TrackEventWrapper& add_annotation(std::string_view key, int value) {
        return add_annotation(key, static_cast<int64_t>(value));
    }
    
    TrackEventWrapper& add_annotation(std::string_view key, double value) {
        auto* annotation = event_->add_debug_annotations();
        annotation->set_name(std::string(key));
        annotation->set_double_value(value);
        return *this;
    }
    
    TrackEventWrapper& add_annotation(std::string_view key, bool value) {
        auto* annotation = event_->add_debug_annotations();
        annotation->set_name(std::string(key));
        annotation->set_bool_value(value);
        return *this;
    }
    
    TrackEventWrapper& add_annotation(std::string_view key, std::string_view value) {
        auto* annotation = event_->add_debug_annotations();
        annotation->set_name(std::string(key));
        annotation->set_string_value(std::string(value));
        return *this;
    }
    
    TrackEventWrapper& add_annotation(std::string_view key, const char* value) {
        return add_annotation(key, std::string_view(value));
    }
    
    // Pointer annotation with automatic formatting
    TrackEventWrapper& add_pointer(std::string_view key, uint64_t address) {
        auto* annotation = event_->add_debug_annotations();
        annotation->set_name(std::string(key));
        annotation->set_pointer_value(address);
        return *this;
    }
    
    // RAII annotation context
    [[nodiscard]] AnnotationBuilder annotation(std::string_view name);
    
    // Variadic template for multiple annotations
    template<typename... Args>
    TrackEventWrapper& add_annotations(Args&&... args) {
        static_assert(sizeof...(args) % 2 == 0, "Annotations must be key-value pairs");
        add_annotations_impl(std::forward<Args>(args)...);
        return *this;
    }
    
private:
    // Base case for recursion
    void add_annotations_impl() {}
    
    // Recursive case
    template<typename Key, typename Value, typename... Rest>
    void add_annotations_impl(Key&& key, Value&& value, Rest&&... rest) {
        add_annotation(std::forward<Key>(key), std::forward<Value>(value));
        add_annotations_impl(std::forward<Rest>(rest)...);
    }
};

// Builder for nested annotations
class AnnotationBuilder {
private:
    perfetto::protos::DebugAnnotation* annotation_;
    perfetto::protos::DebugAnnotation::NestedValue* nested_;
    
public:
    explicit AnnotationBuilder(perfetto::protos::DebugAnnotation* annotation) 
        : annotation_(annotation) {
        nested_ = annotation_->mutable_nested_value();
        nested_->set_nested_type(perfetto::protos::DebugAnnotation::NestedValue::DICT);
    }
    
    // Typed annotation methods
    AnnotationBuilder& integer(std::string_view key, int64_t value) {
        nested_->add_dict_keys(std::string(key));
        auto* nested_val = nested_->add_dict_values();
        nested_val->set_int_value(value);
        return *this;
    }
    
    AnnotationBuilder& floating(std::string_view key, double value) {
        nested_->add_dict_keys(std::string(key));
        auto* nested_val = nested_->add_dict_values();
        nested_val->set_double_value(value);
        return *this;
    }
    
    AnnotationBuilder& boolean(std::string_view key, bool value) {
        nested_->add_dict_keys(std::string(key));
        auto* nested_val = nested_->add_dict_values();
        nested_val->set_bool_value(value);
        return *this;
    }
    
    AnnotationBuilder& string(std::string_view key, std::string_view value) {
        nested_->add_dict_keys(std::string(key));
        auto* nested_val = nested_->add_dict_values();
        nested_val->set_string_value(std::string(value));
        return *this;
    }
    
    AnnotationBuilder& pointer(std::string_view key, uint64_t address) {
        // Store pointers as formatted hex strings in nested values
        std::ostringstream oss;
        oss << "0x" << std::hex << address;
        return string(key, oss.str());
    }
    
    // Nested annotations - creates another level
    [[nodiscard]] AnnotationBuilder nested(std::string_view key) {
        nested_->add_dict_keys(std::string(key));
        auto* nested_val = nested_->add_dict_values();
        nested_val->set_nested_type(perfetto::protos::DebugAnnotation::NestedValue::DICT);
        
        // For simplicity, we'll return a builder for the same annotation
        // In a real implementation, we'd need to create a proper nested structure
        return AnnotationBuilder(annotation_);
    }
};

// Implementation of deferred methods
inline TrackEventWrapper PerfettoTraceBuilder::begin_slice(uint64_t track_uuid, std::string_view name, uint64_t timestamp_ns) {
    auto* packet = create_packet(timestamp_ns);
    
    auto* event = packet->mutable_track_event();
    event->set_type(perfetto::protos::TrackEvent::TYPE_SLICE_BEGIN);
    event->set_track_uuid(track_uuid);
    event->set_name(std::string(name));
    
    return TrackEventWrapper(event);
}

inline TrackEventWrapper PerfettoTraceBuilder::add_instant_event(uint64_t track_uuid, std::string_view name, uint64_t timestamp_ns) {
    auto* packet = create_packet(timestamp_ns);
    
    auto* event = packet->mutable_track_event();
    event->set_type(perfetto::protos::TrackEvent::TYPE_INSTANT);
    event->set_track_uuid(track_uuid);
    event->set_name(std::string(name));
    
    return TrackEventWrapper(event);
}

inline TrackEventWrapper PerfettoTraceBuilder::add_flow(uint64_t track_uuid, std::string_view name, uint64_t timestamp_ns,
                                                         uint64_t flow_id, bool terminating) {
    auto* packet = create_packet(timestamp_ns);
    
    auto* event = packet->mutable_track_event();
    event->set_type(perfetto::protos::TrackEvent::TYPE_INSTANT);
    event->set_track_uuid(track_uuid);
    event->set_name(std::string(name));
    
    if (terminating) {
        event->add_terminating_flow_ids(flow_id);
    } else {
        event->add_flow_ids(flow_id);
    }
    
    return TrackEventWrapper(event);
}

inline AnnotationBuilder TrackEventWrapper::annotation(std::string_view name) {
    auto* annotation = event_->add_debug_annotations();
    annotation->set_name(std::string(name));
    return AnnotationBuilder(annotation);
}

} // namespace retrobus
