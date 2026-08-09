#ifndef RETROBUS_TEST_CODEC_PROFILE_H
#define RETROBUS_TEST_CODEC_PROFILE_H

#include "retrobus/compact_trace.h"

/* Two Redux-shaped no-argument slice tuples in model state 2. */
static const uint8_t test_codec_displacements[64] = {0};
static uint32_t test_codec_keys[128];
static uint16_t test_codec_codes[128];
static const rbct_codec_profile_t test_codec_profile = {
    {1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0},
    {UINT32_C(100), UINT32_C(101)},
    UINT16_C(128),
    UINT32_C(0x4205a75d),
    UINT32_C(0x2f631b0b),
    test_codec_displacements,
    test_codec_keys,
    test_codec_codes,
    {UINT16_C(0x1000), UINT16_C(0x1000), UINT16_C(0x2003)},
};

static const uint8_t test_large_codec_displacements[128] = {0};
static uint32_t test_large_codec_keys[256];
static uint16_t test_large_codec_codes[256];
static const rbct_codec_profile_t test_large_codec_profile = {
    {2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0},
    {UINT32_C(100), UINT32_C(101)},
    UINT16_C(247),
    UINT32_C(1),
    UINT32_C(1),
    test_large_codec_displacements,
    test_large_codec_keys,
    test_large_codec_codes,
    {UINT16_C(0x1000), UINT16_C(0x1000), UINT16_C(0x1001)},
};

static void test_codec_profiles_initialize(void) {
  test_codec_keys[34] = UINT32_C(0x02000001);
  test_codec_keys[84] = UINT32_C(0x02000101);
  test_codec_codes[34] = UINT16_C(0x2001); /* delta 0: bits 1,0 */
  test_codec_codes[84] = UINT16_C(0x1000); /* delta 1: bit 0 */
  test_large_codec_keys[2] = UINT32_C(0x02000001);
  test_large_codec_codes[2] = UINT16_C(0x1000);
}

#endif
