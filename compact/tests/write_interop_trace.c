#include "interop_schema.h"
#include "retrobus/compact_trace.h"

#include <stdio.h>

int main(int argc, char **argv) {
    unsigned char buffer[RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES];
    rbct_scope_t scopes[4];
    rbct_writer_t writer;
    rbct_config_t config = {0};
    rbct_argument_t argument;
    FILE *output;
    unsigned index;

    if (argc != 2) {
        return 2;
    }
    config.clock_rate_numerator = 1000000;
    config.clock_rate_denominator = 1;
    config.clock_width_bits = 32;
    config.producer_id = INTEROP_TRACE_PRODUCER_ID;
    config.schema_version = INTEROP_TRACE_SCHEMA_VERSION;
    config.initial_clock_generation = 7;
    for (index = 0; index < 32; ++index) {
        config.schema_sha256[index] = INTEROP_TRACE_SCHEMA_SHA256[index];
    }
    if (rbct_writer_init(&writer, buffer, sizeof(buffer), scopes, 4, &config) != RBCT_OK) {
        return 3;
    }
    if (rbct_writer_clock_sync(&writer, 7, 100, 102, 1000000, 300) != RBCT_OK) {
        return 4;
    }
    argument = rbct_argument_u64(42);
    if (rbct_writer_begin(&writer, 110, 0, INTEROP_TRACE_EVENT_WORK,
                          &argument, 1) != RBCT_OK) {
        return 5;
    }
    argument = rbct_argument_i64(-7);
    if (rbct_writer_emit(&writer, 120, 0, INTEROP_TRACE_EVENT_FAULT,
                         &argument, 1) != RBCT_OK) {
        return 6;
    }
    if (rbct_writer_end(&writer, 150) != RBCT_OK) {
        return 7;
    }
    argument = rbct_argument_u64(99);
    if (rbct_writer_emit(&writer, 160, 1, INTEROP_TRACE_EVENT_BYTES,
                         &argument, 1) != RBCT_OK) {
        return 8;
    }
    argument = rbct_argument_fixed64(UINT64_C(0xdeadbeef12345678));
    if (rbct_writer_emit(&writer, 170, 0, INTEROP_TRACE_EVENT_ADDRESS,
                         &argument, 1) != RBCT_OK) {
        return 9;
    }
    if (rbct_writer_finalize(&writer) != RBCT_OK) {
        return 10;
    }
    output = fopen(argv[1], "wb");
    if (output == NULL) {
        return 11;
    }
    if (fwrite(rbct_writer_data(&writer), 1, rbct_writer_size(&writer), output) !=
        rbct_writer_size(&writer)) {
        fclose(output);
        return 12;
    }
    if (fclose(output) != 0) {
        return 13;
    }
    return 0;
}
