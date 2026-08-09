#include "retrobus/compact_trace.h"

#include <limits.h>

#if defined(_MSC_VER)
#include <intrin.h>
#if !defined(_M_ARM) && !defined(_M_ARM64) && !defined(_M_ARM64EC)
#pragma intrinsic(_ReadWriteBarrier)
#endif
#endif

#define RBCT_CHUNK_MAGIC_0 ((uint8_t)'R')
#define RBCT_CHUNK_MAGIC_1 ((uint8_t)'B')
#define RBCT_CHUNK_MAGIC_2 ((uint8_t)'C')
#define RBCT_CHUNK_MAGIC_3 ((uint8_t)'K')
#define RBCT_CONTROL_CLOCK_SYNC 0xfdu
#define RBCT_CONTROL_TRACK 0xfeu
#define RBCT_CONTROL_EXTENDED_EVENT 0xffu
#define RBCT_FLAG_FINALIZED 0x0001u
#define RBCT_FLAG_RING_WRAPPED 0x0002u
#define RBCT_FLAG_CHUNK_HEADER_CRC 0x0004u
#define RBCT_NO_CHUNK ((size_t)-1)
#define RBCT_STATE_INITIALIZED 0x01u
#define RBCT_STATE_FINALIZED 0x02u
#define RBCT_STATE_GENERATION_HAS_RECORD 0x04u
#define RBCT_STATE_GENERATION_HAS_SYNC 0x08u
#define RBCT_STATE_SYNC_ADVANCED 0x10u
/*
 * Maximum event body: track and event controls plus uint32 IDs (12 bytes),
 * half-range-bounded timestamp delta and duration (18), and four uint64
 * ULEB128 arguments (40).
 */
#define RBCT_FRAME_DELTA_ZERO_BASE RBCT_MAX_RECORD_BYTES
#define RBCT_FRAME_DELTA_ONE_BASE (2u * RBCT_MAX_RECORD_BYTES)
#define RBCT_FRAME_INLINE_ZERO_BASE (3u * RBCT_MAX_RECORD_BYTES)
#define RBCT_FRAME_INLINE_ONE_BASE (RBCT_FRAME_INLINE_ZERO_BASE + 22u)
#define RBCT_INLINE_EVENT_ID_MAX 21u

#ifndef RBCT_PLATFORM_PUBLISH_BARRIER
#if defined(_MSC_VER) && defined(_M_ARM)
#define RBCT_PLATFORM_PUBLISH_BARRIER() __dmb(_ARM_BARRIER_SY)
#elif defined(_MSC_VER) && (defined(_M_ARM64) || defined(_M_ARM64EC))
#define RBCT_PLATFORM_PUBLISH_BARRIER() __dmb(_ARM64_BARRIER_SY)
#elif defined(_MSC_VER)
#define RBCT_PLATFORM_PUBLISH_BARRIER() _ReadWriteBarrier()
#elif (defined(__GNUC__) || defined(__clang__)) && defined(__aarch64__)
#define RBCT_PLATFORM_PUBLISH_BARRIER() \
  __asm__ __volatile__("dmb sy" ::: "memory")
#elif (defined(__GNUC__) || defined(__clang__)) && defined(__arm__) && \
    defined(__ARM_ARCH) && __ARM_ARCH >= 7
#define RBCT_PLATFORM_PUBLISH_BARRIER() \
  __asm__ __volatile__("dmb sy" ::: "memory")
#elif (defined(__GNUC__) || defined(__clang__)) && defined(__riscv)
#define RBCT_PLATFORM_PUBLISH_BARRIER() \
  __asm__ __volatile__("fence w,w" ::: "memory")
#elif defined(__GNUC__) || defined(__clang__)
#define RBCT_PLATFORM_PUBLISH_BARRIER() __asm__ __volatile__("" ::: "memory")
#else
#define RBCT_PLATFORM_PUBLISH_BARRIER() ((void)0)
#endif
#endif

