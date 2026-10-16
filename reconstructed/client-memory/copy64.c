#include "copy64.h"

#include <stddef.h>
#include <stdint.h>
#include <string.h>

void *mu_copy64_forward_words(void *destination, const void *source)
{
    uint8_t *out = destination;
    const uint8_t *in = source;
    for (size_t offset = 0; offset < 64; offset += 4) {
        uint8_t word[4];
        memcpy(word, in + offset, sizeof word);
        memcpy(out + offset, word, sizeof word);
    }
    return destination;
}
