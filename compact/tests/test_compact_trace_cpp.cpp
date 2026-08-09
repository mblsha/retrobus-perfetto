#include "retrobus/compact_trace.hpp"

#include <array>
#include <cstdint>

#define CHECK(expression) \
  do {                    \
    if (!(expression)) {  \
      return __LINE__;    \
    }                     \
  } while (false)

namespace {

constexpr auto kUnsigned = retrobus::compact::unsigned_argument(7);
constexpr auto kSigned = retrobus::compact::signed_argument(-7);
constexpr auto kFixed = retrobus::compact::fixed64_argument(9);
static_assert(kUnsigned.bits == 7);
static_assert(kSigned.bits == 13);
static_assert(kFixed.bits == 9);

std::uint64_t read_clock(void* context) {
  auto* value = static_cast<std::uint64_t*>(context);
  *value += 10;
  return *value;
}

}  // namespace

int main() {
  std::array<std::uint8_t, RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES> buffer{};
  retrobus::compact::Config config{};
  config.clock_rate_numerator = 1'000'000;
  config.clock_rate_denominator = 1;
  config.clock_width_bits = 64;
  config.producer_id = 9;
  config.schema_version = 1;

  retrobus::compact::Writer writer{buffer.data(), buffer.size(), config};
  CHECK(writer.enabled());
  std::uint64_t clock_value = 100;
  retrobus::compact::Clock clock{read_clock, &clock_value};
  {
    retrobus::compact::TraceScope scope{
        &writer, clock, 0, 1, {retrobus::compact::unsigned_argument(8)}};
    CHECK(scope.active());
    CHECK(writer.emit(clock.now(), 0, 2) == RBCT_OK);
  }
  const auto after_enabled = clock_value;
  {
    retrobus::compact::TraceScope<16> disabled{nullptr, clock, 0, 1};
    CHECK(!disabled.active());
  }
  CHECK(clock_value == after_enabled);
  CHECK(writer.emit(clock.now(), 0, 2,
                    {retrobus::compact::unsigned_argument(1),
                     retrobus::compact::unsigned_argument(2),
                     retrobus::compact::unsigned_argument(3),
                     retrobus::compact::unsigned_argument(4),
                     retrobus::compact::unsigned_argument(5)}) ==
        RBCT_INVALID_ARGUMENT);
  CHECK(writer.enabled());
  {
    retrobus::compact::TraceScope scope{&writer, clock, 0, 1};
    CHECK(scope.active());
    CHECK(scope.cancel() == RBCT_OK);
    CHECK(!scope.active());
  }
  {
    retrobus::compact::TraceScope scope{&writer, clock, 0, 1};
    CHECK(scope.active());
    clock_value = 0;
  }
  CHECK(writer.status() == RBCT_INVALID_ARGUMENT);
  CHECK(writer.native_handle()->scope_depth == 0);
  CHECK(writer.native_handle()->dropped_records == 3);
  CHECK(writer.finalize() == RBCT_OK);
  CHECK(writer.size() == buffer.size());
  return 0;
}
