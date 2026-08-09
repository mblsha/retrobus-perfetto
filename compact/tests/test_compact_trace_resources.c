#include "retrobus/compact_trace.h"
#include "test_codec_profile.h"

#include <stdint.h>

#define CHECK(expression) \
  do {                    \
    if (!(expression)) {  \
      return __LINE__;    \
    }                     \
  } while (0)

#define STATIC_ASSERT(name, expression) \
  typedef char static_assert_##name[(expression) ? 1 : -1]

#if UINTPTR_MAX > UINT32_MAX
#define RBCT_WRITER_SIZE_BUDGET 144u
#else
#define RBCT_WRITER_SIZE_BUDGET 120u
#endif

STATIC_ASSERT(writer_size_budget,
              sizeof(rbct_writer_t) <= RBCT_WRITER_SIZE_BUDGET);
STATIC_ASSERT(scope_size_budget, sizeof(rbct_scope_t) <= 88u);
STATIC_ASSERT(commit_cursor_has_no_per_record_bytes,
              RBCT_RECORD_COMMIT_BYTES == 0u);
STATIC_ASSERT(maximum_committed_record, RBCT_MAX_RECORD_BYTES == 70u);

static uint16_t get_u16(const uint8_t* data, size_t offset) {
  return (uint16_t)((uint16_t)data[offset] |
                    ((uint16_t)data[offset + 1u] << 8u));
}

static uint64_t get_u64(const uint8_t* data, size_t offset) {
  uint64_t value = 0u;
  size_t index;
  for (index = 0u; index < 8u; ++index) {
    value |= (uint64_t)data[offset + index] << (index * 8u);
  }
  return value;
}

int main(void) {
  union {
    uint32_t alignment;
    uint8_t bytes[RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES];
  } storage;
  union {
    uint32_t alignment;
    uint8_t bytes[RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES + 4u];
  } unaligned_storage;
  uint8_t* buffer = storage.bytes;
  rbct_scope_t scope;
  rbct_writer_t writer;
  rbct_config_t config = {0};
  rbct_argument_t maximum_arguments[RBCT_MAX_ARGUMENTS];
  const uint8_t* chunk;
  unsigned index;

  test_codec_profiles_initialize();

  config.clock_rate_numerator = 1u;
  config.clock_rate_denominator = 1u;
  config.clock_width_bits = 64u;
  CHECK(rbct_writer_init(&writer, unaligned_storage.bytes + 1u,
                         sizeof(storage.bytes), &scope, 1u, &config) ==
        RBCT_INVALID_ARGUMENT);
  config.codec_profile = &test_codec_profile;
  CHECK(rbct_writer_init(&writer, buffer, sizeof(storage.bytes), &scope, 1u,
                         &config) == RBCT_OK);

  for (index = 0u; index < 32383u; ++index) {
    CHECK(rbct_writer_begin(&writer, index, 0u, 0u, NULL, 0u) == RBCT_OK);
    CHECK(rbct_writer_end(&writer, index + 1u) == RBCT_OK);
  }
  chunk = buffer + RBCT_FILE_HEADER_BYTES;
  CHECK(get_u16(chunk, 28u) == 32384u);
  CHECK(get_u16(chunk, 30u) == 32383u);
  CHECK(chunk[RBCT_CHUNK_HEADER_BYTES] == 1u);

  CHECK(rbct_writer_begin(&writer, 32383u, 0u, 0u, NULL, 0u) == RBCT_OK);
  CHECK(rbct_writer_end(&writer, 32384u) == RBCT_OK);
  CHECK(get_u64(chunk, 4u) == 1u);
  CHECK(get_u16(chunk, 28u) == 2u);
  CHECK(get_u16(chunk, 30u) == 1u);
  CHECK(writer.overwritten_records == 32383u);

  config.codec_profile = &test_large_codec_profile;
  CHECK(rbct_writer_init(&writer, buffer, sizeof(storage.bytes), &scope, 1u,
                         &config) == RBCT_OK);
  CHECK(rbct_writer_begin(&writer, 0u, 0u, 0u, NULL, 0u) == RBCT_OK);
  CHECK(rbct_writer_end(&writer, 1u) == RBCT_OK);
  chunk = buffer + RBCT_FILE_HEADER_BYTES;
  CHECK(get_u16(chunk, 28u) == 1u);
  CHECK(get_u16(chunk, 30u) == 1u);

  config.codec_profile = NULL;
  CHECK(rbct_writer_init(&writer, buffer, sizeof(storage.bytes), &scope, 1u,
                         &config) == RBCT_OK);
  for (index = 0u; index < 100u; ++index) {
    CHECK(rbct_writer_begin_opcode(&writer, 2u * index + 1u, 0u, 0u, 1u,
                                   NULL, 0u) == RBCT_OK);
    CHECK(rbct_writer_end(&writer, 2u * index + 2u) == RBCT_OK);
  }
  chunk = buffer + RBCT_FILE_HEADER_BYTES;
  CHECK(get_u16(chunk, 28u) == 100u * 27u);
  CHECK(get_u16(chunk, 30u) == 100u);
  CHECK(rbct_writer_begin_opcode(&writer, 201u, 0u, 0u, 1u, NULL, 0u) ==
        RBCT_OK);
  CHECK(rbct_writer_end(&writer, 202u) == RBCT_OK);
  CHECK(get_u64(chunk, 4u) == 0u);
  CHECK(get_u16(chunk, 30u) == 101u);

  for (index = 0u; index < RBCT_MAX_ARGUMENTS; ++index) {
    maximum_arguments[index] = rbct_argument_u64(UINT64_MAX);
  }
  CHECK(rbct_writer_init(&writer, buffer, sizeof(storage.bytes), &scope, 1u,
                         &config) == RBCT_OK);
  CHECK(rbct_writer_emit_opcode(&writer, 0u, 0u, 229u, 1u, 2u, 3u, NULL, 0u) ==
        RBCT_OK);
  CHECK(rbct_writer_begin(&writer, 0u, UINT32_MAX, UINT32_MAX,
                          maximum_arguments, RBCT_MAX_ARGUMENTS) == RBCT_OK);
  CHECK(rbct_writer_end(&writer, (UINT64_C(1) << 63u) - 1u) == RBCT_OK);
  chunk = buffer + RBCT_FILE_HEADER_BYTES;
  CHECK((get_u16(chunk, 28u) + 7u) / 8u <= RBCT_MAX_RECORD_BYTES + 4u);
  return 0;
}
