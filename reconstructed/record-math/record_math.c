#include "record_math.h"

#include <fenv.h>
#include <float.h>
#include <math.h>
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

/* Rotation conversion at 0x00d00724. The original reads angle 2, then 1, then
 * 0; each is widened, multiplied by binary64 0.5 and narrowed to binary32. Each
 * float wrapper widens again, calls the client trig helper and stores its x87
 * result as binary32. All products are scalar binary32 (MULSS), left to right.
 */
static float rotation_half(const uint8_t *angles, size_t index)
{
    volatile double scaled = (double)read_value(angles, index) * 0.5;
    return (float)scaled;
}

void mu_rotation_quaternion_using(const void *angles, void *quaternion,
                                  mu_rotation_trig sine, mu_rotation_trig cosine)
{
    const uint8_t *in = angles;
    uint8_t *out = quaternion;
    volatile float s[3], c[3];
    for (size_t step = 0; step < 3; ++step) {
        size_t index = 2 - step;
        float half = rotation_half(in, index);
        s[index] = (float)sine((double)half);
        c[index] = (float)cosine((double)half);
    }
    volatile float left, right;
    left = s[0] * c[1];
    left = left * c[2];
    right = c[0] * s[1];
    right = right * s[2];
    write_value(out, 0, left - right);
    left = c[0] * s[1];
    left = left * c[2];
    right = s[0] * c[1];
    right = right * s[2];
    write_value(out, 1, left + right);
    left = c[0] * c[1];
    left = left * s[2];
    right = s[0] * s[1];
    right = right * c[2];
    write_value(out, 2, left - right);
    left = c[0] * c[1];
    left = left * c[2];
    right = s[0] * s[1];
    right = right * s[2];
    write_value(out, 3, left + right);
}

void mu_rotation_quaternion(const void *angles, void *quaternion)
{
    mu_rotation_quaternion_using(angles, quaternion, sin, cos);
}

/* ------------------------------------------------------------------------
 * Pose-builder helpers. Field reads happen where the original reads them.
 */

