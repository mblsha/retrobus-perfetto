#include "retrobus/compact_trace.h"

#include <limits.h>

#define RBCT_CHUNK_MAGIC_0 ((uint8_t)'R')
#define RBCT_CHUNK_MAGIC_1 ((uint8_t)'B')
#define RBCT_CHUNK_MAGIC_2 ((uint8_t)'C')
#define RBCT_CHUNK_MAGIC_3 ((uint8_t)'K')
#define RBCT_CONTROL_CLOCK_SYNC 0xfdu
#define RBCT_CONTROL_TRACK 0xfeu
#define RBCT_CONTROL_EXTENDED_EVENT 0xffu
#define RBCT_FLAG_FINALIZED 0x0001u
#define RBCT_FLAG_RING_WRAPPED 0x0002u
#define RBCT_NO_CHUNK ((size_t)-1)
#define RBCT_SCRATCH_BYTES 128u

static void rbct_zero(uint8_t* destination, size_t size) {
  size_t index;
  for (index = 0; index < size; ++index) {
    destination[index] = 0;
  }
}

static void rbct_copy(uint8_t* destination,
                      const uint8_t* source,
                      size_t size) {
  size_t index;
  for (index = 0; index < size; ++index) {
    destination[index] = source[index];
  }
}

static void rbct_put_u16(uint8_t* destination, size_t offset, uint16_t value) {
  destination[offset] = (uint8_t)(value & 0xffu);
  destination[offset + 1u] = (uint8_t)((value >> 8u) & 0xffu);
}

static void rbct_put_u32(uint8_t* destination, size_t offset, uint32_t value) {
  size_t index;
  for (index = 0; index < 4u; ++index) {
    destination[offset + index] = (uint8_t)((value >> (index * 8u)) & 0xffu);
  }
}

static void rbct_put_u64(uint8_t* destination, size_t offset, uint64_t value) {
  size_t index;
  for (index = 0; index < 8u; ++index) {
    destination[offset + index] = (uint8_t)((value >> (index * 8u)) & 0xffu);
  }
}

static uint16_t rbct_get_u16(const uint8_t* source, size_t offset) {
  return (uint16_t)((uint16_t)source[offset] |
                    ((uint16_t)source[offset + 1u] << 8u));
}

static uint32_t rbct_get_u32(const uint8_t* source, size_t offset) {
  uint32_t value = 0;
  size_t index;
  for (index = 0; index < 4u; ++index) {
    value |= (uint32_t)source[offset + index] << (index * 8u);
  }
  return value;
}

static uint32_t rbct_crc32(const uint8_t* source, size_t size) {
  uint32_t crc = 0xffffffffu;
  size_t index;
  for (index = 0; index < size; ++index) {
    unsigned bit;
    crc ^= source[index];
    for (bit = 0; bit < 8u; ++bit) {
      const uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);
      crc = (crc >> 1u) ^ (0xedb88320u & mask);
    }
  }
  return ~crc;
}

static int rbct_append_varint(uint8_t* destination,
                              size_t capacity,
                              size_t* size,
                              uint64_t value) {
  do {
    uint8_t byte;
    if (*size >= capacity) {
      return 0;
    }
    byte = (uint8_t)(value & 0x7fu);
    value >>= 7u;
    if (value != 0u) {
      byte |= 0x80u;
    }
    destination[(*size)++] = byte;
  } while (value != 0u);
  return 1;
}

static int rbct_append_fixed64(uint8_t* destination,
                               size_t capacity,
                               size_t* size,
                               uint64_t value) {
  size_t index;
  if (*size > capacity || capacity - *size < 8u) {
    return 0;
  }
  for (index = 0; index < 8u; ++index) {
    destination[(*size)++] = (uint8_t)((value >> (index * 8u)) & 0xffu);
  }
  return 1;
}

static uint64_t rbct_clock_mask(const rbct_writer_t* writer) {
  if (writer->clock_width_bits == 64u) {
    return UINT64_MAX;
  }
  return ((uint64_t)1u << writer->clock_width_bits) - 1u;
}

static uint64_t rbct_clock_delta(const rbct_writer_t* writer,
                                 uint64_t newer,
                                 uint64_t older) {
  return (newer - older) & rbct_clock_mask(writer);
}

