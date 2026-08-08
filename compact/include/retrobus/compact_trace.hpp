#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <initializer_list>

#include "retrobus/compact_trace.h"

namespace retrobus::compact {

using Argument = rbct_argument_t;
using Config = rbct_config_t;
using Status = rbct_status_t;

[[nodiscard]] constexpr Argument unsigned_argument(std::uint64_t value) noexcept {
    return rbct_argument_u64(value);
}

[[nodiscard]] constexpr Argument signed_argument(std::int64_t value) noexcept {
    return rbct_argument_i64(value);
}

[[nodiscard]] constexpr Argument fixed64_argument(std::uint64_t bits) noexcept {
    return rbct_argument_fixed64(bits);
}

struct Clock {
    using Read = std::uint64_t (*)(void* context);

    Read read{};
    void* context{};

    [[nodiscard]] constexpr explicit operator bool() const noexcept { return read != nullptr; }
    [[nodiscard]] std::uint64_t now() const noexcept { return read(context); }
};

template <std::size_t ScopeDepth = 16>
class Writer {
 public:
    Writer(void* buffer, std::size_t buffer_bytes, const Config& config) noexcept
        : status_(rbct_writer_init(&writer_, buffer, buffer_bytes, scopes_.data(),
                                   scopes_.size(), &config)) {}

    Writer(const Writer&) = delete;
    Writer& operator=(const Writer&) = delete;

    [[nodiscard]] bool enabled() const noexcept {
        return status_ == RBCT_OK && rbct_writer_enabled(&writer_) != 0;
    }
    [[nodiscard]] Status status() const noexcept { return status_; }

    Status begin(std::uint64_t timestamp, std::uint32_t track, std::uint32_t event,
                 std::initializer_list<Argument> arguments = {}) noexcept {
        status_ = rbct_writer_begin(&writer_, timestamp, track, event,
                                    arguments.begin(), arguments.size());
        return status_;
    }

    Status end(std::uint64_t timestamp) noexcept {
        status_ = rbct_writer_end(&writer_, timestamp);
        return status_;
    }

    Status emit(std::uint64_t timestamp, std::uint32_t track, std::uint32_t event,
                std::initializer_list<Argument> arguments = {}) noexcept {
        status_ = rbct_writer_emit(&writer_, timestamp, track, event,
                                   arguments.begin(), arguments.size());
        return status_;
    }

    Status clock_sync(std::uint32_t generation, std::uint64_t before,
                      std::uint64_t after, std::uint64_t reference_ns,
                      std::uint64_t uncertainty_ns = 0) noexcept {
        status_ = rbct_writer_clock_sync(&writer_, generation, before, after,
                                         reference_ns, uncertainty_ns);
        return status_;
    }

    Status finalize() noexcept {
        status_ = rbct_writer_finalize(&writer_);
        return status_;
    }

    [[nodiscard]] const void* data() const noexcept { return rbct_writer_data(&writer_); }
    [[nodiscard]] std::size_t size() const noexcept { return rbct_writer_size(&writer_); }
    [[nodiscard]] rbct_writer_t* native_handle() noexcept { return &writer_; }

 private:
    rbct_writer_t writer_{};
    std::array<rbct_scope_t, ScopeDepth> scopes_{};
    Status status_{RBCT_INVALID_STATE};
};

template <std::size_t ScopeDepth = 16>
class TraceScope {
 public:
    TraceScope(Writer<ScopeDepth>* writer, Clock clock, std::uint32_t track,
               std::uint32_t event,
               std::initializer_list<Argument> arguments = {}) noexcept
        : writer_(writer), clock_(clock) {
        if (writer_ == nullptr || !writer_->enabled() || !clock_) {
            return;
        }
        active_ = writer_->begin(clock_.now(), track, event, arguments) == RBCT_OK;
    }

    ~TraceScope() {
        if (active_) {
            static_cast<void>(writer_->end(clock_.now()));
        }
    }

    TraceScope(const TraceScope&) = delete;
    TraceScope& operator=(const TraceScope&) = delete;
    TraceScope(TraceScope&&) = delete;
    TraceScope& operator=(TraceScope&&) = delete;

    [[nodiscard]] bool active() const noexcept { return active_; }

 private:
    Writer<ScopeDepth>* writer_{};
    Clock clock_{};
    bool active_{};
};

}  // namespace retrobus::compact
