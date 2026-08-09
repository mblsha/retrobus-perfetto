#include "interop_schema.h"
#include "retrobus/compact_trace.h"

#include <stdio.h>

int main(int argc, char** argv) {
  unsigned char buffer[RBCT_FILE_HEADER_BYTES + 2u * RBCT_CHUNK_BYTES];
  rbct_writer_t writer;
  rbct_config_t config = {0};
  FILE* output;
  unsigned generation;
  unsigned index;

  if (argc != 2) {
    return 2;
  }
  config.clock_rate_numerator = 1000000000u;
  config.clock_rate_denominator = 1u;
  config.clock_width_bits = 32u;
  config.producer_id = INTEROP_TRACE_PRODUCER_ID;
  config.schema_version = INTEROP_TRACE_SCHEMA_VERSION;
  config.initial_clock_generation = 7u;
  for (index = 0; index < 32u; ++index) {
    config.schema_sha256[index] = INTEROP_TRACE_SCHEMA_SHA256[index];
  }
  if (rbct_writer_init(&writer, buffer, sizeof(buffer), NULL, 0u, &config) !=
      RBCT_OK) {
    return 3;
  }
  for (generation = 7u; generation <= 10u; ++generation) {
    if (rbct_writer_clock_sync(&writer, generation, 0u, 2u,
                               1000u + (uint64_t)(generation - 7u) * 1000u,
                               0u) != RBCT_OK) {
      return 4;
    }
  }
  if (rbct_writer_finalize(&writer) != RBCT_OK) {
    return 5;
  }
  output = fopen(argv[1], "wb");
  if (output == NULL) {
    return 6;
  }
  if (fwrite(rbct_writer_data(&writer), 1, rbct_writer_size(&writer), output) !=
      rbct_writer_size(&writer)) {
    fclose(output);
    return 7;
  }
  if (fclose(output) != 0) {
    return 8;
  }
  return 0;
}