static uint8_t* rbct_chunk(rbct_writer_t* writer, size_t index) {
  return writer->buffer + RBCT_FILE_HEADER_BYTES + index * RBCT_CHUNK_BYTES;
}

static void rbct_sync_header_counts(rbct_writer_t* writer) {
  uint8_t* header = writer->buffer;
  rbct_put_u64(header, 96u, writer->total_records);
  rbct_put_u64(header, 104u, writer->overwritten_records);
  rbct_put_u64(header, 112u, writer->dropped_records);
  rbct_put_u64(header, 120u, writer->total_events);
  rbct_put_u64(header, 128u, writer->overwritten_events);
}

static void rbct_start_chunk(rbct_writer_t* writer,
                             uint32_t generation,
                             uint64_t base_timestamp) {
  size_t next;
  uint8_t* chunk;
  if (writer->current_chunk == RBCT_NO_CHUNK) {
    next = 0u;
  } else {
    next = writer->current_chunk + 1u;
    if (next == writer->chunk_count) {
      next = 0u;
    }
  }
  if (writer->valid_chunks == writer->chunk_count) {
    const uint8_t* old = rbct_chunk(writer, next);
    writer->overwritten_records += rbct_get_u16(old, 30u);
    writer->overwritten_events += rbct_get_u32(old, 32u);
  } else {
    ++writer->valid_chunks;
  }

  chunk = rbct_chunk(writer, next);
  rbct_zero(chunk, RBCT_CHUNK_BYTES);
  chunk[0] = RBCT_CHUNK_MAGIC_0;
  chunk[1] = RBCT_CHUNK_MAGIC_1;
  chunk[2] = RBCT_CHUNK_MAGIC_2;
  chunk[3] = RBCT_CHUNK_MAGIC_3;
  rbct_put_u64(chunk, 4u, writer->next_sequence++);
  rbct_put_u64(chunk, 12u, base_timestamp);
  rbct_put_u32(chunk, 20u, generation);
  rbct_put_u32(chunk, 24u, writer->default_track);
  writer->current_chunk = next;
  writer->current_generation = generation;
  writer->current_timestamp = base_timestamp;
  writer->current_track = writer->default_track;
}

static int rbct_encode_event(const rbct_writer_t* writer,
                             uint8_t* encoded,
                             size_t capacity,
                             size_t* encoded_size,
                             uint64_t timestamp,
                             uint32_t track_id,
                             uint32_t event_id,
                             int has_duration,
                             uint64_t duration,
                             const rbct_argument_t* arguments,
                             size_t argument_count) {
  size_t index;
  *encoded_size = 0u;
  if (track_id != writer->current_track) {
    if (*encoded_size >= capacity) {
      return 0;
    }
    encoded[(*encoded_size)++] = RBCT_CONTROL_TRACK;
    if (!rbct_append_varint(encoded, capacity, encoded_size, track_id)) {
      return 0;
    }
  }
  if (event_id <= RBCT_DIRECT_EVENT_ID_MAX) {
    if (*encoded_size >= capacity) {
      return 0;
    }
    encoded[(*encoded_size)++] = (uint8_t)event_id;
  } else {
    if (*encoded_size >= capacity) {
      return 0;
    }
    encoded[(*encoded_size)++] = RBCT_CONTROL_EXTENDED_EVENT;
    if (!rbct_append_varint(encoded, capacity, encoded_size, event_id)) {
      return 0;
    }
  }
  if (!rbct_append_varint(
          encoded, capacity, encoded_size,
          rbct_clock_delta(writer, timestamp, writer->current_timestamp))) {
    return 0;
  }
  if (has_duration &&
      !rbct_append_varint(encoded, capacity, encoded_size, duration)) {
    return 0;
  }
  for (index = 0; index < argument_count; ++index) {
    if (arguments[index].encoding == RBCT_ARGUMENT_ULEB128) {
      if (!rbct_append_varint(encoded, capacity, encoded_size,
                              arguments[index].bits)) {
        return 0;
      }
    } else if (arguments[index].encoding == RBCT_ARGUMENT_FIXED64) {
      if (!rbct_append_fixed64(encoded, capacity, encoded_size,
                               arguments[index].bits)) {
        return 0;
      }
    } else {
      return 0;
    }
  }
  return 1;
}

