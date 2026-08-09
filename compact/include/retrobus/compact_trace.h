#ifndef RETROBUS_COMPACT_TRACE_H
#define RETROBUS_COMPACT_TRACE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RBCT_FORMAT_VERSION 4u
#define RBCT_FILE_HEADER_BYTES 192u
#define RBCT_CHUNK_HEADER_BYTES 48u
#define RBCT_CHUNK_BYTES 4096u
#define RBCT_RECORD_COMMIT_BYTES 0u
#define RBCT_RECORD_FRAME_BYTES 0u
#define RBCT_MAX_RECORD_BYTES 70u
#define RBCT_MAX_ARGUMENTS 4u
#define RBCT_CODEC_MAX_CODE_BITS 12u
#define RBCT_CODEC_PROFILE_SMALL_ENTRIES 128u
#define RBCT_CODEC_PROFILE_LARGE_ENTRIES 247u
#define RBCT_DIRECT_EVENT_ID_MAX 251u
#define RBCT_DIRECT_EVENT_OPCODE_MAX 251u

/*
 * When a snapshot can race the writer, compile compact_trace.c with a
 * target-specific RBCT_PLATFORM_PUBLISH_BARRIER() override on architectures
 * without a built-in store barrier. Cache persistence remains platform policy.
 */

typedef enum rbct_status {
  RBCT_OK = 0,
  RBCT_INVALID_ARGUMENT = 1,
  RBCT_INVALID_STATE = 2,
  RBCT_RECORD_TOO_LARGE = 3
} rbct_status_t;

typedef enum rbct_argument_encoding {
  RBCT_ARGUMENT_ULEB128 = 0,
  RBCT_ARGUMENT_FIXED64 = 1
} rbct_argument_encoding_t;

typedef struct rbct_argument {
  uint64_t bits;
  uint8_t encoding;
  uint8_t reserved[7];
} rbct_argument_t;

/*
 * Read-only v4 codec data.  The generated arrays live in ROM; the writer only
 * retains this descriptor pointer.  code_info packs the bit length in bits
 * 12..15 and the LSB-first code in bits 0..11.  entry_limit is 128 or 247.
 */
typedef struct rbct_codec_profile {
  uint8_t sha256[32];
  uint8_t schema_sha256[32];
  uint32_t state_event_ids[2];
  uint16_t entry_limit;
  uint32_t hash_multiplier1;
  uint32_t hash_multiplier2;
  const uint8_t* displacements;
  const uint32_t* keys;
  const uint16_t* code_info;
  uint16_t escape_code_info[3];
} rbct_codec_profile_t;

static inline rbct_argument_t rbct_argument_u64(uint64_t value) {
  rbct_argument_t argument = {
      value, RBCT_ARGUMENT_ULEB128, {0, 0, 0, 0, 0, 0, 0}};
  return argument;
}

static inline rbct_argument_t rbct_argument_i64(int64_t value) {
  const uint64_t encoded = ((uint64_t)value << 1u) ^ (uint64_t)-(value < 0);
  return rbct_argument_u64(encoded);
}

static inline rbct_argument_t rbct_argument_fixed64(uint64_t bits) {
  rbct_argument_t argument = {
      bits, RBCT_ARGUMENT_FIXED64, {0, 0, 0, 0, 0, 0, 0}};
  return argument;
}

typedef struct rbct_config {
  uint64_t clock_rate_numerator;
  uint64_t clock_rate_denominator;
  uint16_t clock_width_bits;
  uint32_t producer_id;
  uint32_t schema_version;
  uint8_t schema_sha256[32];
  uint8_t session_id[16];
  uint32_t initial_clock_generation;
  uint32_t default_track_id;
  const rbct_codec_profile_t* codec_profile;
} rbct_config_t;

typedef struct rbct_scope {
  uint64_t started_at;
  uint32_t event_id;
  uint32_t track_id;
  uint8_t argument_count;
  uint8_t event_opcode;
  uint8_t reserved[6];
  rbct_argument_t arguments[RBCT_MAX_ARGUMENTS];
} rbct_scope_t;

typedef struct rbct_writer {
  uint8_t* buffer;
  size_t buffer_bytes;
  size_t chunk_count;
  size_t current_chunk;
  size_t valid_chunks;
  uint64_t next_sequence;
  uint64_t current_timestamp;
  uint64_t total_records;
  uint64_t overwritten_records;
  uint64_t dropped_records;
  uint64_t total_events;
  uint64_t overwritten_events;
  uint32_t current_generation;
  uint32_t current_track;
  uint32_t default_track;
  uint16_t clock_width_bits;
  uint8_t state;
  const rbct_codec_profile_t* codec_profile;
  rbct_scope_t* scopes;
  size_t scope_capacity;
  size_t scope_depth;
} rbct_writer_t;

size_t rbct_required_buffer_bytes(size_t chunk_count);

rbct_status_t rbct_writer_init(rbct_writer_t* writer,
                               void* buffer,
                               size_t buffer_bytes,
                               rbct_scope_t* scope_storage,
                               size_t scope_capacity,
                               const rbct_config_t* config);

int rbct_writer_enabled(const rbct_writer_t* writer);

rbct_status_t rbct_writer_begin(rbct_writer_t* writer,
                                uint64_t timestamp,
                                uint32_t track_id,
                                uint32_t event_id,
                                const rbct_argument_t* arguments,
                                size_t argument_count);

/*
 * Generic begin/emit use an extended identity in a v4 escape literal.
 * Schema-generated emitters pass their deterministic ordinary identity through
 * these compatibility APIs; profile hits depend only on semantic tuple data.
 */
rbct_status_t rbct_writer_begin_opcode(rbct_writer_t* writer,
                                       uint64_t timestamp,
                                       uint32_t track_id,
                                       uint32_t event_id,
                                       uint8_t event_opcode,
                                       const rbct_argument_t* arguments,
                                       size_t argument_count);

rbct_status_t rbct_writer_end(rbct_writer_t* writer, uint64_t timestamp);

/* Discard the innermost open scope without serializing it. */
rbct_status_t rbct_writer_cancel(rbct_writer_t* writer);

rbct_status_t rbct_writer_emit(rbct_writer_t* writer,
                               uint64_t timestamp,
                               uint32_t track_id,
                               uint32_t event_id,
                               const rbct_argument_t* arguments,
                               size_t argument_count);

rbct_status_t rbct_writer_emit_opcode(rbct_writer_t* writer,
                                      uint64_t timestamp,
                                      uint32_t track_id,
                                      uint32_t event_id,
                                      uint8_t event_opcode,
                                      uint8_t delta_zero_opcode,
                                      uint8_t delta_one_opcode,
                                      const rbct_argument_t* arguments,
                                      size_t argument_count);

rbct_status_t rbct_writer_clock_sync(rbct_writer_t* writer,
                                     uint32_t generation,
                                     uint64_t counter_before,
                                     uint64_t counter_after,
                                     /* Perfetto BOOTTIME nanoseconds. */
                                     uint64_t reference_timestamp_ns,
                                     uint64_t uncertainty_ns);

rbct_status_t rbct_writer_finalize(rbct_writer_t* writer);

const void* rbct_writer_data(const rbct_writer_t* writer);
size_t rbct_writer_size(const rbct_writer_t* writer);

#ifdef __cplusplus
}
#endif

#endif
