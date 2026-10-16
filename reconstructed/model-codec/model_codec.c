#include "model_codec.h"

int32_t mu_bmd12_decode(void *destination, const void *source, int32_t length)
{
    /* Public asset-format constant, already documented in model-recovery/SOURCES.md. */
    static const unsigned char format_key[16] = {
        0xd1, 0x73, 0x52, 0xf6, 0xd2, 0x9a, 0xcb, 0x27,
        0x3e, 0xaf, 0x59, 0x31, 0x37, 0xb3, 0xe7, 0xa2
    };
    unsigned char *output = destination;
    const unsigned char *input = source;
    unsigned int previous = 0x5e;
    if (output != 0) {
        for (int32_t index = 0; index < length; ++index) {
            output[index] = (unsigned char)((input[index] ^ format_key[(uint32_t)index & 15u])-previous);
            previous = ((unsigned int)input[index]+0x3du) & 255u;
        }
    }
    return length;
}
