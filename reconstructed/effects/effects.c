/* Reconstructed effect simulation and vertex generation. See effects.h and
 * docs/research/client-effects.md. Each function names the client routine it
 * mirrors; statements keep the client's binary32 operation order. */
#include "effects.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

/* ---- client scalar helpers ---- */

static const float NEAR_EPS = 9.99999997e-7f;   /* 0x01a80990 / -0x01a80994 */

/* 0x00a72592 */
static int near_zero(float x) { return NEAR_EPS > x && x > -NEAR_EPS; }
/* 0x00a7edb7 */
static int near_equal(float a, float b) { return near_zero(a - b); }

/* CRT wrappers 0x00961a07 (sqrt), 0x009fa223 (cos), 0x009681bd (sin). */
static float crt_sqrtf(float x) { return (float)sqrt((double)x); }
static float crt_cosf(float x) { return (float)cos((double)x); }
static float crt_sinf(float x) { return (float)sin((double)x); }

/* (float) of an unsigned 32-bit value through the client's double path. */
static float u32_to_float(uint32_t v) { return (float)(double)v; }

/* 0x0191c080: truncation through a 64-bit conversion, low 32 bits kept. */
static int32_t ftol(float x)
{
    double d = (double)x;
    if (!(d > -9.2233720368547758e18 && d < 9.2233720368547758e18))
        return 0;   /* the CRT yields the 64-bit indefinite value, low word 0 */
    return (int32_t)(uint32_t)(uint64_t)(int64_t)d;
}

