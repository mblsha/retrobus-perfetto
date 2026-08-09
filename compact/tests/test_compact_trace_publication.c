static void test_publish_barrier(void);

#define RBCT_PLATFORM_PUBLISH_BARRIER() test_publish_barrier()
#include "../src/compact_trace.c"

static uint8_t* watched_buffer;
static rbct_writer_t* watched_writer;
static int saw_invalidated_reused_chunk;
static int saw_prepared_unpublished_chunk;
static int saw_finalized_without_crc;
static int saw_chunk_crc_flag_before_chunk_crc;

static void test_publish_barrier(void) {
  const uint8_t* chunk;
  if (watched_buffer == NULL) {
    return;
  }
  chunk = watched_buffer + RBCT_FILE_HEADER_BYTES;
  if ((rbct_get_u16(watched_buffer, 38u) & RBCT_FLAG_FINALIZED) != 0u &&
      rbct_get_u32(watched_buffer, 152u) == 0u) {
    saw_finalized_without_crc = 1;
  }
  if ((rbct_get_u16(watched_buffer, 38u) & RBCT_FLAG_CHUNK_HEADER_CRC) != 0u &&
      chunk[0] == RBCT_CHUNK_MAGIC_0 && rbct_get_u32(chunk, 44u) == 0u) {
    saw_chunk_crc_flag_before_chunk_crc = 1;
  }
  if (chunk[0] == 0u && chunk[1] == RBCT_CHUNK_MAGIC_1 &&
      chunk[2] == RBCT_CHUNK_MAGIC_2 && chunk[3] == RBCT_CHUNK_MAGIC_3) {
    if (watched_writer != NULL &&
        watched_writer->current_chunk != RBCT_NO_CHUNK &&
        chunk[4] == 0u) {
      saw_invalidated_reused_chunk = 1;
    } else if (chunk[4] != 0u) {
      saw_prepared_unpublished_chunk = 1;
    }
  }
}

int main(void) {
  uint8_t buffer[RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES];
  rbct_writer_t writer;
  rbct_config_t config = {0};
  unsigned index;

  config.clock_rate_numerator = UINT64_C(1000000000);
  config.clock_rate_denominator = 1u;
  config.clock_width_bits = 32u;
  watched_buffer = buffer;
  watched_writer = &writer;
  if (rbct_writer_init(&writer, buffer, sizeof(buffer), NULL, 0u, &config) !=
      RBCT_OK) {
    return 1;
  }
  for (index = 0u; index < 2000u && !saw_invalidated_reused_chunk; ++index) {
    if (rbct_writer_emit(&writer, index, 0u, 1u, NULL, 0u) != RBCT_OK) {
      return 2;
    }
  }
  if (!saw_invalidated_reused_chunk) {
    return 3;
  }
  if (!saw_prepared_unpublished_chunk) {
    return 4;
  }
  if ((rbct_get_u16(buffer, 38u) & RBCT_FLAG_RING_WRAPPED) == 0u) {
    return 5;
  }
  if (rbct_writer_finalize(&writer) != RBCT_OK) {
    return 6;
  }
  if (saw_finalized_without_crc) {
    return 7;
  }
  if (saw_chunk_crc_flag_before_chunk_crc) {
    return 8;
  }
  return 0;
}
