/* MIT licensed reconstruction. See LICENSE-analysis and docs/code-recovery.md. */
#include "decoder.h"
#include <limits.h>

typedef struct {
    const uint8_t *source;
    size_t size, position;
    unsigned bits;
    int failed;
} Reader;

static unsigned byte(Reader *r) {
    if (r->position == r->size) { r->failed = 1; return 0; }
    return r->source[r->position++];
}

static unsigned bit(Reader *r) {
    unsigned carry = r->bits >> 7;
    r->bits = (r->bits << 1) & 255;
    if (!r->bits) {
        unsigned next = byte(r);
        r->bits = ((next << 1) | carry) & 255;
        carry = next >> 7;
    }
    return carry;
}

static uint32_t gamma(Reader *r) {
    uint32_t value = 1;
    do {
        if (value > UINT32_MAX / 2) { r->failed = 1; return 0; }
        value = (value << 1) | bit(r);
        if (r->failed) return 0;
    } while (bit(r) && !r->failed);
    return value;
}

static int copy(uint8_t *out, size_t *position, size_t capacity,
                size_t offset, size_t length) {
    if (!offset || offset > *position || length > capacity - *position) return -1;
    while (length--) {
        out[*position] = out[*position - offset];
        ++*position;
    }
    return 0;
}

int mu_decode_block(const uint8_t *source, size_t source_size,
                    uint8_t *output, size_t capacity,
                    size_t *consumed, size_t *written) {
    Reader r = {source, source_size, 0, 0x80, 0};
    size_t position = 0, previous = 0;
    unsigned state = 2;
    if (!source || !output || !consumed || !written) return -1;
    *consumed = *written = 0;
    if (!capacity || !source_size) return -1;
    output[position++] = (uint8_t)byte(&r);
    for (;;) {
        if (!bit(&r)) {
            unsigned value = byte(&r);
            if (r.failed || position == capacity) return -1;
            output[position++] = (uint8_t)value;
            state = 2;
        } else if (!bit(&r)) {
            uint32_t encoded = gamma(&r);
            size_t offset, length;
            if (r.failed || encoded < state) return -1;
            encoded -= state;
            state = 1;
            if (!encoded) {
                offset = previous;
                length = gamma(&r);
            } else {
                if (encoded - 1 > UINT32_MAX / 256) return -1;
                offset = ((size_t)(encoded - 1) << 8) | byte(&r);
                previous = offset;
                length = gamma(&r);
                if (offset >= 0x7d00 || offset < 0x80) length += 2;
                else if (offset >= 0x500) ++length;
            }
            if (r.failed || copy(output, &position, capacity, offset, length)) return -1;
        } else if (!bit(&r)) {
            unsigned encoded = byte(&r);
            size_t offset = encoded >> 1;
            if (r.failed) return -1;
            if (!offset) {
                *consumed = r.position;
                *written = position;
                return 0;
            }
            if (copy(output, &position, capacity, offset, 2 + (encoded & 1))) return -1;
            previous = offset;
            state = 1;
        } else {
            size_t offset = 0;
            for (int i = 0; i < 4; ++i) offset = (offset << 1) | bit(&r);
            if (r.failed || position == capacity || offset > position) return -1;
            output[position] = offset ? output[position - offset] : 0;
            ++position;
            state = 2;
        }
        if (r.failed) return -1;
    }
}