static uint32_t read_bits(const uint8_t *record, size_t index)
{
    const uint8_t *p = record + index * 4;
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void write_bits(uint8_t *record, size_t index, uint32_t bits)
{
    uint8_t *p = record + index * 4;
    for (unsigned byte = 0; byte < 4; ++byte)
        p[byte] = (uint8_t)(bits >> (byte * 8));
}

/* XORPS with the 0x80000000 mask: a pure sign-bit flip, also for NaN. */
static float negate(float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    bits ^= 0x80000000u;
    memcpy(&value, &bits, sizeof value);
    return value;
}

int mu_quaternion_compare(const void *a, const void *b)
{
    const uint8_t *left = a, *right = b;
    for (size_t index = 0; index < 4; ++index) {
        volatile float difference = read_value(left, index) - read_value(right, index);
        /* 0x0098a647 -> 0x0098a6d2 -> CRT fabs 0x01983660 (ANDPS mask), then
         * the binary32 FSTP/FLD in the wrapper: an exact magnitude. */
        double magnitude = (double)fabsf(difference);
        if (magnitude > 0.001)
            return 0;
    }
    return 1;
}

/* Client float wrappers widen, call the binary64 helper and store binary32. */
static float trig32(mu_rotation_trig function, float value)
{
    return (float)function((double)value);
}

void mu_quaternion_slerp_using(const void *p, void *q, float t, void *out,
                               mu_rotation_trig arccosine, mu_rotation_trig sine)
{
    const uint8_t *from = p;
    uint8_t *to = q, *result = out;
    volatile float a = 0.0f, b = 0.0f, term;
    for (size_t index = 0; index < 4; ++index) {
        volatile float left = read_value(from, index) - read_value(to, index);
        volatile float right = read_value(from, index) - read_value(to, index);
        term = left * right;
        a = term + a;
        left = read_value(from, index) + read_value(to, index);
        right = read_value(from, index) + read_value(to, index);
        term = left * right;
        b = term + b;
    }
    if (a > b)
        for (size_t index = 0; index < 4; ++index)
            write_bits(to, index, read_bits(to, index) ^ 0x80000000u);

    volatile float cosom = read_value(from, 0) * read_value(to, 0);
    for (size_t index = 1; index < 4; ++index) {
        term = read_value(from, index) * read_value(to, index);
        cosom = cosom + term;
    }
    volatile float scale_p, scale_q;
    if ((double)cosom + 1.0 > 1e-8) {
        if (1.0 - (double)cosom > 1e-8) {
            float omega = trig32(arccosine, cosom);
            float sinom = trig32(sine, omega);
            volatile double angle = (1.0 - (double)t) * (double)omega;
            volatile float numerator = trig32(sine, (float)angle);
            scale_p = numerator / sinom;
            volatile float scaled = t * omega;
            numerator = trig32(sine, scaled);
            scale_q = numerator / sinom;
        } else {
            volatile double complement = 1.0 - (double)t;
            scale_p = (float)complement;
            scale_q = t;
        }
        for (size_t index = 0; index < 4; ++index) {
            volatile float left = scale_p * read_value(from, index);
            volatile float right = scale_q * read_value(to, index);
            write_value(result, index, left + right);
        }
        return;
    }
    write_value(result, 0, negate(read_value(from, 1)));
    write_bits(result, 1, read_bits(from, 0));
    write_value(result, 2, negate(read_value(from, 3)));
    write_bits(result, 3, read_bits(from, 2));
    const double pi = (double)3.14159265358979323846f;
    volatile double angle = (1.0 - (double)t) * 0.5;
    angle = angle * pi;
    scale_p = trig32(sine, (float)angle);
    angle = (double)t * 0.5;
    angle = angle * pi;
    scale_q = trig32(sine, (float)angle);
    for (size_t index = 0; index < 3; ++index) {
        volatile float left = scale_p * read_value(from, index);
        volatile float right = scale_q * read_value(result, index);
        write_value(result, index, left + right);
    }
}

void mu_quaternion_slerp(const void *p, void *q, float t, void *out)
{
    mu_quaternion_slerp_using(p, q, t, out, acos, sin);
}

/* (2*a)*b in binary64 from widened binary32 components. */
static double twice(const uint8_t *q, size_t a, size_t b)
{
    volatile double value = (double)read_value(q, a) * 2.0;
    value = value * (double)read_value(q, b);
    return value;
}

void mu_quaternion_matrix(const void *quaternion, void *matrix)
{
    const uint8_t *q = quaternion;
    uint8_t *m = matrix;
    enum { X = 0, Y = 1, Z = 2, W = 3 };
    volatile double value;
    value = 1.0 - twice(q, Y, Y);
    value = value - twice(q, Z, Z);
    write_value(m, 0, (float)value);
    value = twice(q, X, Y) + twice(q, W, Z);
    write_value(m, 4, (float)value);
    value = twice(q, X, Z) - twice(q, W, Y);
    write_value(m, 8, (float)value);
    value = twice(q, X, Y) - twice(q, W, Z);
    write_value(m, 1, (float)value);
    value = 1.0 - twice(q, X, X);
    value = value - twice(q, Z, Z);
    write_value(m, 5, (float)value);
    value = twice(q, Y, Z) + twice(q, W, X);
    write_value(m, 9, (float)value);
    value = twice(q, X, Z) + twice(q, W, Y);
    write_value(m, 2, (float)value);
    value = twice(q, Y, Z) - twice(q, W, X);
    write_value(m, 6, (float)value);
    value = 1.0 - twice(q, X, X);
    value = value - twice(q, Y, Y);
    write_value(m, 10, (float)value);
}

void mu_angle_matrix_using(const void *angles, void *matrix,
                           mu_rotation_trig sine, mu_rotation_trig cosine)
{
    const uint8_t *in = angles;
    uint8_t *m = matrix;
    const float degrees = 0.017453292f; /* binary32 at 0x01a7fd6c */
    volatile float angle;
    angle = read_value(in, 2) * degrees;
    float sy = trig32(sine, angle), cy = trig32(cosine, angle);
    angle = read_value(in, 1) * degrees;
    float sp = trig32(sine, angle), cp = trig32(cosine, angle);
    angle = read_value(in, 0) * degrees;
    float sr = trig32(sine, angle), cr = trig32(cosine, angle);
    volatile float left, right;
    left = cp * cy;
    write_value(m, 0, left);
    left = cp * sy;
    write_value(m, 4, left);
    write_value(m, 8, negate(sp));
    left = sr * sp;
    left = left * cy;
    right = negate(sy) * cr;
    write_value(m, 1, left + right);
    left = sr * sp;
    left = left * sy;
    right = cr * cy;
    write_value(m, 5, left + right);
    left = sr * cp;
    write_value(m, 9, left);
    left = cr * sp;
    left = left * cy;
    right = negate(sr) * negate(sy);
    write_value(m, 2, left + right);
    left = cr * sp;
    left = left * sy;
    right = negate(sr) * cy;
    write_value(m, 6, left + right);
    left = cr * cp;
    write_value(m, 10, left);
    write_value(m, 3, 0.0f);
    write_value(m, 7, 0.0f);
    write_value(m, 11, 0.0f);
}

void mu_angle_matrix(const void *angles, void *matrix)
{
    mu_angle_matrix_using(angles, matrix, sin, cos);
}

/* Vector helpers 0x00d000ad, 0x00d002b2 and 0x00cfff3c. Every operand is
 * reread from memory at the point the original loads it. */
static void vector_rows(const uint8_t *in, const uint8_t *m, uint8_t *out, int transpose, int translate)
{
    for (size_t r = 0; r < 3; ++r) {
        volatile float value = read_value(in, 0) * read_value(m, transpose ? r : r*4);
        volatile float product = read_value(in, 1) * read_value(m, transpose ? 4+r : r*4+1);
        value = value + product;
        product = read_value(in, 2) * read_value(m, transpose ? 8+r : r*4+2);
        value = value + product;
        if (translate)
            value = value + read_value(m, r*4+3);
        write_value(out, r, value);
    }
}

void mu_vector_rotate(const void *in, const void *matrix, void *out)
{
    vector_rows(in, matrix, out, 0, 0);
}

void mu_vector_transform(const void *in, const void *matrix, void *out)
{
    vector_rows(in, matrix, out, 0, 1);
}

void mu_vector_irotate(const void *in, const void *matrix, void *out)
{
    vector_rows(in, matrix, out, 1, 0);
}
