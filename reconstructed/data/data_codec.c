#include "data_codec.h"

#include <string.h>

const uint8_t mu_data_key3[3] = {0xfc, 0xcf, 0xab};

void mu_data_xor3(uint8_t *buffer, int32_t size, const uint8_t key[3]) {
    if (buffer == NULL || key == NULL) return;
    for (int32_t i = 0; i < size; ++i)
        buffer[i] = (uint8_t)(buffer[i] ^ key[i % 3]);
}

void mu_data_xor3_local(uint8_t *buffer, int32_t size) {
    static const uint8_t local[3] = {0xfc, 0xcf, 0xab};
    mu_data_xor3(buffer, size, local);
}

uint32_t mu_data_checksum(const uint8_t *buffer, uint32_t size, uint32_t key) {
    const uint32_t k = key & 0xffffu;
    uint32_t result = k << 9;
    if (buffer == NULL || size < 4) return result;
    for (uint32_t offset = 0; offset <= size - 4; offset += 4) {
        uint32_t word;
        memcpy(&word, buffer + offset, 4);
#if defined(__BYTE_ORDER__) && __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
        word = __builtin_bswap32(word);
#endif
        if (((offset >> 2) + k) % 2 == 0)
            result ^= word;
        else
            result += word;
        if (offset % 16 == 0)
            result = ((k + result) >> (((offset >> 2) % 8) + 1)) ^ result;
    }
    return result;
}

void mu_data_xor3_key(uint8_t *buffer, uint32_t size, const uint8_t key3[3], uint32_t key) {
    if (buffer == NULL || key3 == NULL) return;
    for (uint32_t i = 0; i < size; ++i) {
        buffer[i] = (uint8_t)(buffer[i] ^ key3[i % 3]);
        buffer[i] = (uint8_t)(buffer[i] ^ (uint8_t)key);
    }
}