static rbct_status_t rbct_append_event(rbct_writer_t* writer,
                                       uint64_t timestamp,
                                       uint32_t track_id,
                                       uint32_t event_id,
                                       int has_duration,
                                       uint64_t duration,
                                       const rbct_argument_t* arguments,
                                       size_t argument_count,
                                       uint32_t expanded_events) {
  uint8_t encoded[RBCT_SCRATCH_BYTES];
  size_t encoded_size = 0u;
  uint8_t* chunk;
  uint16_t used;

  if (writer == NULL || !rbct_writer_enabled(writer)) {
    return RBCT_INVALID_STATE;
  }
  if (argument_count > RBCT_MAX_ARGUMENTS ||
      (argument_count != 0u && arguments == NULL)) {
    ++writer->dropped_records;
    return RBCT_INVALID_ARGUMENT;
  }
  if (writer->current_chunk == RBCT_NO_CHUNK) {
    rbct_start_chunk(writer, writer->current_generation, timestamp);
  }
  if (!rbct_encode_event(writer, encoded, sizeof(encoded), &encoded_size,
                         timestamp, track_id, event_id, has_duration, duration,
                         arguments, argument_count)) {
    ++writer->dropped_records;
    return RBCT_RECORD_TOO_LARGE;
  }

  chunk = rbct_chunk(writer, writer->current_chunk);
  used = rbct_get_u16(chunk, 28u);
  if (encoded_size > RBCT_CHUNK_BYTES - RBCT_CHUNK_HEADER_BYTES - used) {
    rbct_start_chunk(writer, writer->current_generation, timestamp);
    if (!rbct_encode_event(writer, encoded, sizeof(encoded), &encoded_size,
                           timestamp, track_id, event_id, has_duration,
                           duration, arguments, argument_count)) {
      ++writer->dropped_records;
      return RBCT_RECORD_TOO_LARGE;
    }
    chunk = rbct_chunk(writer, writer->current_chunk);
    used = 0u;
  }
  if (encoded_size > RBCT_CHUNK_BYTES - RBCT_CHUNK_HEADER_BYTES - used) {
    ++writer->dropped_records;
    return RBCT_RECORD_TOO_LARGE;
  }

  rbct_copy(chunk + RBCT_CHUNK_HEADER_BYTES + used, encoded, encoded_size);
  rbct_put_u16(chunk, 28u, (uint16_t)(used + encoded_size));
  rbct_put_u16(chunk, 30u, (uint16_t)(rbct_get_u16(chunk, 30u) + 1u));
  rbct_put_u32(chunk, 32u, rbct_get_u32(chunk, 32u) + expanded_events);
  writer->current_timestamp = timestamp;
  writer->current_track = track_id;
  ++writer->total_records;
  writer->total_events += expanded_events;
  return RBCT_OK;
}

size_t rbct_required_buffer_bytes(size_t chunk_count) {
  if (chunk_count == 0u ||
      chunk_count > (SIZE_MAX - RBCT_FILE_HEADER_BYTES) / RBCT_CHUNK_BYTES) {
    return 0u;
  }
  return RBCT_FILE_HEADER_BYTES + chunk_count * RBCT_CHUNK_BYTES;
}

