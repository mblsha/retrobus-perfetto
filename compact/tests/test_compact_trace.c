#include "retrobus/compact_trace.h"

#include <assert.h>
#include <stdint.h>

static uint16_t get_u16(const uint8_t *data, size_t offset) {
    return (uint16_t)((uint16_t)data[offset] | ((uint16_t)data[offset + 1u] << 8u));
}

static uint64_t get_u64(const uint8_t *data, size_t offset) {
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
    const uint8_t *data;

    config.clock_rate_numerator = 3686400u;
    config.clock_rate_denominator = 1u;
    config.clock_width_bits = 32u;
    config.producer_id = 42u;
    config.schema_version = 3u;
    config.initial_clock_generation = 7u;

    assert(rbct_required_buffer_bytes(2u) == sizeof(buffer));
    assert(rbct_writer_init(&writer, buffer, sizeof(buffer), scopes, 4u, &config) == RBCT_OK);
    assert(rbct_writer_enabled(&writer));
    assert(rbct_writer_clock_sync(&writer, 7u, 100u, 102u, 1000000u, 300u) == RBCT_OK);
    assert(rbct_writer_begin(&writer, 110u, 0u, 1u, &amount, 1u) == RBCT_OK);
    assert(rbct_writer_emit(&writer, 120u, 0u, 2u, &negative, 1u) == RBCT_OK);
    assert(rbct_writer_end(&writer, 150u) == RBCT_OK);
    assert(rbct_writer_emit(&writer, 160u, 1u, 300u, &amount, 1u) == RBCT_OK);
    assert(rbct_writer_finalize(&writer) == RBCT_OK);
    assert(!rbct_writer_enabled(&writer));

    data = (const uint8_t *)rbct_writer_data(&writer);
    assert(data != 0);
    assert(data[0] == 'R' && data[1] == 'B' && data[6] == '1');
    assert((get_u16(data, 38u) & 1u) != 0u);
    assert(get_u64(data, 96u) == 3u);
    assert(get_u64(data, 120u) == 4u);
    assert(get_u16(data + RBCT_FILE_HEADER_BYTES, 30u) == 3u);
    assert(get_u16(data + RBCT_FILE_HEADER_BYTES, 36u) == 1u);
    assert(rbct_writer_size(&writer) == sizeof(buffer));

    assert(rbct_writer_init(&writer, buffer,
                            RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES,
                            0, 0, &config) == RBCT_OK);
    {
        unsigned index;
        for (index = 0; index < 3000u; ++index) {
            assert(rbct_writer_emit(&writer, index, 0u, 2u, 0, 0) == RBCT_OK);
        }
    }
    assert(rbct_writer_finalize(&writer) == RBCT_OK);
    data = (const uint8_t *)rbct_writer_data(&writer);
    assert((get_u16(data, 38u) & 2u) != 0u);
    assert(get_u64(data, 96u) == 3000u);
    assert(get_u64(data, 104u) > 0u);
    assert(get_u64(data, 104u) < get_u64(data, 96u));
    return 0;
}
