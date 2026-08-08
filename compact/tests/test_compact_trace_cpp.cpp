#include "retrobus/compact_trace.hpp"

#include <array>
#include <cassert>
#include <cstdint>

namespace {

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
  assert(writer.enabled());
  std::uint64_t clock_value = 100;
  retrobus::compact::Clock clock{read_clock, &clock_value};
  {
    retrobus::compact::TraceScope scope{
        &writer, clock, 0, 1, {retrobus::compact::unsigned_argument(8)}};
    assert(scope.active());
    assert(writer.emit(clock.now(), 0, 2) == RBCT_OK);
  }
  const auto after_enabled = clock_value;
  {
    retrobus::compact::TraceScope<16> disabled{nullptr, clock, 0, 1};
    assert(!disabled.active());
  }
  assert(clock_value == after_enabled);
  assert(writer.emit(clock.now(), 0, 2,
                     {retrobus::compact::unsigned_argument(1),
                      retrobus::compact::unsigned_argument(2),
                      retrobus::compact::unsigned_argument(3),
                      retrobus::compact::unsigned_argument(4),
                      retrobus::compact::unsigned_argument(5)}) ==
         RBCT_INVALID_ARGUMENT);
  assert(writer.enabled());
  {
    retrobus::compact::TraceScope scope{&writer, clock, 0, 1};
    assert(scope.active());
  }
  assert(writer.finalize() == RBCT_OK);
  assert(writer.size() == buffer.size());
  return 0;
}