/* cvttss2si */
static int32_t cvttss2si(float x)
{
    if (!(x > -2147483904.0f && x < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)x;
}

void mu_fx_rng_seed(mu_fx_rng *rng, uint32_t seed)
{
    rng->state = seed;
    rng->calls = 0;
}

/* 0x01989721 (MSVC rand). */
int32_t mu_fx_rand(mu_fx_rng *rng)
{
    rng->state = rng->state * 0x343fdu + 0x269ec3u;
    rng->calls++;
    return (int32_t)((rng->state >> 16) & 0x7fff);
}

/* 0x00a7eb14 */
static float lerp(float a, float b, float t)
{
    if (a == b)
        return a;
    if (near_equal(t, 0.0f))
        return a;
    if (near_equal(t, 1.0f))
        return b;
    float left = (1.0f - t) * a;
    float right = t * b;
    return left + right;
}

/* 0x00a7ebb0 */
float mu_fx_random_range(mu_fx_rng *rng, float lo, float hi)
{
    float t = (float)(mu_fx_rand(rng) % 1001) / 1000.0f;
    return lerp(lo, hi, t);
}

/* 0x00a824b8 */
static int32_t random_int(mu_fx_rng *rng, int32_t lo, int32_t hi)
{
    int32_t d = (int32_t)((uint32_t)hi - (uint32_t)lo);
    if (d >= 0)
        return mu_fx_rand(rng) % (d + 1) + lo;
    return lo - mu_fx_rand(rng) % (-d + 1);
}

/* 0x00a82491: minimum by unsigned comparison. */
static int32_t min_unsigned(int32_t a, int32_t b) { return (uint32_t)a < (uint32_t)b ? a : b; }

/* ---- vectors (client Vector3 helpers 0x00cfc8f2..0x00cfd2fa) ---- */

static void v3_set(float o[3], float x, float y, float z) { o[0] = x; o[1] = y; o[2] = z; }
static void v3_copy(float o[3], const float a[3]) { o[0] = a[0]; o[1] = a[1]; o[2] = a[2]; }
static void v3_add(float o[3], const float a[3], const float b[3])
{
    float x = a[0] + b[0], y = a[1] + b[1], z = a[2] + b[2];
    o[0] = x; o[1] = y; o[2] = z;
}
static void v3_sub(float o[3], const float a[3], const float b[3])
{
    float x = a[0] - b[0], y = a[1] - b[1], z = a[2] - b[2];
    o[0] = x; o[1] = y; o[2] = z;
}
static void v3_scale(float o[3], const float a[3], float s)
{
    float x = a[0] * s, y = a[1] * s, z = a[2] * s;
    o[0] = x; o[1] = y; o[2] = z;
}
static void v3_cross(float o[3], const float a[3], const float b[3])
{
    float z = a[0] * b[1] - a[1] * b[0];
    float y = a[2] * b[0] - a[0] * b[2];
    float x = a[1] * b[2] - a[2] * b[1];
    o[0] = x; o[1] = y; o[2] = z;
}
/* 0x00cfd03b */
static float v3_length_squared(const float a[3])
{
    float s = a[0] * a[0];
    s = s + a[1] * a[1];
    s = s + a[2] * a[2];
    return s;
}
/* 0x00cfd020 */
static float v3_length(const float a[3]) { return crt_sqrtf(v3_length_squared(a)); }
/* 0x00cfd21b (dot) */
static float v3_dot(const float a[3], const float b[3])
{
    float s = a[0] * b[0];
    s = s + a[1] * b[1];
    s = s + a[2] * b[2];
    return s;
}
/* 0x00cfd15f: normalize in place, near-zero length gives the zero vector. */
static void v3_normalize(float v[3])
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
static void m_point(float o[3], const float m[16], const float v[3])
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
static void m_vector(float o[3], const float m[16], const float v[3])
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
static int v3_near_zero(const float a[3]) { return near_zero(v3_length_squared(a)); }

/* ---- matrices ---- */

/* 0x00cef49d: arguments (a, b, c) = (rotation z, rotation y, rotation x). */
void mu_fx_rotation_matrix(float m[16], float a, float b, float c)
{
    float cx = crt_cosf(c), sx = crt_sinf(c);
    float cy = crt_cosf(b), sy = crt_sinf(b);
    float cz = crt_cosf(a), sz = crt_sinf(a);
    m[0] = cy * cz;
    m[4] = -(cy * sz);
    m[8] = sy;
    m[12] = 0.0f;
    float t = sx * sy;
    t = t * cz;
    m[1] = t + cx * sz;
    t = sx * sy;
    t = -(t * sz);
    m[5] = t + cx * cz;
    m[9] = -(sx * cy);
    m[13] = 0.0f;
    t = cx * sy;
    t = -(t * cz);
    m[2] = t + sx * sz;
    t = cx * sy;
    t = t * sz;
    m[6] = t + sx * cz;
    m[10] = cx * cy;
    m[14] = 0.0f;
    m[3] = 0.0f;
    m[7] = 0.0f;
    m[11] = 0.0f;
    m[15] = 1.0f;
}

/* 0x00cee8cd: affine inverse. The client's result record is uninitialised
 * stack (no-op constructor 0x00a7497a): entries 3, 7, 11 and 15 and the whole
 * singular case are undefined there; this port writes identity values for them
 * and returns 0 when singular. */
int mu_fx_affine_inverse(float r[16], const float m[16])
{
    float c0 = m[5] * m[10] - m[6] * m[9];
    float c1 = m[2] * m[9] - m[1] * m[10];
    float c2 = m[1] * m[6] - m[2] * m[5];
    float det = m[0] * c0;
    det = det + m[4] * c1;
    det = det + m[8] * c2;
    float out[16] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
    if (near_zero(det)) {
        memcpy(r, out, sizeof out);
        return 0;
    }
    float inv = 1.0f / det;
    out[0] = inv * c0;
    out[1] = inv * c1;
    out[2] = inv * c2;
    out[4] = (m[6] * m[8] - m[4] * m[10]) * inv;
    out[5] = (m[0] * m[10] - m[2] * m[8]) * inv;
    out[6] = (m[2] * m[4] - m[0] * m[6]) * inv;
    out[8] = (m[4] * m[9] - m[5] * m[8]) * inv;
    out[9] = (m[1] * m[8] - m[0] * m[9]) * inv;
    out[10] = (m[0] * m[5] - m[1] * m[4]) * inv;
    float t = -out[0] * m[12];
    t = t - out[4] * m[13];
    out[12] = t - out[8] * m[14];
    t = -out[1] * m[12];
    t = t - out[5] * m[13];
    out[13] = t - out[9] * m[14];
    t = -out[2] * m[12];
    t = t - out[6] * m[13];
    out[14] = t - out[10] * m[14];
    memcpy(r, out, sizeof out);
    return 1;
}

/* 0x00a76dfe for a node without parent. */
void mu_fx_update_transform(mu_fx_effect *e)
{
    float *m = e->matrix;
    mu_fx_rotation_matrix(m, e->rotation[2], e->rotation[1], e->rotation[0]);
    static const int upper[9] = {0, 4, 8, 1, 5, 9, 2, 6, 10};
    for (int k = 0; k < 9; ++k)
        m[upper[k]] = m[upper[k]] * e->scale;
    m[12] = e->position[0];
    m[13] = e->position[1];
    m[14] = e->position[2];
    e->world_scale = e->scale;
    v3_set(e->world_position, m[12], m[13], m[14]);
}

/* ---- curves and gradients ---- */

int mu_fx_curve_eval(const mu_fx_curve *c, float *out, float t)
{
    uint32_t n = c->count;
    if (n == 0)
        return 0;
    const mu_fx_curve_key *k = c->keys;
    if (n == 1 || !(k[0].time < t)) {
        *out = k[0].value;
        return 1;
    }
    if (!(t < k[n - 1].time)) {
        *out = k[n - 1].value;
        return 1;
    }
    uint32_t i = 1;
    for (; i < n - 1; ++i)
        if (k[i].time > t)
            break;
    float s = (t - k[i - 1].time) / (k[i].time - k[i - 1].time);
    float s2 = s * s;
    float s3 = s2 * s;
    float h00 = 2.0f * s3 - 3.0f * s2;
    h00 = h00 + 1.0f;
    float acc = h00 * k[i - 1].value;
    float h01 = -2.0f * s3 + 3.0f * s2;
    acc = acc + h01 * k[i].value;
    float h10 = s3 - 2.0f * s2;
    h10 = h10 + s;
    acc = acc + h10 * k[i - 1].tangent;
    float h11 = s3 - s2;
    acc = acc + h11 * k[i].tangent;
    *out = acc;
    return 1;
}

int mu_fx_grad1_eval(const mu_fx_grad1 *g, float *out, float t)
{
    uint32_t n = g->count;
    if (n == 0)
        return 0;
    const mu_fx_grad1_key *k = g->keys;
    if (n == 1 || !(k[0].time < t)) {
        *out = k[0].value;
        return 1;
    }
    if (!(t < k[n - 1].time)) {
        *out = k[n - 1].value;
        return 1;
    }
    uint32_t i = 1;
    for (; i < n - 1; ++i)
        if (k[i].time > t)
            break;
    float s = (t - k[i - 1].time) / (k[i].time - k[i - 1].time);
    float a = (1.0f - s) * k[i - 1].value;
    *out = a + s * k[i].value;
    return 1;
}

int mu_fx_grad3_eval(const mu_fx_grad3 *g, float out[3], float t)
{
    uint32_t n = g->count;
    if (n == 0)
        return 0;
    const mu_fx_grad3_key *k = g->keys;
    if (n == 1 || !(k[0].time < t)) {
        v3_copy(out, k[0].rgb);
        return 1;
    }
    if (!(t < k[n - 1].time)) {
        v3_copy(out, k[n - 1].rgb);
        return 1;
    }
    uint32_t i = 1;
    for (; i < n - 1; ++i)
        if (k[i].time > t)
            break;
    float s = (t - k[i - 1].time) / (k[i].time - k[i - 1].time);
    float right[3], left[3];
    v3_scale(right, k[i].rgb, s);
    v3_scale(left, k[i - 1].rgb, 1.0f - s);
    v3_add(out, left, right);
    return 1;
}

/* ---- camera ---- */

/* First part of 0x00a8d821 (frustum planes omitted). */
void mu_fx_camera_set(mu_fx_camera *c, const float position[3], const float forward[3], const float up[3])
{
    v3_copy(c->position, position);
    v3_copy(c->forward, forward);
    v3_copy(c->up, up);
    v3_cross(c->right, c->forward, c->up);
}

/* ---- particle emission ---- */

static float effect_progress(const mu_fx_effect *e)
{
    float q = e->time_left / e->duration;
    return 1.0f - q;
}

static void to_world(const mu_fx_effect *e, mu_fx_particle *p)
{
    if (e->space_is_local)
        return;
    float t[3];
    m_point(t, e->matrix, p->position);
    v3_copy(p->position, t);
    m_vector(t, e->matrix, p->direction);
    v3_copy(p->direction, t);
}

/* 0x00a7dcae */
static void shape_box(const mu_fx_effect *e, const mu_fx_shape *s, mu_fx_particle *p, mu_fx_rng *rng)
{
    if (s->random_direction) {
        p->direction[0] = mu_fx_random_range(rng, -1.0f, 1.0f);
        p->direction[1] = mu_fx_random_range(rng, -1.0f, 1.0f);
        p->direction[2] = mu_fx_random_range(rng, -1.0f, 1.0f);
    } else {
        v3_set(p->direction, 0.0f, 0.0f, 1.0f);
    }
    if (s->emit_from_shell) {
        int32_t face = mu_fx_rand(rng) % 3;
        for (int axis = 0; axis < 3; ++axis) {
            if (axis == face) {
                float v = (mu_fx_rand(rng) % 2) ? -s->size[axis] : s->size[axis];
                p->position[axis] = v / 2.0f;
            } else {
                p->position[axis] = mu_fx_random_range(rng, -s->size[axis], s->size[axis]) / 2.0f;
            }
        }
    } else {
        for (int axis = 0; axis < 3; ++axis)
            p->position[axis] = mu_fx_random_range(rng, -s->size[axis], s->size[axis]) / 2.0f;
    }
    to_world(e, p);
    v3_normalize(p->direction);
}

/* 0x00a7f50b */
static void shape_cone(const mu_fx_effect *e, const mu_fx_shape *s, mu_fx_particle *p, mu_fx_rng *rng)
{
    float h = mu_fx_random_range(rng, 0.0f, 1.0f);
    float z = s->height * h;
    float r1 = s->emit_from_shell ? 1.0f : mu_fx_random_range(rng, 0.0f, 1.0f);
    float a = mu_fx_random_range(rng, 0.0f, 6.28318548f);
    float c = crt_cosf(a), sn = crt_sinf(a);
    float radius = s->height * s->tangent;
    radius = radius * h;
    radius = radius + s->radius;
    radius = radius * r1;
    if (s->cylinder)
        radius = s->radius > radius ? radius : s->radius;
    p->position[0] = radius * c;
    p->position[1] = radius * sn;
    p->position[2] = z;
    if (s->random_direction) {
        p->direction[0] = mu_fx_random_range(rng, -1.0f, 1.0f);
        p->direction[1] = mu_fx_random_range(rng, -1.0f, 1.0f);
        p->direction[2] = mu_fx_random_range(rng, -1.0f, 1.0f);
    } else {
        float d = s->tangent * r1;
        p->direction[0] = d * c;
        d = s->tangent * r1;
        p->direction[1] = d * sn;
        p->direction[2] = 1.0f;
    }
    to_world(e, p);
    v3_normalize(p->direction);
}

/* 0x00a84629 (hemisphere, z in [0,1]) and 0x00a860a7 (sphere). */
static void shape_sphere(const mu_fx_effect *e, const mu_fx_shape *s, mu_fx_particle *p, mu_fx_rng *rng, int hemi)
{
    p->position[0] = mu_fx_random_range(rng, -1.0f, 1.0f);
    p->position[1] = mu_fx_random_range(rng, -1.0f, 1.0f);
    p->position[2] = mu_fx_random_range(rng, hemi ? 0.0f : -1.0f, 1.0f);
    v3_normalize(p->position);
    if (s->random_direction) {
        p->direction[0] = mu_fx_random_range(rng, -1.0f, 1.0f);
        p->direction[1] = mu_fx_random_range(rng, -1.0f, 1.0f);
        p->direction[2] = mu_fx_random_range(rng, -1.0f, 1.0f);
    } else {
        v3_copy(p->direction, p->position);
    }
    float r;
    if (s->emit_from_shell) {
        r = s->radius;
    } else {
        float u = mu_fx_random_range(rng, 0.0f, 1.0f);
        r = u * s->radius;
    }
    v3_scale(p->position, p->position, r);
    to_world(e, p);
    v3_normalize(p->direction);
}

/* 0x00a8503b: world position, random direction in z, y, x evaluation order. */
static void shape_point(const mu_fx_effect *e, mu_fx_particle *p, mu_fx_rng *rng)
{
    if (!e->space_is_local)
        v3_copy(p->position, e->world_position);
    else
        v3_set(p->position, 0.0f, 0.0f, 0.0f);
    float z = mu_fx_random_range(rng, -1.0f, 1.0f);
    float y = mu_fx_random_range(rng, -1.0f, 1.0f);
    float x = mu_fx_random_range(rng, -1.0f, 1.0f);
    v3_set(p->direction, x, y, z);
    v3_normalize(p->direction);
}

static int v4_near_equal(const float a[4], const float b[4])
{
    return near_equal(a[0], b[0]) && near_equal(a[1], b[1]) && near_equal(a[2], b[2]) && near_equal(a[3], b[3]);
}

/* 0x00a86ae1 */
static void start_color(const mu_fx_effect *e, const mu_fx_start_color *s, mu_fx_particle *p, mu_fx_rng *rng)
{
    if (s->color.count == 0 && s->alpha.count == 0) {
        if (v4_near_equal(s->min_color, s->max_color)) {
            memcpy(p->start_color, s->min_color, sizeof p->start_color);
        } else {
            float t = mu_fx_random_range(rng, 0.0f, 1.0f);
            /* 0x00a873a2 */
            if (v4_near_equal(s->min_color, s->max_color) || near_equal(t, 0.0f)) {
                memcpy(p->start_color, s->min_color, sizeof p->start_color);
            } else if (near_equal(t, 1.0f)) {
                memcpy(p->start_color, s->max_color, sizeof p->start_color);
            } else {
                float u = 1.0f - t;
                for (int k = 0; k < 4; ++k) {
                    float right = t * s->max_color[k];
                    float left = u * s->min_color[k];
                    p->start_color[k] = left + right;
                }
            }
        }
    } else {
        float rgb[3] = {1.0f, 1.0f, 1.0f}, alpha = 1.0f;
        float t = effect_progress(e);
        mu_fx_grad3_eval(&s->color, rgb, t);
        mu_fx_grad1_eval(&s->alpha, &alpha, t);
        p->start_color[0] = rgb[0];
        p->start_color[1] = rgb[1];
        p->start_color[2] = rgb[2];
        p->start_color[3] = alpha;
    }
    memcpy(p->color, p->start_color, sizeof p->color);
    if (s->brightness.count == 0) {
        if (near_equal(s->min_brightness, s->max_brightness))
            p->brightness = s->min_brightness;
        else
            p->brightness = lerp(s->min_brightness, s->max_brightness, mu_fx_random_range(rng, 0.0f, 1.0f));
    } else {
        float t = effect_progress(e);
        float b = 1.0f;
        mu_fx_grad1_eval(&s->brightness, &b, t);
        p->brightness = b;
    }
}

/* 0x00a87647 / 0x00a87cad / 0x00a88089: value from the range or the curve. */
static float start_value(const mu_fx_effect *e, const mu_fx_range *r, mu_fx_rng *rng, float current)
{
    if (r->curve.count == 0) {
        if (near_equal(r->min, r->max))
            return r->min;
        return lerp(r->min, r->max, mu_fx_random_range(rng, 0.0f, 1.0f));
    }
    float v = current;
    mu_fx_curve_eval(&r->curve, &v, effect_progress(e));
    return v;
}

static void init_particle(const mu_fx_effect *e, mu_fx_particle *p, mu_fx_rng *rng)
{
    const mu_fx_emitter *m = &e->emitter;
    p->uv0[0] = 0.0f; p->uv0[1] = 0.0f;
    p->uv1[0] = 1.0f; p->uv1[1] = 1.0f;
    v3_set(p->force, 0.0f, 0.0f, 0.0f);
    v3_set(p->velocity, 0.0f, 0.0f, 0.0f);
    p->angular_velocity = 0.0f;
    p->bounce = 1.0f;
    if (m->shape.present) {
        switch (m->shape.shape) {
        case MU_FX_SHAPE_BOX: shape_box(e, &m->shape, p, rng); break;
        case MU_FX_SHAPE_CONE: shape_cone(e, &m->shape, p, rng); break;
        case MU_FX_SHAPE_HEMISPHERE: shape_sphere(e, &m->shape, p, rng, 1); break;
        case MU_FX_SHAPE_POINT: shape_point(e, p, rng); break;
        case MU_FX_SHAPE_SPHERE: shape_sphere(e, &m->shape, p, rng, 0); break;
        default: break;
        }
    }
    if (m->color.present)
        start_color(e, &m->color, p, rng);
    if (m->lifetime.present) {
        p->start_life = start_value(e, &m->lifetime, rng, p->start_life);
        p->life = p->start_life;
    }
    if (m->rotation.present)
        p->angle = near_equal(m->rotation.min, m->rotation.max)
                       ? m->rotation.min
                       : lerp(m->rotation.min, m->rotation.max, mu_fx_random_range(rng, 0.0f, 1.0f));
    if (m->size.present) {
        p->start_size = start_value(e, &m->size, rng, p->start_size);
        if (!e->space_is_local)
            p->start_size = e->world_scale * p->start_size;
        p->size = p->start_size;
    }
    if (m->speed.present) {
        p->start_speed = start_value(e, &m->speed, rng, p->start_speed);
        if (!e->space_is_local)
            p->start_speed = e->world_scale * p->start_speed;
        p->speed = p->start_speed;
    }
}

/* 0x00a8185f */
static int32_t emission_count(const mu_fx_effect *e, float dt, mu_fx_rng *rng)
{
    const mu_fx_emitter *m = &e->emitter;
    if (!e->playing)
        return 0;
    int32_t count;
    if (m->count_curve.count == 0 && e->playing) {
        count = m->min_count == m->max_count ? m->min_count : random_int(rng, m->min_count, m->max_count);
    } else {
        float v = 0.0f;
        mu_fx_curve_eval(&m->count_curve, &v, effect_progress(e));
        count = ftol(v + 0.5f);
    }
    float cf = u32_to_float((uint32_t)count);
    float rate = m->accumulated / 0.0399999991f;
    int32_t scaled = ftol(cf * rate);
    count = min_unsigned(count, scaled);
    for (uint32_t b = 0; b < m->burst_count; ++b) {
        const mu_fx_burst *burst = &m->bursts[b];
        if (burst->count == 0)
            continue;
        if (burst->time > e->duration)
            continue;
        float t = e->duration - e->time_left;
        t = t - burst->time;
        if (0.0f > t)
            t = e->duration + t;
        if (t >= 0.0f && dt > t + NEAR_EPS)
            count = (int32_t)((uint32_t)count + (uint32_t)burst->count);
    }
    int32_t room = (int32_t)(e->capacity - e->count);
    return min_unsigned(count, room);
}

/* 0x00a80752; returns 0 on the rand() % 0 fault. */
static int emitter_update(mu_fx_effect *e, float dt, mu_fx_rng *rng)
{
    mu_fx_emitter *m = &e->emitter;
    m->delay_left = m->delay_left - dt;
    if (m->delay_left > 0.0f)
        return 1;
    uint32_t r = (uint32_t)mu_fx_rand(rng);
    if (m->frequency == 0)
        return 0;
    if (r % m->frequency != 0)
        return 1;
    m->accumulated = m->accumulated + dt;
    int32_t count = emission_count(e, dt, rng);
    if (count == 0)
        return 1;
    uint32_t first = e->count, last = first + (uint32_t)count;
    for (uint32_t i = first; i < last; ++i)
        init_particle(e, &e->particles[i], rng);
    m->accumulated = 0.0f;
    e->count = e->count + (uint32_t)count;
    return 1;
}

/* ---- particle components over lifetime ---- */

static float particle_progress(const mu_fx_particle *p)
{
    float q = p->life / p->start_life;
    return 1.0f - q;
}

/* 0x00a7eeba */
static void color_lifetime(mu_fx_effect *e)
{
    float rgb[3] = {1.0f, 1.0f, 1.0f}, alpha = 1.0f;
    for (uint32_t i = 0; i < e->count; ++i) {
        mu_fx_particle *p = &e->particles[i];
        float t = particle_progress(p);
        if (mu_fx_grad3_eval(&e->color_lifetime.color, rgb, t)) {
            p->color[0] = p->start_color[0] * rgb[0];
            p->color[1] = p->start_color[1] * rgb[1];
            p->color[2] = p->start_color[2] * rgb[2];
        }
        if (mu_fx_grad1_eval(&e->color_lifetime.alpha, &alpha, t))
            p->color[3] = p->start_color[3] * alpha;
    }
}

/* 0x00a83e91 */
static void force_lifetime(mu_fx_effect *e)
{
    const mu_fx_force_lifetime *f = &e->force_lifetime;
    for (uint32_t i = 0; i < e->count; ++i) {
        mu_fx_particle *p = &e->particles[i];
        float t = particle_progress(p);
        for (int k = 0; k < 3; ++k) {
            if (f->curve[k].count == 0)
                p->force[k] = f->constant[k];
            else
                mu_fx_curve_eval(&f->curve[k], &p->force[k], t);
        }
        if (!e->space_is_local)
            v3_scale(p->force, p->force, e->world_scale);
    }
}

/* 0x00a85240 */
static void rotation_lifetime(mu_fx_effect *e, float dt, mu_fx_rng *rng)
{
    const mu_fx_rotation_lifetime *r = &e->rotation_lifetime;
    float w = 0.0f;
    for (uint32_t i = 0; i < e->count; ++i) {
        mu_fx_particle *p = &e->particles[i];
        if (r->curve.count != 0) {
            mu_fx_curve_eval(&r->curve, &w, particle_progress(p));
        } else {
            if (near_equal(p->start_life, p->life))
                p->angular_velocity = mu_fx_random_range(rng, r->min, r->max);
            w = p->angular_velocity;
        }
        float step = w * dt;
        p->angle = step + p->angle;
    }
}

/* 0x00a85819 */
static void size_lifetime(mu_fx_effect *e)
{
    if (e->size_lifetime.curve.count == 0)
        return;
    float s = 0.0f;
    for (uint32_t i = 0; i < e->count; ++i) {
        mu_fx_particle *p = &e->particles[i];
        mu_fx_curve_eval(&e->size_lifetime.curve, &s, particle_progress(p));
        p->size = p->start_size * s;
    }
}

/* 0x00a85c5b */
static void speed_lifetime(mu_fx_effect *e)
{
    float v = 0.0f;
    for (uint32_t i = 0; i < e->count; ++i) {
        mu_fx_particle *p = &e->particles[i];
        if (mu_fx_curve_eval(&e->speed_lifetime.curve, &v, particle_progress(p)))
            p->speed = p->start_speed * v;
    }
}

/* 0x00a8d371; returns 0 on a division by zero tile count. */
static int texcoord_animation(mu_fx_effect *e, mu_fx_rng *rng)
{
    const mu_fx_texcoord_animation *a = &e->texcoord;
    int32_t index = 0;
    for (uint32_t i = 0; i < e->count; ++i) {
        mu_fx_particle *p = &e->particles[i];
        if (a->tiles.count != 0) {
            float v = 0.0f;
            mu_fx_curve_eval(&a->tiles, &v, particle_progress(p));
            index = cvttss2si(v);
        } else {
            if (!near_equal(p->start_life, p->life))
                continue;
            index = a->min_tile == a->max_tile ? a->min_tile : random_int(rng, a->min_tile, a->max_tile);
        }
        if (a->horizontal == 0 || a->vertical == 0)
            return 0;
        float du = 1.0f / u32_to_float(a->horizontal);
        float dv = 1.0f / u32_to_float(a->vertical);
        p->uv0[0] = u32_to_float((uint32_t)index % a->horizontal) * du;
        p->uv0[1] = u32_to_float((uint32_t)index / a->vertical) * dv;
        p->uv1[0] = p->uv0[0] + du;
        p->uv1[1] = p->uv0[1] + dv;
    }
    return 1;
}

/* 0x00a8ce2d */
static void terrain_collider(mu_fx_effect *e, float dt, const mu_fx_terrain *terrain)
{
    if (!terrain || !terrain->height || !terrain->normal)
        return;
    for (uint32_t i = 0; i < e->count; ++i) {
        mu_fx_particle *p = &e->particles[i];
        float position[3], velocity[3], tmp[3];
        v3_copy(position, p->position);
        v3_scale(tmp, p->direction, p->speed);
        v3_add(velocity, tmp, p->force);
        if (e->space_is_local) {
            m_point(tmp, e->matrix, position);
            v3_copy(position, tmp);
            m_vector(tmp, e->matrix, velocity);
            v3_copy(velocity, tmp);
        }
        float h = terrain->height(terrain->context, position[0], position[1]);
        if (!(position[2] + NEAR_EPS >= h))
            continue;
        float below = velocity[2] * dt;
        below = below + position[2];
        below = below - NEAR_EPS;
        if (!(h >= below))
            continue;
        float n[3], reflected[3];
        terrain->normal(terrain->context, position[0], position[1], n);
        float d = v3_dot(n, velocity);
        v3_scale(tmp, n, d * -2.0f);
        v3_add(reflected, tmp, velocity);
        if (e->space_is_local) {
            float inverse[16];
            mu_fx_affine_inverse(inverse, e->matrix);
            m_vector(tmp, inverse, reflected);
            v3_copy(reflected, tmp);
        }
        p->bounce = p->bounce * e->collider.bounding;
        float along[3], unit[3], scaled[3];
        along[0] = p->force[0] / p->speed;
        along[1] = p->force[1] / p->speed;
        along[2] = p->force[2] / p->speed;   /* 0x00cfcbee: per-component division */
        v3_copy(unit, reflected);
        v3_normalize(unit);
        v3_scale(scaled, unit, p->bounce);
        v3_sub(p->direction, scaled, along);
    }
}

/* 0x00a8a273 */
static void particle_loop(mu_fx_effect *e, mu_fx_rng *rng)
{
    if (0.0f < e->time_left)
        return;
    if (e->random_duration) {
        float r = (float)(mu_fx_rand(rng) % 1000);
        float span = e->max_duration - e->min_duration;
        float v = r * span;
        v = v * 0.00100000005f;
        e->time_left = v + e->min_duration;
    } else {
        e->time_left = e->duration;
    }
    if (e->emitter.present)
        e->emitter.delay_left = e->emitter.delay;
}

/* 0x00a88443 */
static void particle_update(mu_fx_effect *e, float dt, mu_fx_rng *rng, const mu_fx_terrain *terrain)
{
    e->time_left = e->time_left - dt;
    if (!e->drawn)
        return;
    if (e->looping)
        particle_loop(e, rng);
    e->drawn = 0;
    for (uint32_t i = 0; i < e->count; ++i) {
        mu_fx_particle *p = &e->particles[i];
        p->life = p->life - dt;
        if (p->life <= 0.0f) {
            e->count--;
            if (i != e->count)
                memcpy(p, &e->particles[e->count], sizeof *p);
        }
    }
    if (e->time_left > 0.0f) {
        if (e->emitter.present && !emitter_update(e, dt, rng)) {
            e->faulted = 1;
            return;
        }
        if (e->color_lifetime.present && e->time_left > 0.0f)
            color_lifetime(e);
        if (e->force_lifetime.present && e->time_left > 0.0f)
            force_lifetime(e);
        if (e->rotation_lifetime.present && e->time_left > 0.0f)
            rotation_lifetime(e, dt, rng);
        if (e->size_lifetime.present && e->time_left > 0.0f)
            size_lifetime(e);
        if (e->speed_lifetime.present && e->time_left > 0.0f)
            speed_lifetime(e);
        if (e->texcoord.present && e->time_left > 0.0f && !texcoord_animation(e, rng)) {
            e->faulted = 1;
            return;
        }
        if (e->collider.present && e->time_left > 0.0f)
            terrain_collider(e, dt, terrain);
    }
    for (uint32_t i = 0; i < e->count; ++i) {
        mu_fx_particle *p = &e->particles[i];
        float tmp[3];
        v3_scale(tmp, p->direction, p->speed);
        v3_add(p->velocity, tmp, p->force);
        v3_scale(tmp, p->velocity, dt);
        v3_add(p->position, p->position, tmp);
    }
}

/* ---- billboard ---- */

/* 0x00a6ea2c */
static int billboard_update(mu_fx_effect *e, float dt, mu_fx_rng *rng)
{
    e->time_left = e->time_left - dt;
    if (!(0.0f < e->time_left)) {
        if (!e->looping || !e->drawn)
            return 1;
        if (e->random_duration) {
            float r = (float)(mu_fx_rand(rng) % 1000);
            float span = e->max_duration - e->min_duration;
            float v = r * span;
            v = v / 1000.0f;
            e->time_left = v + e->min_duration;
        } else {
            e->time_left = e->duration;
        }
    }
    e->drawn = 0;
    float t;
    if (e->bb_color.present && e->time_left > 0.0f) {         /* 0x00a72efd */
        float rgb[3] = {1.0f, 1.0f, 1.0f}, alpha = 1.0f;
        t = effect_progress(e);
        mu_fx_grad3_eval(&e->bb_color.color, rgb, t);
        mu_fx_grad1_eval(&e->bb_color.alpha, &alpha, t);
        e->color[0] = rgb[0] * e->base_color[0];
        e->color[1] = rgb[1] * e->base_color[1];
        e->color[2] = rgb[2] * e->base_color[2];
        e->color[3] = alpha * e->base_color[3];
    }
    if (e->bb_rotation.present && e->time_left > 0.0f) {      /* 0x00a74d2a */
        float w = 0.0f;
        if (e->bb_rotation.curve.count == 0)
            w = e->bb_rotation.constant;
        else
            mu_fx_curve_eval(&e->bb_rotation.curve, &w, effect_progress(e));
        float step = w * dt;
        e->angle = step + e->angle;
    }
    if (e->bb_size.present && e->time_left > 0.0f) {          /* 0x00a74fbc */
        float s = 0.0f;
        if (mu_fx_curve_eval(&e->bb_size.curve, &s, effect_progress(e))) {
            e->width = e->base_width * s;
            e->height = e->base_height * s;
        }
    }
    if (e->bb_texcoord.present && e->time_left > 0.0f) {      /* 0x00a7519f */
        const mu_fx_texcoord_animation *a = &e->bb_texcoord;
        float v = 0.0f;
        mu_fx_curve_eval(&a->tiles, &v, effect_progress(e));
        if (a->horizontal == 0 || a->vertical == 0)
            return 0;
        float du = 1.0f / u32_to_float(a->horizontal);
        float dv = 1.0f / u32_to_float(a->vertical);
        int32_t index = cvttss2si(v);
        float row = u32_to_float((uint32_t)index / a->vertical) * dv;
        float col = u32_to_float((uint32_t)index % a->horizontal) * du;
        e->uv0[0] = col;
        e->uv0[1] = row;
        e->uv1[0] = col + du;
        e->uv1[1] = row + dv;
    }
    if (e->bb_force.present && e->time_left > 0.0f) {         /* 0x00a742bf */
        mu_fx_force_lifetime *f = &e->bb_force;
        float force[3] = {0.0f, 0.0f, 0.0f};
        t = effect_progress(e);
        for (int k = 0; k < 3; ++k) {
            if (f->curve[k].count == 0)
                force[k] = f->constant[k];
            else
                mu_fx_curve_eval(&f->curve[k], &force[k], t);
        }
        if (!v3_near_zero(e->rotation)) {
            float m[16], tmp[3];
            mu_fx_rotation_matrix(m, e->rotation[2], e->rotation[1], e->rotation[0]);
            m_vector(tmp, m, force);
            v3_copy(force, tmp);
        }
        float s = e->scale * dt;
        v3_scale(force, force, s);
        v3_add(f->offset, f->offset, force);
        v3_add(e->position, e->position, force);
    }
    return 1;
}

/* 0x00a6fcfd */
static void billboard_reset(mu_fx_effect *e)
{
    memcpy(e->color, e->base_color, sizeof e->color);
    e->width = e->base_width;
    e->height = e->base_height;
    e->angle = e->base_angle;
    e->uv0[0] = 0.0f; e->uv0[1] = 0.0f;
    e->uv1[0] = 1.0f; e->uv1[1] = 1.0f;
    if (e->bb_force.present) {                                  /* 0x00a747cb */
        v3_sub(e->position, e->position, e->bb_force.offset);
        v3_set(e->bb_force.offset, 0.0f, 0.0f, 0.0f);
    }
}

void mu_fx_restart(mu_fx_effect *e)
{
    e->time_left = e->duration;
    e->faulted = 0;
    if (e->type == MU_FX_PARTICLE_SYSTEM) {
        e->count = 0;                                           /* 0x00a89a4a */
        if (e->emitter.present) {                               /* 0x00a81721 */
            e->emitter.accumulated = 0.0f;
            e->emitter.delay_left = e->emitter.delay;
        }
    } else {
        billboard_reset(e);
    }
}

void mu_fx_update(mu_fx_effect *e, float dt, mu_fx_rng *rng, const mu_fx_terrain *terrain)
{
    if (e->faulted)
        return;
    mu_fx_update_transform(e);
    if (e->type == MU_FX_PARTICLE_SYSTEM)
        particle_update(e, dt, rng, terrain);
    else if (!billboard_update(e, dt, rng))
        e->faulted = 1;
}

/* ---- vertex generation ---- */

static void put_color(mu_fx_vertex *v, const float color[4], float brightness, int additive)
{
    v[0].color[0] = color[0] * brightness;
    v[0].color[1] = color[1] * brightness;
    v[0].color[2] = color[2] * brightness;
    v[0].color[3] = color[3];
    if (additive) {
        float a = v[0].color[3];
        for (int k = 0; k < 4; ++k)
            v[0].color[k] = v[0].color[k] * a;
    }
    for (int j = 1; j < 4; ++j)
        memcpy(v[j].color, v[0].color, sizeof v[0].color);
}

/* 0x00a8a55c */
static void particle_fill(mu_fx_effect *e, const mu_fx_camera *camera, mu_fx_vertex *out)
{
    float axis_a[3] = {0, 0, 0}, axis_b[3] = {0, 0, 0}, eye[3], tmp[3];
    v3_copy(eye, camera->position);
    switch (e->billboarding) {
    case MU_FX_BILLBOARD_EYELINE:
        v3_copy(axis_a, camera->up);
        v3_copy(axis_b, camera->right);
        break;
    case MU_FX_BILLBOARD_VERTICAL:
        v3_set(axis_a, 0.0f, 0.0f, 1.0f);
        v3_copy(axis_b, camera->right);
        break;
    case MU_FX_BILLBOARD_HORIZONTAL:
        v3_set(axis_a, 0.0f, 1.0f, 0.0f);
        v3_set(axis_b, 1.0f, 0.0f, 0.0f);
        break;
    default:
        break;
    }
    if (e->space_is_local) {
        float inverse[16];
        mu_fx_affine_inverse(inverse, e->matrix);
        if (e->billboarding == MU_FX_BILLBOARD_DIRECTIONAL) {
            m_point(tmp, inverse, eye);
            v3_copy(eye, tmp);
        } else {
            m_vector(tmp, inverse, axis_a);
            v3_copy(axis_a, tmp);
            v3_normalize(axis_a);
            m_vector(tmp, inverse, axis_b);
            v3_copy(axis_b, tmp);
            v3_normalize(axis_b);
        }
    }
    const float root2 = crt_sqrtf(2.0f);                       /* static 0x01d1e70c */
    const float quarter = 45.0f * 0.0174532924f;              /* static 0x01d1e714 via 0x00a8c87e */
    for (uint32_t i = 0; i < e->count; ++i) {
        mu_fx_particle *p = &e->particles[i];
        if (e->billboarding == MU_FX_BILLBOARD_DIRECTIONAL) {
            float dir[3], to_eye[3], t1[3], t2[3], c[3], an[3];
            v3_copy(dir, p->velocity);
            v3_normalize(dir);
            v3_sub(to_eye, p->position, eye);
            v3_normalize(to_eye);
            v3_scale(t1, p->velocity, e->speed_scale);
            v3_scale(t2, dir, e->length_scale);
            v3_add(axis_a, t2, t1);
            v3_cross(axis_b, to_eye, dir);
            v3_normalize(axis_b);
            v3_copy(an, axis_a);
            v3_normalize(an);
            v3_cross(c, axis_b, an);
            float d = c[0] * to_eye[0];
            d = d + c[1] * to_eye[1];
            d = d + c[2] * to_eye[2];
            if (d > 0.0f) {
                v3_cross(axis_b, dir, to_eye);
                v3_normalize(axis_b);
            }
        }
        float half_a = p->size * 0.5f, half_b = half_a;
        if (e->billboarding != MU_FX_BILLBOARD_DIRECTIONAL && !near_zero(p->angle)) {
            float c = crt_cosf(p->angle + quarter);
            c = c * root2;
            half_a = c * half_a;
            float s = crt_sinf(p->angle + quarter);
            s = s * root2;
            half_b = s * half_b;
        }
        mu_fx_vertex *v = &out[4 * i];
        float a1[3], b2[3], t[3];
        /* v0 = (p - B*h2) + A*h1 */
        v3_scale(a1, axis_a, half_a);
        v3_scale(b2, axis_b, half_b);
        v3_sub(t, p->position, b2);
        v3_add(v[0].position, t, a1);
        /* v1 = (p - B*h1) - A*h2 */
        v3_scale(a1, axis_a, half_b);
        v3_scale(b2, axis_b, half_a);
        v3_sub(t, p->position, b2);
        v3_sub(v[1].position, t, a1);
        /* v2 = (p + B*h2) - A*h1 */
        v3_scale(a1, axis_a, half_a);
        v3_scale(b2, axis_b, half_b);
        v3_add(t, p->position, b2);
        v3_sub(v[2].position, t, a1);
        /* v3 = (p + B*h1) + A*h2 */
        v3_scale(a1, axis_a, half_b);
        v3_scale(b2, axis_b, half_a);
        v3_add(t, p->position, b2);
        v3_add(v[3].position, t, a1);
        v[0].texcoord[0] = p->uv0[0]; v[0].texcoord[1] = p->uv0[1];
        v[1].texcoord[0] = p->uv0[0]; v[1].texcoord[1] = p->uv1[1];
        v[2].texcoord[0] = p->uv1[0]; v[2].texcoord[1] = p->uv1[1];
        v[3].texcoord[0] = p->uv1[0]; v[3].texcoord[1] = p->uv0[1];
        put_color(v, p->color, p->brightness, e->blending == MU_FX_BLEND_ADDITIVE);
    }
}

/* 0x00a70036 */
static void billboard_fill(const mu_fx_effect *e, const mu_fx_camera *camera, mu_fx_vertex *v)
{
    const float *m = e->matrix;
    float axis_a[3] = {0, 0, 0}, axis_b[3] = {0, 0, 0};
    switch (e->billboarding) {
    case MU_FX_BILLBOARD_EYELINE:
        v3_copy(axis_a, camera->up);
        v3_copy(axis_b, camera->right);
        break;
    case MU_FX_BILLBOARD_VERTICAL:
        v3_set(axis_a, 0.0f, 0.0f, 1.0f);
        v3_copy(axis_b, camera->right);
        break;
    case MU_FX_BILLBOARD_HORIZONTAL:
        v3_set(axis_a, 0.0f, 1.0f, 0.0f);
        v3_set(axis_b, 1.0f, 0.0f, 0.0f);
        break;
    case MU_FX_BILLBOARD_LOCAL_PLANE:
        v3_set(axis_a, m[2], m[6], m[10]);
        v3_set(axis_b, m[0], m[4], m[8]);
        break;
    default:
        break;
    }
    if (e->billboarding == MU_FX_BILLBOARD_DIRECTIONAL) {
        float d[3];
        v3_sub(d, e->position, camera->position);
        v3_normalize(d);
        v3_set(axis_a, m[2], m[6], m[10]);
        v3_normalize(axis_a);
        v3_cross(axis_b, d, axis_a);
        v3_normalize(axis_b);
    }
    v3_normalize(axis_a);
    v3_normalize(axis_b);
    if (e->billboarding != MU_FX_BILLBOARD_DIRECTIONAL && !near_zero(e->angle)) {
        float c = crt_cosf(e->angle), s = crt_sinf(e->angle);
        float t1[3], t2[3], na[3], nb[3];
        v3_scale(t1, axis_a, c);
        v3_scale(t2, axis_b, -s);
        v3_add(na, t2, t1);
        v3_scale(t1, axis_a, s);
        v3_scale(t2, axis_b, c);
        v3_add(nb, t2, t1);
        v3_copy(axis_a, na);
        v3_copy(axis_b, nb);
    }
    float h = e->height * 0.5f;
    h = h * e->world_scale;
    v3_scale(axis_a, axis_a, h);
    float w = e->width * 0.5f;
    w = w * e->world_scale;
    v3_scale(axis_b, axis_b, w);
    float t[3];
    v3_sub(t, e->world_position, axis_b);
    v3_add(v[0].position, t, axis_a);
    v3_sub(t, e->world_position, axis_b);
    v3_sub(v[1].position, t, axis_a);
    v3_add(t, e->world_position, axis_b);
    v3_sub(v[2].position, t, axis_a);
    v3_add(t, e->world_position, axis_b);
    v3_add(v[3].position, t, axis_a);
    v[0].texcoord[0] = e->uv0[0]; v[0].texcoord[1] = e->uv0[1];
    v[1].texcoord[0] = e->uv0[0]; v[1].texcoord[1] = e->uv1[1];
    v[2].texcoord[0] = e->uv1[0]; v[2].texcoord[1] = e->uv1[1];
    v[3].texcoord[0] = e->uv1[0]; v[3].texcoord[1] = e->uv0[1];
    put_color(v, e->color, e->brightness, e->blending == MU_FX_BLEND_ADDITIVE);
}

uint32_t mu_fx_draw(mu_fx_effect *e, const mu_fx_camera *camera, int texture_loaded, mu_fx_vertex *vertices,
                    mu_fx_draw_state *state)
{
    mu_fx_draw_state s;
    memset(&s, 0, sizeof s);
    if (e->type == MU_FX_PARTICLE_SYSTEM) {
        e->drawn = 1;
        s.visible = 1;
        s.texture = texture_loaded ? 1 : 0;
        s.multiply_matrix = e->space_is_local;
        switch (e->blending) {
        case MU_FX_BLEND_ALPHA: s.blend = 1; s.src = 0x302; s.dst = 0x303; break;
        case MU_FX_BLEND_ADDITIVE: s.blend = 1; s.src = 1; s.dst = 1; break;
        case MU_FX_BLEND_MULTIPLY: s.blend = 1; s.src = 0x306; s.dst = 0; break;
        default: break;
        }
        particle_fill(e, camera, vertices);
        s.vertex_count = 4 * e->count;
    } else {
        e->drawn = 1;
        if (!e->playing || 0.0f > e->time_left) {
            if (state)
                *state = s;
            return 0;
        }
        s.visible = 1;   /* an expired or stopped billboard returns before any GL call */
        s.texture = texture_loaded ? 1 : 0;
        s.disable_cull = 1;
        switch (e->blending) {
        case MU_FX_BLEND_ALPHA: s.blend = 1; s.src = 0x302; s.dst = 0x303; break;
        case MU_FX_BLEND_ADDITIVE: s.blend = 1; s.src = 0x300; s.dst = 1; break;
        case MU_FX_BLEND_MULTIPLY: s.blend = 1; s.src = 0x306; s.dst = 0; break;
        default: break;
        }
        billboard_fill(e, camera, vertices);
        s.vertex_count = 4;
    }
    if (state)
        *state = s;
    return s.vertex_count;
}
