#include "interop_schema.h"
#include "retrobus/compact_trace.h"

#include <stdio.h>

int main(int argc, char** argv) {
  unsigned char buffer[RBCT_FILE_HEADER_BYTES + 2u * RBCT_CHUNK_BYTES];
  rbct_writer_t writer;
  rbct_config_t config = {0};
  FILE* output;
  unsigned index;

  if (argc != 2 && argc != 3) {
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
  if (rbct_writer_clock_sync(&writer, 7u, 0u, 2u, 1000u, 0u) != RBCT_OK) {
    return 4;
  }
  for (index = 1; index <= 672u; ++index) {
    if (INTEROP_TRACE_EMIT_ADDRESS(&writer, index, 0u, 0u) != RBCT_OK) {
      return 5;
    }
  }
  if (rbct_writer_clock_sync(&writer, 8u, 0u, 2u, 2000u, 0u) != RBCT_OK) {
    return 6;
  }
  if (argc == 2 && rbct_writer_finalize(&writer) != RBCT_OK) {
    return 7;
  }
  output = fopen(argv[1], "wb");
  if (output == NULL) {
    return 8;
  }
  if (fwrite(rbct_writer_data(&writer), 1, rbct_writer_size(&writer), output) !=
      rbct_writer_size(&writer)) {
    fclose(output);
    return 9;
  }
  if (fclose(output) != 0) {
    return 10;
  }
  return 0;
}
