#include "interop_codec.h"
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
  FILE* output;
  unsigned index;
  if (argc != 2 && argc != 3) {
    return 2;
  }
  config.clock_rate_numerator = 1000000;
  config.clock_rate_denominator = 1;
  config.clock_width_bits = 32;
  config.producer_id = INTEROP_TRACE_PRODUCER_ID;
  config.schema_version = INTEROP_TRACE_SCHEMA_VERSION;
  config.codec_profile = argc == 2 ? &INTEROP_CODEC_PROFILE : NULL;
  for (index = 0; index < 32; ++index) {
    config.schema_sha256[index] = INTEROP_TRACE_SCHEMA_SHA256[index];
  }
  if (rbct_writer_init(&writer, storage.bytes, sizeof(storage.bytes), &scope, 1,
                       &config) != RBCT_OK) {
    return 3;
  }
  for (index = 0; index < 1000; ++index) {
    if (INTEROP_TRACE_BEGIN_IDLE(&writer, index, 0) != RBCT_OK ||
        rbct_writer_end(&writer, index + 1) != RBCT_OK) {
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
  if (fwrite(storage.bytes, 1, sizeof(storage.bytes), output) !=
      sizeof(storage.bytes)) {
    fclose(output);
    return 7;
  }
  return fclose(output) == 0 ? 0 : 8;
}
