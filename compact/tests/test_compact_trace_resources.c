#include "retrobus/compact_trace.h"

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
#define RBCT_WRITER_SIZE_BUDGET 136u
#else
#define RBCT_WRITER_SIZE_BUDGET 112u
#endif

STATIC_ASSERT(writer_size_budget,
              sizeof(rbct_writer_t) <= RBCT_WRITER_SIZE_BUDGET);
STATIC_ASSERT(scope_size_budget, sizeof(rbct_scope_t) <= 88u);
STATIC_ASSERT(single_byte_commit_opcodes, RBCT_RECORD_COMMIT_BYTES == 1u);
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
  uint8_t buffer[RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES];
  rbct_scope_t scope;
  rbct_writer_t writer;
  rbct_config_t config = {0};
  rbct_argument_t maximum_arguments[RBCT_MAX_ARGUMENTS];
  const uint8_t* chunk;
  unsigned index;

  config.clock_rate_numerator = 1u;
  config.clock_rate_denominator = 1u;
  config.clock_width_bits = 64u;
  CHECK(rbct_writer_init(&writer, buffer, sizeof(buffer), NULL, 0u, &config) ==
        RBCT_OK);

  for (index = 0u; index < 4048u; ++index) {
    CHECK(rbct_writer_emit_opcode(&writer, index, 0u, 229u, 1u, 2u, 3u, NULL,
                                  0u) == RBCT_OK);
  }
  chunk = buffer + RBCT_FILE_HEADER_BYTES;
  CHECK(get_u16(chunk, 28u) == RBCT_CHUNK_BYTES - RBCT_CHUNK_HEADER_BYTES);
  CHECK(get_u16(chunk, 30u) == 4048u);
  CHECK(chunk[RBCT_CHUNK_HEADER_BYTES] == 2u);
  CHECK(chunk[RBCT_CHUNK_HEADER_BYTES + 1u] == 3u);

  CHECK(rbct_writer_emit_opcode(&writer, 4048u, 0u, 229u, 1u, 2u, 3u, NULL,
                                0u) == RBCT_OK);
  CHECK(get_u64(chunk, 4u) == 1u);
  CHECK(get_u16(chunk, 28u) == 1u);
  CHECK(get_u16(chunk, 30u) == 1u);
  CHECK(writer.overwritten_records == 4048u);

  CHECK(rbct_writer_init(&writer, buffer, sizeof(buffer), &scope, 1u,
                         &config) == RBCT_OK);
  for (index = 0u; index < 1349u; ++index) {
    CHECK(rbct_writer_begin_opcode(&writer, 2u * index + 1u, 0u, 0u, 1u,
                                   NULL, 0u) == RBCT_OK);
    CHECK(rbct_writer_end(&writer, 2u * index + 2u) == RBCT_OK);
  }
  chunk = buffer + RBCT_FILE_HEADER_BYTES;
  CHECK(get_u16(chunk, 28u) == 4047u);
  CHECK(get_u16(chunk, 30u) == 1349u);
  CHECK(chunk[RBCT_CHUNK_HEADER_BYTES] == 1u);
  CHECK(chunk[RBCT_CHUNK_HEADER_BYTES + 1u] == 0u);
  CHECK(chunk[RBCT_CHUNK_HEADER_BYTES + 2u] == 1u);
  CHECK(rbct_writer_begin_opcode(&writer, 2699u, 0u, 0u, 1u, NULL, 0u) ==
        RBCT_OK);
  CHECK(rbct_writer_end(&writer, 2700u) == RBCT_OK);
  CHECK(get_u64(chunk, 4u) == 1u);
  CHECK(get_u16(chunk, 28u) == 3u);
  CHECK(get_u16(chunk, 30u) == 1u);
  CHECK(writer.overwritten_records == 1349u);

  for (index = 0u; index < RBCT_MAX_ARGUMENTS; ++index) {
    maximum_arguments[index] = rbct_argument_u64(UINT64_MAX);
  }
  CHECK(rbct_writer_init(&writer, buffer, sizeof(buffer), &scope, 1u,
                         &config) == RBCT_OK);
  CHECK(rbct_writer_emit_opcode(&writer, 0u, 0u, 229u, 1u, 2u, 3u, NULL, 0u) ==
        RBCT_OK);
  CHECK(rbct_writer_begin(&writer, 0u, UINT32_MAX, UINT32_MAX,
                          maximum_arguments, RBCT_MAX_ARGUMENTS) == RBCT_OK);
  CHECK(rbct_writer_end(&writer, (UINT64_C(1) << 63u) - 1u) == RBCT_OK);
  chunk = buffer + RBCT_FILE_HEADER_BYTES;
  CHECK(get_u16(chunk, 28u) == 71u);
  CHECK(chunk[RBCT_CHUNK_HEADER_BYTES + 1u] == 0xfeu);
  return 0;
}
