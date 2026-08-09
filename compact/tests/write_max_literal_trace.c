#include "interop_schema.h"
#include "retrobus/compact_trace.h"

#include <stdio.h>

int main(int argc, char** argv) {
  union {
    uint32_t alignment;
    unsigned char bytes[RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES];
  } storage;
  rbct_scope_t scope;
  rbct_writer_t writer;
  rbct_config_t config = {0};
  rbct_argument_t arguments[4];
  FILE* output;
  unsigned index;
  if (argc != 2) {
    return 2;
  }
  config.clock_rate_numerator = 1;
  config.clock_rate_denominator = 1;
  config.clock_width_bits = 64;
  config.producer_id = INTEROP_TRACE_PRODUCER_ID;
  config.schema_version = INTEROP_TRACE_SCHEMA_VERSION;
  for (index = 0; index < 32; ++index) {
    config.schema_sha256[index] = INTEROP_TRACE_SCHEMA_SHA256[index];
  }
  for (index = 0; index < 4; ++index) {
    arguments[index] = rbct_argument_u64(UINT64_MAX);
  }
  if (rbct_writer_init(&writer, storage.bytes, sizeof(storage.bytes), &scope, 1,
                       &config) != RBCT_OK) {
    return 3;
  }
  if (rbct_writer_emit(&writer, 0, 0, 21, NULL, 0) != RBCT_OK) {
    return 4;
  }
  if (rbct_writer_begin(&writer, 0, UINT32_MAX, UINT32_MAX, arguments, 4) !=
          RBCT_OK ||
      rbct_writer_end(&writer, (UINT64_C(1) << 63) - 1) != RBCT_OK) {
    return 5;
  }
  if (rbct_writer_finalize(&writer) != RBCT_OK) {
    return 6;
  }
  output = fopen(argv[1], "wb");
  if (output == NULL) {
    return 7;
  }
  if (fwrite(storage.bytes, 1, sizeof(storage.bytes), output) !=
      sizeof(storage.bytes)) {
    fclose(output);
    return 8;
  }
  return fclose(output) == 0 ? 0 : 9;
}
