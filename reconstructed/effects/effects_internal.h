/* Client scalar, vector and matrix helpers shared by the effect sources
 * (effects.c, effects_tree.c). Each names the client routine it mirrors and
 * keeps its binary32 operation order. Internal header. */
#ifndef MU_EFFECTS_INTERNAL_H
#define MU_EFFECTS_INTERNAL_H

#include <math.h>
#include <stdint.h>
#include <string.h>

/* ---- client scalar helpers ---- */

static const float MU_FX_NEAR_EPS = 9.99999997e-7f;   /* 0x01a80990 / -0x01a80994 */

/* 0x00a72592 */
static inline int near_zero(float x) { return MU_FX_NEAR_EPS > x && x > -MU_FX_NEAR_EPS; }
/* 0x00a7edb7 */
static inline int near_equal(float a, float b) { return near_zero(a - b); }

/* CRT wrappers 0x00961a07 (sqrt), 0x009fa223 (cos), 0x009681bd (sin). */
static inline float crt_sqrtf(float x) { return (float)sqrt((double)x); }
static inline float crt_cosf(float x) { return (float)cos((double)x); }
static inline float crt_sinf(float x) { return (float)sin((double)x); }

/* (float) of an unsigned 32-bit value through the client's double path. */
static inline float u32_to_float(uint32_t v) { return (float)(double)v; }

/* ---- vectors (client Vector3 helpers 0x00cfc8f2..0x00cfd2fa) ---- */

static inline void v3_set(float o[3], float x, float y, float z) { o[0] = x; o[1] = y; o[2] = z; }
static inline void v3_copy(float o[3], const float a[3]) { o[0] = a[0]; o[1] = a[1]; o[2] = a[2]; }
static inline void v3_add(float o[3], const float a[3], const float b[3])
{
    float x = a[0] + b[0], y = a[1] + b[1], z = a[2] + b[2];
    o[0] = x; o[1] = y; o[2] = z;
}
static inline void v3_sub(float o[3], const float a[3], const float b[3])
{
    float x = a[0] - b[0], y = a[1] - b[1], z = a[2] - b[2];
    o[0] = x; o[1] = y; o[2] = z;
}
static inline void v3_scale(float o[3], const float a[3], float s)
{
    float x = a[0] * s, y = a[1] * s, z = a[2] * s;
    o[0] = x; o[1] = y; o[2] = z;
}
static inline void v3_cross(float o[3], const float a[3], const float b[3])
{
    float z = a[0] * b[1] - a[1] * b[0];
    float y = a[2] * b[0] - a[0] * b[2];
    float x = a[1] * b[2] - a[2] * b[1];
    o[0] = x; o[1] = y; o[2] = z;
}
/* 0x00cfd03b */
static inline float v3_length_squared(const float a[3])
{
    float s = a[0] * a[0];
    s = s + a[1] * a[1];
    s = s + a[2] * a[2];
    return s;
}
/* 0x00cfd020 */
static inline float v3_length(const float a[3]) { return crt_sqrtf(v3_length_squared(a)); }
/* 0x00cfd21b (dot) */
static inline float v3_dot(const float a[3], const float b[3])
{
    float s = a[0] * b[0];
    s = s + a[1] * b[1];
    s = s + a[2] * b[2];
    return s;
}
/* 0x00cfd15f: normalize in place, near-zero length gives the zero vector. */
static inline void v3_normalize(float v[3])
{
    float length = v3_length(v);
    if (near_zero(length)) {
        v3_set(v, 0.0f, 0.0f, 0.0f);
        return;
    }
    float inverse = 1.0f / length;
    v3_scale(v, v, inverse);
}
/* 0x00cf213d: point through a column-major matrix. */
static inline void m_point(float o[3], const float m[16], const float v[3])
{
    float x = m[0] * v[0];
    x = x + m[4] * v[1];
    x = x + m[8] * v[2];
    float y = m[1] * v[0];
    y = y + m[5] * v[1];
    y = y + m[9] * v[2];
    float z = m[2] * v[0];
    z = z + m[6] * v[1];
    z = z + m[10] * v[2];
    x = x + m[12];
    y = y + m[13];
    z = z + m[14];
    o[0] = x; o[1] = y; o[2] = z;
}
/* 0x00cf22ce: direction through the upper 3x3. */
static inline void m_vector(float o[3], const float m[16], const float v[3])
{
    float x = m[0] * v[0];
    x = x + m[4] * v[1];
    x = x + m[8] * v[2];
    float y = m[1] * v[0];
    y = y + m[5] * v[1];
    y = y + m[9] * v[2];
    float z = m[2] * v[0];
    z = z + m[6] * v[1];
    z = z + m[10] * v[2];
    o[0] = x; o[1] = y; o[2] = z;
}
/* 0x00cfd083 */
static inline int v3_near_zero(const float a[3]) { return near_zero(v3_length_squared(a)); }

/* Entry points shared between the effect sources. */
struct mu_fx_effect;
int mu_fxi_type_update(struct mu_fx_effect *effect, float dt, struct mu_fx_rng *rng,
                       const struct mu_fx_terrain *terrain);

#endif
