#include "retrobus/compact_trace.h"

#include <stdint.h>

#define CHECK(expression) \
  do {                    \
    if (!(expression)) {  \
      return __LINE__;    \
    }                     \
  } while (0)

static uint16_t get_u16(const uint8_t* data, size_t offset) {
  return (uint16_t)((uint16_t)data[offset] |
                    ((uint16_t)data[offset + 1u] << 8u));
}

static uint64_t get_u64(const uint8_t* data, size_t offset) {
  uint64_t value = 0;
  size_t index;
  for (index = 0; index < 8u; ++index) {
    value |= (uint64_t)data[offset + index] << (index * 8u);
  }
  return value;
}

int main(void) {
  uint8_t buffer[RBCT_FILE_HEADER_BYTES + 2u * RBCT_CHUNK_BYTES];
  rbct_scope_t scopes[4];
  rbct_writer_t writer;
  rbct_config_t config = {0};
  const rbct_argument_t amount = rbct_argument_u64(42u);
  const rbct_argument_t negative = rbct_argument_i64(-7);
  const uint8_t* data;

  config.clock_rate_numerator = 3686400u;
  config.clock_rate_denominator = 1u;
  config.clock_width_bits = 32u;
  config.producer_id = 42u;
  config.schema_version = 3u;
  config.initial_clock_generation = 7u;

  CHECK(rbct_required_buffer_bytes(2u) == sizeof(buffer));
  CHECK(rbct_writer_init(&writer, &writer,
                         RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES, scopes, 4u,
                         &config) == RBCT_INVALID_ARGUMENT);
  CHECK(rbct_writer_init(&writer, buffer, sizeof(buffer), (rbct_scope_t*)buffer,
                         1u, &config) == RBCT_INVALID_ARGUMENT);
  CHECK(rbct_writer_init(&writer, buffer, sizeof(buffer) - 1u, scopes, 4u,
                         &config) == RBCT_INVALID_ARGUMENT);
  CHECK(rbct_writer_init(&writer, buffer, sizeof(buffer), scopes, 4u,
                         &config) == RBCT_OK);
  CHECK(rbct_writer_enabled(&writer));
  CHECK(rbct_writer_clock_sync(&writer, 7u, 100u, 102u, 1000000u, 300u) ==
        RBCT_OK);
  CHECK(rbct_writer_clock_sync(&writer, 7u, 100u, 102u, 1000001u, 300u) ==
        RBCT_INVALID_ARGUMENT);
  CHECK(rbct_writer_begin(&writer, 110u, 0u, 1u, &amount, 1u) == RBCT_OK);
  CHECK(rbct_writer_emit(&writer, 120u, 0u, 2u, &negative, 1u) == RBCT_OK);
  CHECK(rbct_writer_end(&writer, 150u) == RBCT_OK);
  CHECK(rbct_writer_emit(&writer, 160u, 1u, 300u, &amount, 1u) == RBCT_OK);
  CHECK(rbct_writer_finalize(&writer) == RBCT_OK);
  CHECK(!rbct_writer_enabled(&writer));

  data = (const uint8_t*)rbct_writer_data(&writer);
  CHECK(data != 0);
  CHECK(data[0] == 'R' && data[1] == 'B' && data[6] == '2');
  CHECK((get_u16(data, 38u) & 1u) != 0u);
  CHECK((get_u16(data, 38u) & 4u) != 0u);
  CHECK(get_u64(data, 96u) == 3u);
  CHECK(get_u64(data, 120u) == 4u);
  CHECK(get_u16(data + RBCT_FILE_HEADER_BYTES, 30u) == 3u);
  CHECK(get_u16(data + RBCT_FILE_HEADER_BYTES, 36u) == 1u);
  CHECK(data[RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_HEADER_BYTES] != 0u);
  CHECK(rbct_writer_size(&writer) == sizeof(buffer));

  CHECK(rbct_writer_init(&writer, buffer,
                         RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES, scopes, 4u,
                         &config) == RBCT_OK);
  CHECK(rbct_writer_clock_sync(&writer, 9u, 10u, 12u, 1000000u, 0u) ==
        RBCT_INVALID_ARGUMENT);
  CHECK(rbct_writer_begin(&writer, 10u, 0u, 1u, 0, 0) == RBCT_OK);
  CHECK(rbct_writer_clock_sync(&writer, 8u, 20u, 22u, 2000000u, 0u) ==
        RBCT_INVALID_STATE);
  CHECK(rbct_writer_end(&writer, 30u) == RBCT_OK);
  CHECK(rbct_writer_clock_sync(&writer, 8u, 40u, 42u, 2000000u, 0u) ==
        RBCT_INVALID_ARGUMENT);
  CHECK(rbct_writer_clock_sync(&writer, 9u, 1u, 3u, 1999999u, 0u) ==
        RBCT_INVALID_ARGUMENT);
  CHECK(rbct_writer_emit(&writer, UINT64_C(1) << 32u, 0u, 2u, 0, 0) ==
        RBCT_INVALID_ARGUMENT);
  CHECK(rbct_writer_emit(&writer, 20u, 0u, 2u, 0, 0) == RBCT_INVALID_ARGUMENT);

  CHECK(rbct_writer_init(&writer, buffer,
                         RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES, scopes, 4u,
                         &config) == RBCT_OK);
  CHECK(rbct_writer_begin(&writer, 100u, 0u, 1u, 0, 0) == RBCT_OK);
  CHECK(rbct_writer_emit(&writer, 99u, 0u, 2u, 0, 0) == RBCT_OK);
  CHECK(rbct_writer_cancel(&writer) == RBCT_OK);

  CHECK(rbct_writer_init(&writer, buffer,
                         RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES, scopes, 4u,
                         &config) == RBCT_OK);
  CHECK(rbct_writer_begin(&writer, 0u, 0u, 1u, 0, 0) == RBCT_OK);
  CHECK(rbct_writer_end(&writer, UINT64_C(1) << 31u) == RBCT_INVALID_ARGUMENT);
  CHECK(writer.scope_depth == 1u);
  CHECK(rbct_writer_cancel(&writer) == RBCT_OK);
  CHECK(writer.dropped_records == 1u);
  CHECK(rbct_writer_finalize(&writer) == RBCT_OK);

  config.clock_rate_numerator = UINT64_C(1000000000);
  config.clock_width_bits = 8u;
  CHECK(rbct_writer_init(&writer, buffer,
                         RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES, scopes, 4u,
                         &config) == RBCT_OK);
  CHECK(rbct_writer_emit(&writer, 0u, 0u, 2u, 0, 0) == RBCT_OK);
  CHECK(rbct_writer_begin(&writer, 100u, 0u, 1u, 0, 0) == RBCT_OK);
  CHECK(rbct_writer_end(&writer, 200u) == RBCT_INVALID_ARGUMENT);
  CHECK(rbct_writer_cancel(&writer) == RBCT_OK);

  config.clock_width_bits = 32u;
  CHECK(rbct_writer_init(&writer, buffer,
                         RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES, 0, 0,
                         &config) == RBCT_OK);
  CHECK(rbct_writer_emit(&writer, 100u, 0u, 2u, 0, 0) == RBCT_OK);
  CHECK(rbct_writer_clock_sync(&writer, 7u, 200u, 200u, 1000u, 0u) ==
        RBCT_INVALID_ARGUMENT);
  CHECK(rbct_writer_clock_sync(&writer, 8u, 0u, 0u, 1000u, 0u) ==
        RBCT_INVALID_ARGUMENT);

  CHECK(rbct_writer_init(&writer, buffer,
                         RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES, 0, 0,
                         &config) == RBCT_OK);
  CHECK(rbct_writer_clock_sync(&writer, 7u, 0u, 0u, 1000u, 0u) == RBCT_OK);
  CHECK(rbct_writer_emit(&writer, 1000u, 0u, 2u, 0, 0) == RBCT_OK);
  /* Cross-generation rational clock validation is performed by the host. */
  CHECK(rbct_writer_clock_sync(&writer, 8u, 0u, 0u, 1500u, 0u) == RBCT_OK);
  CHECK(rbct_writer_finalize(&writer) == RBCT_OK);

  config.clock_rate_numerator = UINT64_MAX;
  config.clock_rate_denominator = UINT64_MAX;
  config.clock_width_bits = 64u;
  CHECK(rbct_writer_init(&writer, buffer,
                         RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES, 0, 0,
                         &config) == RBCT_OK);
  CHECK(rbct_writer_clock_sync(&writer, 7u, 0u, 0u, 0u, 0u) == RBCT_OK);
  CHECK(rbct_writer_emit(&writer, 1u, 0u, 2u, 0, 0) == RBCT_OK);
  CHECK(rbct_writer_clock_sync(&writer, 8u, 0u, 0u, 999999999u, 0u) == RBCT_OK);

  config.clock_rate_numerator = UINT64_C(1000000000);
  config.clock_rate_denominator = 1u;
  config.clock_width_bits = 32u;

  CHECK(rbct_writer_init(&writer, buffer,
                         RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES, 0, 0,
                         &config) == RBCT_OK);
  {
    unsigned index;
    for (index = 0; index < 5000u; ++index) {
      CHECK(rbct_writer_emit(&writer, index, 0u, 2u, 0, 0) == RBCT_OK);
    }
  }
  CHECK(rbct_writer_finalize(&writer) == RBCT_OK);
  data = (const uint8_t*)rbct_writer_data(&writer);
  CHECK((get_u16(data, 38u) & 2u) != 0u);
  CHECK(get_u64(data, 96u) == 5000u);
  CHECK(get_u64(data, 104u) > 0u);
  CHECK(get_u64(data, 104u) < get_u64(data, 96u));
  return 0;
}