rbct_status_t rbct_writer_init(rbct_writer_t* writer,
                               void* buffer,
                               size_t buffer_bytes,
                               rbct_scope_t* scope_storage,
                               size_t scope_capacity,
                               const rbct_config_t* config) {
  size_t chunk_count;
  size_t usable_bytes;
  uint8_t* header;
  if (writer == NULL || buffer == NULL || config == NULL ||
      config->clock_rate_numerator == 0u ||
      config->clock_rate_denominator == 0u || config->clock_width_bits == 0u ||
      config->clock_width_bits > 64u ||
      (scope_capacity != 0u && scope_storage == NULL) ||
      buffer_bytes < RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES) {
    return RBCT_INVALID_ARGUMENT;
  }
  chunk_count = (buffer_bytes - RBCT_FILE_HEADER_BYTES) / RBCT_CHUNK_BYTES;
  usable_bytes = rbct_required_buffer_bytes(chunk_count);
  if (usable_bytes == 0u) {
    return RBCT_INVALID_ARGUMENT;
  }

  rbct_zero((uint8_t*)writer, sizeof(*writer));
  rbct_zero((uint8_t*)buffer, usable_bytes);
  writer->buffer = (uint8_t*)buffer;
  writer->buffer_bytes = usable_bytes;
  writer->chunk_count = chunk_count;
  writer->current_chunk = RBCT_NO_CHUNK;
  writer->current_generation = config->initial_clock_generation;
  writer->current_track = config->default_track_id;
  writer->default_track = config->default_track_id;
  writer->clock_width_bits = config->clock_width_bits;
  writer->scopes = scope_storage;
  writer->scope_capacity = scope_capacity;
  writer->initialized = 1u;

  header = writer->buffer;
  header[0] = (uint8_t)'R';
  header[1] = (uint8_t)'B';
  header[2] = (uint8_t)'C';
  header[3] = (uint8_t)'T';
  header[4] = (uint8_t)'R';
  header[5] = (uint8_t)'C';
  header[6] = (uint8_t)'1';
  header[7] = 0u;
  rbct_put_u16(header, 8u, RBCT_FORMAT_VERSION);
  rbct_put_u16(header, 10u, RBCT_FILE_HEADER_BYTES);
  rbct_put_u16(header, 12u, RBCT_CHUNK_HEADER_BYTES);
  rbct_put_u32(header, 16u, RBCT_CHUNK_BYTES);
  rbct_put_u64(header, 20u, config->clock_rate_numerator);
  rbct_put_u64(header, 28u, config->clock_rate_denominator);
  rbct_put_u16(header, 36u, config->clock_width_bits);
  rbct_put_u32(header, 40u, config->producer_id);
  rbct_put_u32(header, 44u, config->schema_version);
  rbct_copy(header + 48u, config->schema_sha256, 32u);
  rbct_copy(header + 80u, config->session_id, 16u);
  rbct_put_u64(header, 136u, usable_bytes);
  rbct_put_u32(header, 144u, config->initial_clock_generation);
  rbct_put_u32(header, 148u, config->default_track_id);
  return RBCT_OK;
}

int rbct_writer_enabled(const rbct_writer_t* writer) {
  return writer != NULL && writer->initialized != 0u && writer->finalized == 0u;
}

rbct_status_t rbct_writer_begin(rbct_writer_t* writer,
                                uint64_t timestamp,
                                uint32_t track_id,
                                uint32_t event_id,
                                const rbct_argument_t* arguments,
                                size_t argument_count) {
  rbct_scope_t* scope;
  size_t index;
  if (writer == NULL || !rbct_writer_enabled(writer)) {
    return RBCT_INVALID_STATE;
  }
  if (argument_count > RBCT_MAX_ARGUMENTS ||
      (argument_count != 0u && arguments == NULL) ||
      writer->scope_depth == writer->scope_capacity) {
    ++writer->dropped_records;
    return RBCT_INVALID_ARGUMENT;
  }
  scope = &writer->scopes[writer->scope_depth++];
  scope->started_at = timestamp;
  scope->track_id = track_id;
  scope->event_id = event_id;
  scope->argument_count = (uint8_t)argument_count;
  for (index = 0; index < argument_count; ++index) {
    scope->arguments[index].bits = arguments[index].bits;
    scope->arguments[index].encoding = arguments[index].encoding;
  }
  return RBCT_OK;
}

rbct_status_t rbct_writer_end(rbct_writer_t* writer, uint64_t timestamp) {
  const rbct_scope_t* scope;
  if (writer == NULL || !rbct_writer_enabled(writer) ||
      writer->scope_depth == 0u) {
    if (writer != NULL && rbct_writer_enabled(writer)) {
      ++writer->dropped_records;
    }
    return RBCT_INVALID_STATE;
  }
  --writer->scope_depth;
  scope = &writer->scopes[writer->scope_depth];
  return rbct_append_event(
      writer, timestamp, scope->track_id, scope->event_id, 1,
      rbct_clock_delta(writer, timestamp, scope->started_at), scope->arguments,
      scope->argument_count, 2u);
}