static void rbct_zero(uint8_t* destination, size_t size) {
#if defined(_MSC_VER)
  volatile uint8_t* output = destination;
#else
  uint8_t* output = destination;
#endif
  size_t index;
  for (index = 0; index < size; ++index) {
    output[index] = 0;
  }
}

static void rbct_copy(uint8_t* destination,
                      const uint8_t* source,
                      size_t size) {
#if defined(_MSC_VER)
  volatile uint8_t* output = destination;
#else
  uint8_t* output = destination;
#endif
  size_t index;
  for (index = 0; index < size; ++index) {
    output[index] = source[index];
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

static uint32_t rbct_final_header_crc32(const uint8_t* source,
                                        uint16_t final_flags) {
  uint32_t crc = 0xffffffffu;
  size_t index;
  for (index = 0; index < RBCT_FILE_HEADER_BYTES; ++index) {
    uint8_t byte = source[index];
    unsigned bit;
    if (index == 38u) {
      byte = (uint8_t)(final_flags & 0xffu);
    } else if (index == 39u) {
      byte = (uint8_t)(final_flags >> 8u);
    } else if (index >= 152u && index < 156u) {
      byte = 0u;
    }
    crc ^= byte;
    for (bit = 0; bit < 8u; ++bit) {
      const uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);
      crc = (crc >> 1u) ^ (0xedb88320u & mask);
    }
  }
  return ~crc;
}

static void rbct_append_varint(uint8_t* destination,
                               size_t* size,
                               uint64_t value) {
  do {
    uint8_t byte;
    byte = (uint8_t)(value & 0x7fu);
    value >>= 7u;
    if (value != 0u) {
      byte |= 0x80u;
    }
    destination[(*size)++] = byte;
  } while (value != 0u);
}

static void rbct_append_fixed64(uint8_t* destination,
                                size_t* size,
                                uint64_t value) {
  size_t index;
  for (index = 0; index < 8u; ++index) {
    destination[(*size)++] = (uint8_t)((value >> (index * 8u)) & 0xffu);
  }
}

static size_t rbct_framed_size(size_t encoded_size) {
  return RBCT_RECORD_FRAME_BYTES + encoded_size;
}

static void rbct_commit_record(uint8_t* chunk,
                               uint16_t used,
                               const uint8_t* encoded,
                               size_t encoded_size,
                               uint8_t marker_base) {
  uint8_t* frame = chunk + RBCT_CHUNK_HEADER_BYTES + used;

  /*
   * The one-byte frame marker publishes the record. All supported targets
   * publish a byte atomically. RBCT_PLATFORM_PUBLISH_BARRIER keeps the body
   * ahead of it for the selected target. Platforms without a built-in hardware
   * barrier, or with non-coherent persistence, must override that macro or
   * quiesce and flush the completed buffer according to platform policy.
   */
  rbct_copy(frame + RBCT_RECORD_FRAME_BYTES, encoded, encoded_size);
  RBCT_PLATFORM_PUBLISH_BARRIER();
  frame[0] = (uint8_t)(marker_base + encoded_size);
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

static int rbct_clock_sample_valid(const rbct_writer_t* writer,
                                   uint64_t sample) {
  return (sample & ~rbct_clock_mask(writer)) == 0u;
}

static int rbct_clock_delta_valid(const rbct_writer_t* writer,
                                  uint64_t newer,
                                  uint64_t older) {
  const uint64_t half_range = (uint64_t)1u << (writer->clock_width_bits - 1u);
  return rbct_clock_delta(writer, newer, older) < half_range;
}

static int rbct_arguments_valid(const rbct_argument_t* arguments,
                                size_t argument_count) {
  size_t index;
  if (argument_count > RBCT_MAX_ARGUMENTS ||
      (argument_count != 0u && arguments == NULL)) {
    return 0;
  }
  for (index = 0; index < argument_count; ++index) {
    if (arguments[index].encoding != RBCT_ARGUMENT_ULEB128 &&
        arguments[index].encoding != RBCT_ARGUMENT_FIXED64) {
      return 0;
    }
  }
  return 1;
}

static int rbct_ranges_overlap(const void* left,
                               size_t left_size,
                               const void* right,
                               size_t right_size) {
  const uintptr_t left_begin = (uintptr_t)left;
  const uintptr_t right_begin = (uintptr_t)right;
  uintptr_t left_end;
  uintptr_t right_end;
  if (left_size == 0u || right_size == 0u) {
    return 0;
  }
  if (left_size > UINTPTR_MAX - left_begin ||
      right_size > UINTPTR_MAX - right_begin) {
    return 1;
  }
  left_end = left_begin + left_size;
  right_end = right_begin + right_size;
  return left_begin < right_end && right_begin < left_end;
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
    const uint16_t flags = rbct_get_u16(writer->buffer, 38u);
    writer->overwritten_records += rbct_get_u16(old, 30u);
    writer->overwritten_events += rbct_get_u32(old, 32u);
    if ((flags & RBCT_FLAG_RING_WRAPPED) == 0u) {
      rbct_put_u16(writer->buffer, 38u,
                   (uint16_t)(flags | RBCT_FLAG_RING_WRAPPED));
      RBCT_PLATFORM_PUBLISH_BARRIER();
    }
  } else {
    ++writer->valid_chunks;
  }

  chunk = rbct_chunk(writer, next);
  /* Invalidate an old RBCK marker before any reused contents can change. */
  chunk[0] = 0u;
  RBCT_PLATFORM_PUBLISH_BARRIER();
  rbct_zero(chunk, RBCT_CHUNK_BYTES);
  rbct_put_u64(chunk, 4u, writer->next_sequence++);
  rbct_put_u64(chunk, 12u, base_timestamp);
  rbct_put_u32(chunk, 20u, generation);
  rbct_put_u32(chunk, 24u, writer->default_track);
  /* Publish the first magic byte last so RBCK is the commit marker. */
  chunk[1] = RBCT_CHUNK_MAGIC_1;
  chunk[2] = RBCT_CHUNK_MAGIC_2;
  chunk[3] = RBCT_CHUNK_MAGIC_3;
  RBCT_PLATFORM_PUBLISH_BARRIER();
  chunk[0] = RBCT_CHUNK_MAGIC_0;
  writer->current_chunk = next;
  writer->current_generation = generation;
  writer->current_timestamp = base_timestamp;
  writer->current_track = writer->default_track;
}

static uint8_t rbct_encode_event(const rbct_writer_t* writer,
                                 uint8_t* encoded,
                                 size_t* encoded_size,
                                 uint64_t timestamp_delta,
                                 uint32_t track_id,
                                 uint32_t event_id,
                                 int has_duration,
                                 uint64_t duration,
                                 const rbct_argument_t* arguments,
                                 size_t argument_count) {
  size_t index;
  *encoded_size = 0u;
  if (track_id == writer->current_track &&
      event_id <= RBCT_INLINE_EVENT_ID_MAX && !has_duration &&
      argument_count == 0u && timestamp_delta <= 1u) {
    return (uint8_t)((timestamp_delta == 0u ? RBCT_FRAME_INLINE_ZERO_BASE
                                            : RBCT_FRAME_INLINE_ONE_BASE) +
                     event_id + 1u);
  }
  if (track_id != writer->current_track) {
    encoded[(*encoded_size)++] = RBCT_CONTROL_TRACK;
    rbct_append_varint(encoded, encoded_size, track_id);
  }
  if (event_id <= RBCT_DIRECT_EVENT_ID_MAX) {
    encoded[(*encoded_size)++] = (uint8_t)event_id;
  } else {
    encoded[(*encoded_size)++] = RBCT_CONTROL_EXTENDED_EVENT;
    rbct_append_varint(encoded, encoded_size, event_id);
  }
  if (timestamp_delta > 1u) {
    rbct_append_varint(encoded, encoded_size, timestamp_delta);
  }
  if (has_duration) {
    rbct_append_varint(encoded, encoded_size, duration);
  }
  for (index = 0; index < argument_count; ++index) {
    if (arguments[index].encoding == RBCT_ARGUMENT_ULEB128) {
      rbct_append_varint(encoded, encoded_size, arguments[index].bits);
    } else {
      rbct_append_fixed64(encoded, encoded_size, arguments[index].bits);
    }
  }
  return timestamp_delta <= 1u
             ? (uint8_t)((timestamp_delta + 1u) * RBCT_MAX_RECORD_BYTES)
             : 0u;
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
  uint8_t encoded[RBCT_MAX_RECORD_BYTES];
  size_t encoded_size = 0u;
  uint8_t* chunk;
  uint16_t used;
  uint64_t observation_delta = 0u;
  uint64_t wire_delta;
  uint8_t marker_base;

  if (writer == NULL || !rbct_writer_enabled(writer)) {
    return RBCT_INVALID_STATE;
  }
  if (!rbct_arguments_valid(arguments, argument_count) ||
      !rbct_clock_sample_valid(writer, timestamp) ||
      (writer->current_chunk != RBCT_NO_CHUNK &&
       !rbct_clock_delta_valid(writer, timestamp, writer->current_timestamp)) ||
      (has_duration &&
       !rbct_clock_delta_valid(writer, timestamp, timestamp - duration))) {
    ++writer->dropped_records;
    return RBCT_INVALID_ARGUMENT;
  }
  if (writer->current_chunk != RBCT_NO_CHUNK) {
    observation_delta =
        rbct_clock_delta(writer, timestamp, writer->current_timestamp);
  }
  if (writer->current_chunk == RBCT_NO_CHUNK) {
    rbct_start_chunk(writer, writer->current_generation, timestamp);
  }
  wire_delta = rbct_clock_delta(writer, timestamp, writer->current_timestamp);
  marker_base = rbct_encode_event(writer, encoded, &encoded_size, wire_delta,
                                  track_id, event_id, has_duration, duration,
                                  arguments, argument_count);

  chunk = rbct_chunk(writer, writer->current_chunk);
  used = rbct_get_u16(chunk, 28u);
  if (rbct_framed_size(encoded_size) >
      RBCT_CHUNK_BYTES - RBCT_CHUNK_HEADER_BYTES - used) {
    rbct_start_chunk(writer, writer->current_generation, timestamp);
    wire_delta = 0u;
    marker_base = rbct_encode_event(writer, encoded, &encoded_size, wire_delta,
                                    track_id, event_id, has_duration, duration,
                                    arguments, argument_count);
    chunk = rbct_chunk(writer, writer->current_chunk);
    used = 0u;
  }

  rbct_commit_record(chunk, used, encoded, encoded_size, marker_base);
  rbct_put_u16(chunk, 28u, (uint16_t)(used + rbct_framed_size(encoded_size)));
  rbct_put_u16(chunk, 30u, (uint16_t)(rbct_get_u16(chunk, 30u) + 1u));
  rbct_put_u32(chunk, 32u, rbct_get_u32(chunk, 32u) + expanded_events);
  writer->current_timestamp = timestamp;
  writer->state |= RBCT_STATE_GENERATION_HAS_RECORD;
  if ((writer->state & RBCT_STATE_GENERATION_HAS_SYNC) != 0u &&
      observation_delta != 0u) {
    writer->state |= RBCT_STATE_SYNC_ADVANCED;
  }
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
  size_t scope_bytes;
  size_t usable_bytes;
  uint8_t* header;
  if (writer == NULL || buffer == NULL || config == NULL ||
      config->clock_rate_numerator == 0u ||
      config->clock_rate_denominator == 0u || config->clock_width_bits == 0u ||
      config->clock_width_bits > 64u ||
      (scope_capacity != 0u && scope_storage == NULL) ||
      scope_capacity > SIZE_MAX / sizeof(*scope_storage) ||
      buffer_bytes < RBCT_FILE_HEADER_BYTES + RBCT_CHUNK_BYTES ||
      (buffer_bytes - RBCT_FILE_HEADER_BYTES) % RBCT_CHUNK_BYTES != 0u) {
    return RBCT_INVALID_ARGUMENT;
  }
  chunk_count = (buffer_bytes - RBCT_FILE_HEADER_BYTES) / RBCT_CHUNK_BYTES;
  usable_bytes = rbct_required_buffer_bytes(chunk_count);
  scope_bytes = scope_capacity * sizeof(*scope_storage);
  if (usable_bytes == 0u ||
      rbct_ranges_overlap(writer, sizeof(*writer), buffer, usable_bytes) ||
      rbct_ranges_overlap(writer, sizeof(*writer), scope_storage,
                          scope_bytes) ||
      rbct_ranges_overlap(writer, sizeof(*writer), config, sizeof(*config)) ||
      rbct_ranges_overlap(buffer, usable_bytes, scope_storage, scope_bytes) ||
      rbct_ranges_overlap(buffer, usable_bytes, config, sizeof(*config)) ||
      rbct_ranges_overlap(scope_storage, scope_bytes, config,
                          sizeof(*config))) {
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
  writer->state = RBCT_STATE_INITIALIZED;

  header = writer->buffer;
  header[0] = (uint8_t)'R';
  header[1] = (uint8_t)'B';
  header[2] = (uint8_t)'C';
  header[3] = (uint8_t)'T';
  header[4] = (uint8_t)'R';
  header[5] = (uint8_t)'C';
  header[6] = (uint8_t)'2';
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
  return writer != NULL && (writer->state & RBCT_STATE_INITIALIZED) != 0u &&
         (writer->state & RBCT_STATE_FINALIZED) == 0u;
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
  if (!rbct_arguments_valid(arguments, argument_count) ||
      !rbct_clock_sample_valid(writer, timestamp) ||
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
  rbct_status_t status;
  if (writer == NULL || !rbct_writer_enabled(writer) ||
      writer->scope_depth == 0u) {
    if (writer != NULL && rbct_writer_enabled(writer)) {
      ++writer->dropped_records;
    }
    return RBCT_INVALID_STATE;
  }
  scope = &writer->scopes[writer->scope_depth - 1u];
  status =
      rbct_append_event(writer, timestamp, scope->track_id, scope->event_id, 1,
                        rbct_clock_delta(writer, timestamp, scope->started_at),
                        scope->arguments, scope->argument_count, 2u);
  if (status == RBCT_OK) {
    --writer->scope_depth;
  } else if (writer->dropped_records != 0u) {
    /* The scope remains retryable and has not yet been dropped. */
    --writer->dropped_records;
  }
  return status;
}

rbct_status_t rbct_writer_cancel(rbct_writer_t* writer) {
  if (writer == NULL || !rbct_writer_enabled(writer) ||
      writer->scope_depth == 0u) {
    return RBCT_INVALID_STATE;
  }
  --writer->scope_depth;
  ++writer->dropped_records;
  return RBCT_OK;
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
  uint8_t encoded[RBCT_MAX_RECORD_BYTES];
  size_t encoded_size = 0u;
  uint8_t* chunk;
  uint16_t used;
  uint64_t midpoint;
  uint64_t serialized_delta = 0u;
  int generation_transition;
  if (writer == NULL || !rbct_writer_enabled(writer)) {
    return RBCT_INVALID_STATE;
  }
  generation_transition = writer->current_generation != generation;
  if (generation_transition && writer->scope_depth != 0u) {
    return RBCT_INVALID_STATE;
  }
  if (generation_transition && generation != writer->current_generation + 1u) {
    return RBCT_INVALID_ARGUMENT;
  }
  if (!rbct_clock_sample_valid(writer, counter_before) ||
      !rbct_clock_sample_valid(writer, counter_after) ||
      !rbct_clock_delta_valid(writer, counter_after, counter_before)) {
    return RBCT_INVALID_ARGUMENT;
  }
  midpoint = (counter_before +
              rbct_clock_delta(writer, counter_after, counter_before) / 2u) &
             rbct_clock_mask(writer);
  if ((writer->state & RBCT_STATE_GENERATION_HAS_RECORD) != 0u &&
      (writer->state & RBCT_STATE_GENERATION_HAS_SYNC) == 0u) {
    return RBCT_INVALID_ARGUMENT;
  }
  if (!generation_transition && writer->current_chunk != RBCT_NO_CHUNK) {
    if (!rbct_clock_delta_valid(writer, midpoint, writer->current_timestamp)) {
      return RBCT_INVALID_ARGUMENT;
    }
    serialized_delta =
        rbct_clock_delta(writer, midpoint, writer->current_timestamp);
    if ((writer->state & RBCT_STATE_GENERATION_HAS_SYNC) != 0u &&
        (writer->state & RBCT_STATE_SYNC_ADVANCED) == 0u &&
        serialized_delta == 0u) {
      return RBCT_INVALID_ARGUMENT;
    }
  }
  encoded[encoded_size++] = RBCT_CONTROL_CLOCK_SYNC;
  rbct_append_varint(encoded, &encoded_size, generation);
  rbct_append_varint(encoded, &encoded_size, counter_before);
  rbct_append_varint(encoded, &encoded_size, counter_after);
  rbct_append_varint(encoded, &encoded_size, reference_timestamp_ns);
  rbct_append_varint(encoded, &encoded_size, uncertainty_ns);
  if (writer->current_chunk == RBCT_NO_CHUNK || generation_transition) {
    rbct_start_chunk(writer, generation, counter_before);
    if (generation_transition) {
      writer->state &=
          (uint8_t)~(RBCT_STATE_GENERATION_HAS_RECORD |
                     RBCT_STATE_GENERATION_HAS_SYNC | RBCT_STATE_SYNC_ADVANCED);
    }
  }
  chunk = rbct_chunk(writer, writer->current_chunk);
  used = rbct_get_u16(chunk, 28u);
  if (rbct_framed_size(encoded_size) >
      RBCT_CHUNK_BYTES - RBCT_CHUNK_HEADER_BYTES - used) {
    rbct_start_chunk(writer, generation, counter_before);
    chunk = rbct_chunk(writer, writer->current_chunk);
    used = 0u;
  }
  rbct_commit_record(chunk, used, encoded, encoded_size, 0u);
  rbct_put_u16(chunk, 28u, (uint16_t)(used + rbct_framed_size(encoded_size)));
  rbct_put_u16(chunk, 36u, (uint16_t)(rbct_get_u16(chunk, 36u) + 1u));
  writer->current_timestamp = midpoint;
  writer->state |= RBCT_STATE_GENERATION_HAS_SYNC;
  writer->state &= (uint8_t)~RBCT_STATE_SYNC_ADVANCED;
  return RBCT_OK;
}

rbct_status_t rbct_writer_finalize(rbct_writer_t* writer) {
  size_t index;
  uint16_t flags = RBCT_FLAG_FINALIZED | RBCT_FLAG_CHUNK_HEADER_CRC;
  uint32_t header_crc;
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
      rbct_put_u32(chunk, 44u, 0u);
      rbct_put_u32(chunk, 44u, rbct_crc32(chunk, RBCT_CHUNK_HEADER_BYTES));
    }
  }
  rbct_sync_header_counts(writer);
  /* Publish completed chunk CRCs before advertising their presence. */
  RBCT_PLATFORM_PUBLISH_BARRIER();
  /* Keep the finalized bit clear until its matching CRC is fully published. */
  rbct_put_u16(writer->buffer, 38u,
               (uint16_t)(flags & (uint16_t)~RBCT_FLAG_FINALIZED));
  rbct_put_u32(writer->buffer, 152u, 0u);
  header_crc = rbct_final_header_crc32(writer->buffer, flags);
  rbct_put_u32(writer->buffer, 152u, header_crc);
  RBCT_PLATFORM_PUBLISH_BARRIER();
  writer->buffer[38] = (uint8_t)(flags & 0xffu);
  writer->state |= RBCT_STATE_FINALIZED;
  return RBCT_OK;
}

const void* rbct_writer_data(const rbct_writer_t* writer) {
  return writer == NULL ? NULL : writer->buffer;
}

size_t rbct_writer_size(const rbct_writer_t* writer) {
  return writer == NULL ? 0u : writer->buffer_bytes;
}
