/* Authored compact reconstruction of the observed LEA key-context layout.
 * Public cipher constants also appear in model-recovery/lea256.c.
 * See docs/research/client-lea-key.md for exact-client evidence and limits.
 */
#include "client_lea.h"
#include <stddef.h>

static uint32_t rotate_left(uint32_t value, unsigned bits) {
    bits &= 31u;
    return (value << bits) | (value >> ((32u-bits) & 31u));
}

static uint32_t load_le(const uint8_t *bytes) {
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static void store_le(uint8_t *bytes, uint32_t value) {
    for (unsigned index = 0; index < 4; ++index)
        bytes[index] = (uint8_t)(value >> (8u*index));
}

void mu_client_lea_setup(void *context, const void *key, int32_t key_bytes) {
    static const uint32_t delta[8] = {
        0xc3efe9db, 0x44626b02, 0x79e27c8a, 0x78df30ec,
        0x715ea49e, 0xc785da0a, 0xe04ef22a, 0xe5c40957
    };
    static const unsigned rotations[6] = {1, 3, 6, 11, 13, 17};
    if (context == NULL || key == NULL ||
        (key_bytes != 16 && key_bytes != 24 && key_bytes != 32))
        return;
    uint8_t *output = context;
    const uint8_t *input = key;
    const unsigned word_count = (unsigned)key_bytes/4u;
    const unsigned rounds = (unsigned)key_bytes/2u+16u;
    uint32_t words[8];
    for (unsigned index = 0; index < word_count; ++index)
        words[index] = load_le(input+4u*index);
    for (unsigned round = 0; round < rounds; ++round) {
        const uint32_t constant = delta[round % word_count];
        if (key_bytes == 16) {
            static const unsigned repeated[6] = {0, 1, 2, 1, 3, 1};
            for (unsigned index = 0; index < 4; ++index)
                words[index] = rotate_left(words[index]+rotate_left(constant, round+index),
                                           rotations[index]);
            for (unsigned index = 0; index < 6; ++index)
                store_le(output+4u*(6u*round+index), words[repeated[index]]);
        } else {
            for (unsigned index = 0; index < 6; ++index) {
                const unsigned position = key_bytes == 24 ? index : (6u*round+index) % 8u;
                words[position] = rotate_left(words[position]+rotate_left(constant, round+index),
                                              rotations[index]);
                store_le(output+4u*(6u*round+index), words[position]);
            }
        }
    }
    store_le(output+768, rounds);
}