rbct_status_t rbct_writer_emit(rbct_writer_t* writer,
                               uint64_t timestamp,
                               uint32_t track_id,
                               uint32_t event_id,
                               const rbct_argument_t* arguments,
                               size_t argument_count) {
  return rbct_append_event(writer, timestamp, track_id, event_id, 0, 0u,
                           arguments, argument_count, 1u);
}

rbct_status_t rbct_writer_clock_sync(rbct_writer_t* writer,
                                     uint32_t generation,
                                     uint64_t counter_before,
                                     uint64_t counter_after,
                                     uint64_t reference_timestamp_ns,
                                     uint64_t uncertainty_ns) {
  uint8_t encoded[RBCT_SCRATCH_BYTES];
  size_t encoded_size = 0u;
  uint8_t* chunk;
  uint16_t used;
  if (writer == NULL || !rbct_writer_enabled(writer)) {
    return RBCT_INVALID_STATE;
  }
  encoded[encoded_size++] = RBCT_CONTROL_CLOCK_SYNC;
  if (!rbct_append_varint(encoded, sizeof(encoded), &encoded_size,
                          generation) ||
      !rbct_append_varint(encoded, sizeof(encoded), &encoded_size,
                          counter_before) ||
      !rbct_append_varint(encoded, sizeof(encoded), &encoded_size,
                          counter_after) ||
      !rbct_append_varint(encoded, sizeof(encoded), &encoded_size,
                          reference_timestamp_ns) ||
      !rbct_append_varint(encoded, sizeof(encoded), &encoded_size,
                          uncertainty_ns)) {
    return RBCT_RECORD_TOO_LARGE;
  }
  if (writer->current_chunk == RBCT_NO_CHUNK ||
      writer->current_generation != generation) {
    rbct_start_chunk(writer, generation, counter_before);
  }
  chunk = rbct_chunk(writer, writer->current_chunk);
  used = rbct_get_u16(chunk, 28u);
  if (encoded_size > RBCT_CHUNK_BYTES - RBCT_CHUNK_HEADER_BYTES - used) {
    rbct_start_chunk(writer, generation, counter_before);
    chunk = rbct_chunk(writer, writer->current_chunk);
    used = 0u;
  }
  rbct_copy(chunk + RBCT_CHUNK_HEADER_BYTES + used, encoded, encoded_size);
  rbct_put_u16(chunk, 28u, (uint16_t)(used + encoded_size));
  rbct_put_u16(chunk, 36u, (uint16_t)(rbct_get_u16(chunk, 36u) + 1u));
  return RBCT_OK;
}

rbct_status_t rbct_writer_finalize(rbct_writer_t* writer) {
  size_t index;
  uint16_t flags = RBCT_FLAG_FINALIZED;
  if (writer == NULL || !rbct_writer_enabled(writer) ||
      writer->scope_depth != 0u) {
    return RBCT_INVALID_STATE;
  }
  if (writer->valid_chunks == writer->chunk_count &&
      writer->next_sequence > writer->chunk_count) {
    flags |= RBCT_FLAG_RING_WRAPPED;
  }
  for (index = 0; index < writer->chunk_count; ++index) {
    uint8_t* chunk = rbct_chunk(writer, index);
    if (chunk[0] == RBCT_CHUNK_MAGIC_0 && chunk[1] == RBCT_CHUNK_MAGIC_1 &&
        chunk[2] == RBCT_CHUNK_MAGIC_2 && chunk[3] == RBCT_CHUNK_MAGIC_3) {
      const uint16_t used = rbct_get_u16(chunk, 28u);
      rbct_put_u32(chunk, 40u,
                   rbct_crc32(chunk + RBCT_CHUNK_HEADER_BYTES, used));
    }
  }
  rbct_sync_header_counts(writer);
  rbct_put_u16(writer->buffer, 38u, flags);
  rbct_put_u32(writer->buffer, 152u, 0u);
  rbct_put_u32(writer->buffer, 152u,
               rbct_crc32(writer->buffer, RBCT_FILE_HEADER_BYTES));
  writer->finalized = 1u;
  return RBCT_OK;
}

const void* rbct_writer_data(const rbct_writer_t* writer) {
  return writer == NULL ? NULL : writer->buffer;
}

size_t rbct_writer_size(const rbct_writer_t* writer) {
  return writer == NULL ? 0u : writer->buffer_bytes;
}
