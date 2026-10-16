#include "record_math.h"

#include <fenv.h>
#include <float.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

_Static_assert(sizeof(float) == 4 && sizeof(double) == 8, "Requires binary32/binary64 storage");

int mu_record_math_environment_supported(void)
{
    return FLT_RADIX == 2 && FLT_MANT_DIG == 24 && DBL_MANT_DIG == 53 &&
           FLT_EVAL_METHOD == 0 && fegetround() == FE_TONEAREST;
}

static float read_value(const uint8_t *record, size_t index)
{
    const uint8_t *p = record + index * 4;
    uint32_t bits = (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
                    ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

static void write_value(uint8_t *record, size_t index, float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    uint8_t *p = record + index * 4;
    for (unsigned byte = 0; byte < 4; ++byte)
        p[byte] = (uint8_t)(bits >> (byte * 8));
}

static double product3(const uint8_t *record, size_t a, size_t b, size_t c)
{
    volatile double product = (double)read_value(record, a) * (double)read_value(record, b);
    product = product * (double)read_value(record, c);
    return product;
}

float mu_record_cofactor(const void *source, unsigned row, unsigned column)
{
    static const size_t remaining[4][3] = {{1, 2, 3}, {0, 2, 3}, {0, 1, 3}, {0, 1, 2}};
    const size_t *r = remaining[row], *c = remaining[column];
    const uint8_t *in = source;
    float value = (float)product3(in, r[1]*4+c[1], r[0]*4+c[0], r[2]*4+c[2]);
    value = (float)((double)value + product3(in, r[1]*4+c[0], r[2]*4+c[1], r[0]*4+c[2]));
    value = (float)((double)value + product3(in, r[0]*4+c[1], r[2]*4+c[0], r[1]*4+c[2]));
    value = (float)((double)value - product3(in, r[2]*4+c[1], r[0]*4+c[0], r[1]*4+c[2]));
    value = (float)((double)value - product3(in, r[0]*4+c[1], r[1]*4+c[0], r[2]*4+c[2]));
    value = (float)((double)value - product3(in, r[1]*4+c[1], r[2]*4+c[0], r[0]*4+c[2]));
    return ((row + column) & 1u) ? -value : value;
}

void mu_record_inverse(void *destination, const void *source)
{
    uint8_t *out = destination;
    const uint8_t *in = source;
    float cofactors[16];
    for (unsigned row = 0; row < 4; ++row)
        for (unsigned column = 0; column < 4; ++column)
            cofactors[row*4+column] = mu_record_cofactor(in, row, column);
    float scalar = (float)((double)read_value(in, 0) * (double)cofactors[0] + 0.0);
    for (size_t column = 1; column < 4; ++column)
        scalar = (float)((double)scalar + (double)read_value(in, column) * (double)cofactors[column]);
    if (scalar == 0.0f) {
        for (size_t index = 0; index < 16; ++index)
            write_value(out, index, index % 5 == 0 ? 1.0f : 0.0f);
        for (size_t index = 12; index < 15; ++index)
            write_value(out, index, -read_value(in, index));
        return;
    }
    float reciprocal = (float)(1.0 / (double)scalar);
    for (size_t row = 0; row < 4; ++row)
        for (size_t column = 0; column < 4; ++column)
            write_value(out, column*4+row, (float)((double)cofactors[row*4+column] * (double)reciprocal));
}

/* The actual pose helper stores row-major fields one at a time. Input values
 * must be reread after each output store when any caller spans overlap.
 */
void mu_pose_concat(const void *parent, const void *local, void *destination)
{
    const uint8_t *a = parent, *b = local;
    uint8_t *output = destination;
    for (size_t row = 0; row < 3; ++row) {
        for (size_t column = 0; column < 4; ++column) {
            volatile float value = read_value(a, row*4) * read_value(b, column);
            volatile float product = read_value(a, row*4+1) * read_value(b, 4+column);
            value = value + product;
            product = read_value(a, row*4+2) * read_value(b, 8+column);
            value = value + product;
            if (column == 3)
                value = value + read_value(a, row*4+3);
            write_value(output, row*4+column, value);
        }
    }
}
