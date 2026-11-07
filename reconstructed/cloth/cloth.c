/* RENDER-ITEMS-CLOAK: the client's physics cloth. See cloth.h and docs/research/client-render-items.md part 24.
 * Each function names the routine it follows; the statement order is the client's (binary32, SSE scalar). */
#include "cloth.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "../record-math/record_math.h"

/* CRT wrappers: float widened, double sin / cos / sqrt, rounded to float (0x009681bd, 0x009fa223, 0x00961a07). */
static float crt_sin(float x) { return (float)sin((double)x); }
static float crt_cos(float x) { return (float)cos((double)x); }
static float crt_sqrt(float x) { return (float)sqrt((double)x); }

void mu_cloth_default_globals(mu_cloth_globals *g)
{
    memset(g, 0, sizeof *g);
    g->world = -1;
    g->gravity[0] = 9.8f;
    g->gravity[1] = 0.0025f;
    g->gravity[2] = 400.0f;
    g->rand_seed = 1;
}

static int32_t crt_rand(mu_cloth_globals *g)   /* 0x01989721 */
{
    g->rand_seed = g->rand_seed * 214013u + 2531011u;
    return (int32_t)((g->rand_seed >> 16) & 0x7fff);
}

/* ---- the OBJECT / model services ---- */

static const float *owner_bone(const mu_cloth_host *h, int32_t bone)   /* 0x0129f12c */
{
    if (!h->has_model || !h->bones)
        return NULL;
    if (bone < 0 || bone >= h->bone_count)
        return NULL;
    return h->bones + 12 * bone;
}

/* TransformPosition 0x012b6ef1 with translate 1: (M v + T) * BodyScale + BodyOrigin, component by component. */
static void transform_position(const mu_cloth_host *h, const float *matrix, const float in[3], float out[3])
{
    float t[3];
    mu_vector_transform(in, matrix, t);
    for (int k = 0; k < 3; ++k)
        t[k] = h->body_scale * t[k];
    for (int k = 0; k < 3; ++k)
        out[k] = t[k] + h->body_origin[k];
}

/* ---- CPhysicsVertex ---- */

static void vertex_reset(mu_cloth_vertex *v)   /* 0x00fd5916 */
{
    v->count = 0;
    for (int k = 0; k < 3; ++k) {
        v->delta[k] = 0.0f;
        v->position[k] = 0.0f;
        v->velocity[k] = 0.0f;
        v->force[k] = 0.0f;
    }
    v->flags = 0;
}

static void vertex_set(mu_cloth_vertex *v, float x, float y, float z, int fixed)   /* 0x00fd5985 */
{
    v->position[0] = x;
    v->position[1] = y;
    v->position[2] = z;
    if (fixed)
        v->flags |= 1;
}

static float vertex_distance(const mu_cloth_vertex *a, const mu_cloth_vertex *b, float diff[3])   /* 0x00fd5fb5 */
{
    for (int k = 0; k < 3; ++k)
        diff[k] = a->position[k] - b->position[k];
    float dot = diff[0] * diff[0];
    dot = dot + diff[1] * diff[1];
    dot = dot + diff[2] * diff[2];
    return crt_sqrt(dot);
}

/* The clamped distance of the spring passes: the distance, or 0.001 below it (the client calls 0x00fd5fb5 twice). */
static float clamped_distance(const mu_cloth_vertex *a, const mu_cloth_vertex *b, float diff[3])
{
    float d = vertex_distance(a, b, diff);
    if (0.001f > d)
        return 0.001f;
    return vertex_distance(a, b, diff);
}

static void vertex_add_force(mu_cloth_vertex *v, float x, float y, float z)   /* 0x00fd5ea3 */
{
    v->force[0] = v->force[0] + x;
    v->force[1] = v->force[1] + y;
    v->force[2] = v->force[2] + z;
}

/* InitForce 0x00fd59e8(distance, type, wind, angles, push0, push1). */
static void vertex_init_force(mu_cloth_vertex *v, const mu_cloth_globals *g, int32_t distance, uint32_t type,
                              float wind, const float angles[3], float push0, float push1)
{
    if (v->flags & 1) {
        v->force[2] = 0.0f;
        v->force[1] = 0.0f;
        v->force[0] = 0.0f;
        return;
    }
    const float c = 1.0f;
    const int32_t n = 5 - distance;
    const int32_t k4 = (uint32_t)n < 4u ? n : 4;   /* the client's unsigned compare: far vertices take 4 */
    const int32_t weight = k4 == 0 ? 0 : k4 + 2;
    const float w = (float)weight;
    for (int k = 0; k < 3; ++k) {
        const float a = w * g->wind_vector[k];
        const float b = v->velocity[k] * 0.01f;
        v->force[k] = a - b;
    }
    switch (type & 0x300) {
    case 0x100: {
        float t = wind + 0.1f;
        t = t * w;
        t = t * 1.0f;
        v->force[2] = t + v->force[2];
        break;
    }
    case 0x200:
        v->force[2] = w * wind + v->force[2];
        break;
    default:
        break;
    }
    switch (type & 0xfc000) {
    case 0x4000: {
        float t = w * wind;
        t = t * 0.5f;
        v->force[0] = -t + v->force[0];
        float s = wind + 0.1f;
        s = s * w;
        s = s * 0.5f;
        const float wave = crt_sin(g->time * 0.003f);
        float z = s * wave;
        z = z * 5.0f;
        v->force[2] = z + v->force[2];
        float grav = g->gravity[0] * c;
        grav = grav * g->gravity[1];
        grav = grav * 50.0f;
        v->force[2] = v->force[2] - grav;
        break;
    }
    case 0x8000: {
        float t = w * wind;
        t = t * 0.8f;
        v->force[0] = -t + v->force[0];
        break;
    }
    case 0x10000: {
        float t = w * wind;
        t = t * 0.8f;
        v->force[0] = v->force[0] - -t;
        break;
    }
    default:
        break;
    }
    const float calm = 0.0f > wind ? 0.0f : wind;
    float local[3];
    float x = w * calm;
    x = x * push1;
    local[0] = x + push0;
    local[1] = 0.0f;
    local[2] = 0.0f;
    float m[12], r[3];
    mu_angle_matrix(angles, m);
    mu_vector_rotate(local, m, r);
    for (int k = 0; k < 3; ++k)
        v->force[k] = v->force[k] + r[k];
    float grav = g->gravity[0] * c;
    grav = grav * g->gravity[1];
    grav = grav * ((type & 0xc00) == 0x400 ? 180.0f : 100.0f);
    v->force[2] = v->force[2] - grav;
}

static void vertex_move(mu_cloth_vertex *v, const mu_cloth_globals *g, float time)   /* 0x00fd5f15 */
{
    if (v->flags & 1)
        return;
    for (int k = 0; k < 3; ++k) {
        float a = v->force[k] * g->gravity[2];
        a = a * time;
        v->velocity[k] = a + v->velocity[k];
        v->position[k] = v->velocity[k] * time + v->position[k];
    }
}

/* 0x00fd63be(other, length): moves both ends half of the error each. */
static void vertex_constrain(mu_cloth_vertex *a, mu_cloth_vertex *b, float length)
{
    float diff[3];
    const float d = clamped_distance(a, b, diff);
    for (int k = 0; k < 3; ++k) {
        float f = d - length;
        f = f * 0.5f;
        f = f / d;
        diff[k] = f * diff[k];
    }
    for (int k = 0; k < 3; ++k)
        a->delta[k] = a->delta[k] - diff[k];
    for (int k = 0; k < 3; ++k)
        b->delta[k] = b->delta[k] + diff[k];
    a->count++;
    b->count++;
}

static void vertex_apply(mu_cloth_vertex *v)   /* 0x00fd65b1 */
{
    if (v->flags & 1) {
        v->delta[2] = 0.0f;
        v->delta[1] = 0.0f;
        v->delta[0] = 0.0f;
        return;
    }
    if (v->count <= 0)
        return;
    for (int k = 0; k < 3; ++k)
        v->delta[k] = v->delta[k] / (float)v->count;
    for (int k = 0; k < 3; ++k)
        v->position[k] = v->position[k] + v->delta[k];
    v->delta[2] = 0.0f;
    v->delta[1] = 0.0f;
    v->delta[0] = 0.0f;
    v->count = 0;
}

static void vertex_add_delta(mu_cloth_vertex *v, const float d[3])   /* 0x00fd6734 */
{
    for (int k = 0; k < 3; ++k)
        v->delta[k] = v->delta[k] + d[k];
    v->count++;
}

/* 0x00fd606f(other, &spring.min_length), this = the spring's second vertex. 0 stops the constraint pass. */
static int vertex_stretch(mu_cloth_vertex *v, const mu_cloth_vertex *o, const mu_cloth_spring *s,
                          const mu_cloth_globals *g)
{
    if (v->flags & 1)
        return 1;
    float diff[3];
    const float d = clamped_distance(v, o, diff);
    if (d > s->length * 20.0f && !g->stretch_hold)
        return 0;
    if (d > s->length) {
        for (int k = 0; k < 3; ++k) {
            float f = d - s->length;
            f = f / d;
            diff[k] = f * diff[k];
        }
    } else if (s->min_length > d) {
        for (int k = 0; k < 3; ++k) {
            float f = d - s->min_length;
            f = f / d;
            diff[k] = f * diff[k];
        }
    } else {
        return 1;
    }
    for (int k = 0; k < 3; ++k)
        v->position[k] = v->position[k] - diff[k];
    return 1;
}

/* Collision sphere 0x00fd69e8(vertex). */
static void sphere_collide(const mu_cloth_sphere *s, mu_cloth_vertex *v)
{
    float d[3];
    for (int k = 0; k < 3; ++k)
        d[k] = v->position[k] - s->center[k];
    float dot = d[0] * d[0];
    dot = dot + d[1] * d[1];
    dot = dot + d[2] * d[2];
    float length = crt_sqrt(dot);
    if (0.01f > length) {
        length = 0.01f;
        d[0] = length;
        d[1] = 0.0f;
        d[2] = 0.0f;
    }
    if (!(s->radius > length))
        return;
    for (int k = 0; k < 3; ++k) {
        float f = s->radius - length;
        f = f / length;
        d[k] = f * d[k];
    }
    vertex_add_delta(v, d);
}

/* ---- CPhysicsCloth ---- */

void mu_cloth_init(mu_cloth *c)   /* 0x00fd6c22 -> 0x00fd6ca4 */
{
    memset(c, 0, sizeof *c);
    c->owner = 0;
    c->bone = 0;
    c->texture_back = 0;
    c->texture_front = 0;
    c->type = 0;
    c->origin[2] = 0.0f;
    c->origin[1] = 0.0f;
    c->origin[0] = 0.0f;
    c->height = 1.0f;
    c->width = 1.0f;
    c->step[1] = 1.0f;
    c->step[0] = 1.0f;
    c->columns = c->rows = c->vertex_count = 0;
    c->spring_count = 0;
    c->wind_range = 1;
    c->wind_base = 1;
    c->push[0] = 0.0f;
    c->push[1] = 0.0f;
    c->uv_scale[0] = 1.0f;
    c->uv_scale[1] = 1.0f;
    c->uv_offset[0] = 0.0f;
    c->uv_offset[1] = 0.0f;
    c->custom = 0;
    c->glow_texture = -1;
    c->mesh = -1;
    c->sphere_count = 0;
}

static void set_spring(mu_cloth *c, int32_t index, int32_t v0, int32_t v1, float min_length, float length,
                       uint8_t flags)   /* 0x00fd8192 */
{
    mu_cloth_spring *s = &c->springs[index];
    s->v0 = (int16_t)v0;
    s->v1 = (int16_t)v1;
    s->min_length = min_length;
    s->length = length;
    s->flags = flags;
}

/* SetFixed (virtual slot 4, 0x00fd79bb): the top row hangs from the matrix. */
static void set_fixed(mu_cloth *c, const mu_cloth_host *h, const float *matrix)
{
    int curve = 0;
    for (int32_t x = 0; x < c->columns; ++x) {
        float width = c->width;
        float step = c->step[0];
        switch (c->type & 0xc) {
        case 4:
            width = width * 0.6f;
            step = width / (float)(c->columns - 1);
            break;
        case 8:
            curve = 1;
            break;
        default:
            break;
        }
        float p[3];
        const float a = (float)x * step;
        const float b = 0.5f * width;
        p[0] = a - b;
        p[1] = 10.0f;
        p[2] = 0.0f;
        p[0] = p[0] + c->origin[0];
        if (curve) {
            const float s = crt_sin((float)x / (float)(c->columns - 1) * 3.14f);
            const float t = s * 130.0f;
            p[1] = t - 110.0f;
        } else {
            p[1] = c->origin[1];
        }
        p[2] = c->origin[2];
        if ((c->type & 0x30) == 0x10) {
            p[0] = p[0] + 5.0f;
            p[1] = p[1] + 10.0f;
        }
        if ((c->type & 3) == 1) {
            const float e = fabsf((float)x / (float)(c->columns - 1) - 0.5f);
            const float f = e * 2.0f;
            float drop = 10.0f * f;
            drop = drop * f;
            p[1] = p[1] - drop;
        }
        const float q[3] = {p[0], p[1], p[2]};
        p[0] = q[2];
        p[1] = -q[1];
        p[2] = q[0];
        if (!h->has_model)
            return;
        float out[3];
        transform_position(h, matrix, p, out);
        vertex_set(&c->vertices[x], out[0], out[1], out[2], 1);
    }
}

int mu_cloth_create(mu_cloth *c, const mu_cloth_host *h, int32_t bone, float x, float y, float z, int32_t columns,
                    int32_t rows, float width, float height, int32_t texture_front, int32_t texture_back,
                    uint32_t type)
{
    if (columns < 2 || rows < 2 || columns * rows > MU_CLOTH_MAX_VERTICES ||
        ((columns - 1) * rows + (rows - 1) * columns) * 2 > MU_CLOTH_MAX_SPRINGS)
        return MU_CLOTH_UNSUPPORTED;
    c->owner = 1;
    c->bone = bone;
    c->texture_front = texture_front;
    c->texture_back = texture_back;
    c->type |= type;
    c->origin[0] = x;
    c->origin[1] = y;
    c->origin[2] = z;
    c->alpha = 1.0f;
    c->alpha_from_object = 1;
    c->custom = 0;
    c->width = width;
    c->height = height;
    c->columns = columns;
    c->rows = rows;
    c->vertex_count = columns * rows;
    for (int32_t i = 0; i < c->vertex_count; ++i)
        vertex_reset(&c->vertices[i]);
    c->spring_count = ((columns - 1) * rows + (rows - 1) * columns) * 2;
    memset(c->springs, 0, sizeof c->springs);   /* operator new without a constructor: our arrays start clear */
    c->step[0] = c->width / (float)(c->columns - 1);
    c->step[1] = c->height / (float)(c->rows - 1);
    int32_t n = 0;
    float m[12];
    mu_angle_matrix(h->angles, m);
    if (h->bones)
        for (int r = 0; r < 3; ++r) {
            const float *b = owner_bone(h, c->bone);
            if (!b)
                return MU_CLOTH_FAILED;
            m[4 * r + 3] = b[4 * r + 3];
        }
    int curve = 0;
    for (int32_t yy = 0; yy < c->rows; ++yy) {
        float w = c->width;
        float sx = c->step[0];
        const float sy = c->step[1];
        switch (c->type & 0xc) {
        case 4: {
            float t = (float)yy * 0x1.999998p-2f;   /* 0x01ab27e0 = 0x3ecccccc */
            t = t / (float)(c->rows - 1);
            t = t + 0.6f;
            w = t * w;
            sx = w / (float)(c->columns - 1);
            break;
        }
        case 8:
            curve = 1;
            break;
        default:
            break;
        }
        for (int32_t xx = 0; xx < c->columns; ++xx) {
            const int32_t index = c->columns * yy + xx;
            float p[3];
            if (curve) {
                const float s = crt_sin((float)xx / (float)(c->columns - 1) * 3.14f);
                const float t = s * 100.0f;
                p[0] = (float)xx * sx;
                p[1] = t - 30.0f;
                p[2] = (float)yy * sy;
            } else {
                const float a = (float)xx * sx;
                const float b = 0.5f * w;
                p[0] = a - b;
                p[1] = 20.0f;
                p[2] = -sy * (float)yy;
            }
            switch (c->type & 3) {
            case 1: {
                const float e = fabsf((float)xx / (float)(c->columns - 1) - 0.5f);
                const float f = e * 2.0f;
                float drop = 10.0f * f;
                drop = drop * f;
                p[1] = p[1] - drop;
                break;
            }
            case 2:
                p[1] = 0.0f;
                break;
            default:
                break;
            }
            float out[3];
            if (h->bones) {
                if (!h->has_model)
                    return MU_CLOTH_FAILED;
                transform_position(h, m, p, out);
            } else {
                out[0] = p[0];
                out[1] = p[1];
                out[2] = p[2];
            }
            vertex_set(&c->vertices[index], out[0], out[1], out[2], 0);
        }
    }
    uint8_t vertical = 0, diagonal = 0;
    if ((c->type & 0x300) != 0x100) {
        vertical |= 4;
        diagonal |= 1;
    }
    for (int32_t yy = 0; yy < c->rows; ++yy)
        for (int32_t xx = 0; xx < c->columns; ++xx) {
            const int32_t i = c->columns * yy + xx;
            float diff[3], d;
            if (yy < c->rows - 1) {
                d = vertex_distance(&c->vertices[i], &c->vertices[i + c->columns], diff);
                set_spring(c, n++, i, i + c->columns, d * 0.8f, d, (uint8_t)(vertical | 2));
            }
            if (xx < c->columns - 1) {
                d = vertex_distance(&c->vertices[i], &c->vertices[i + 1], diff);
                set_spring(c, n++, i, i + 1, d * 0.8f, d, 3);
                if (yy < c->rows - 1) {
                    d = vertex_distance(&c->vertices[i], &c->vertices[i + c->columns + 1], diff);
                    set_spring(c, n++, i, i + c->columns + 1, d * 0.8f, d, diagonal);
                }
                if (yy > 1) {
                    d = vertex_distance(&c->vertices[i], &c->vertices[i + 1 - c->columns], diff);
                    set_spring(c, n++, i, i + 1 - c->columns, d * 0.8f, d, diagonal);
                }
            }
        }
    c->spring_count = n;
    set_fixed(c, h, m);
    return MU_CLOTH_OK;
}

int mu_cloth_add_sphere(mu_cloth *c, float x, float y, float z, float radius, int32_t bone)
{
    if (c->sphere_count >= MU_CLOTH_MAX_SPHERES)
        return MU_CLOTH_UNSUPPORTED;
    mu_cloth_sphere *s = &c->spheres[c->sphere_count++];
    memset(s, 0, sizeof *s);
    s->offset[0] = x;
    s->offset[1] = y;
    s->offset[2] = z;
    s->radius = radius;
    s->bone = bone;
    return MU_CLOTH_OK;
}

/* InitForces (virtual slot 7, 0x00fd8463). */
static void init_forces(mu_cloth *c, const mu_cloth_host *h, const mu_cloth_globals *g)
{
    float angles[3] = {0.0f, 0.0f, 0.0f};
    if (c->owner) {
        angles[0] = h->angles[0];
        angles[1] = h->angles[1];
        angles[2] = h->angles[2];
    }
    const int32_t q = g->logic_steps / 10;
    const int32_t t = (int32_t)((uint32_t)q * 101u) % c->vertex_count;
    for (int32_t i = 0; i < c->vertex_count; ++i) {
        const int32_t a = abs(t % c->columns - i % c->columns);
        const int32_t b = abs(t / c->columns - i / c->columns);
        vertex_init_force(&c->vertices[i], g, a + b, c->type, c->wind, angles, c->push[0], c->push[1]);
    }
}

/* 0x00fd85f0(time): forces, the force springs, the top row, then the vertices' steps. */
static void integrate(mu_cloth *c, const mu_cloth_host *h, const mu_cloth_globals *g, float time)
{
    init_forces(c, h, g);
    for (int32_t i = 0; i < c->spring_count; ++i) {
        const mu_cloth_spring *s = &c->springs[i];
        if (!(s->flags & 2))
            continue;
        mu_cloth_vertex *a = &c->vertices[s->v0], *b = &c->vertices[s->v1];
        float diff[3];
        const float d = clamped_distance(a, b, diff);
        if (!(d > s->length + 0.01f))
            continue;
        float f[3];
        for (int k = 0; k < 3; ++k) {
            float e = d - s->length;
            e = e * diff[k];
            f[k] = e / d;
            if (c->type & 0x20000000) {
                const float l = s->length / 32.0f;
                f[k] = l * f[k];
            }
            if ((c->type & 0x300) == 0x100)
                f[k] = f[k] * 3.0f;
            switch (c->type & 0xfc000) {
            case 0x4000:
                f[k] = f[k] * 2.0f;
                break;
            case 0x8000:
            case 0x10000:
                f[k] = f[k] * 1.0f;
                break;
            default:
                break;
            }
        }
        vertex_add_force(a, -f[0], -f[1], -f[2]);
        vertex_add_force(b, f[0], f[1], f[2]);
    }
    const float *bone = owner_bone(h, c->bone);
    if (!bone)
        return;
    set_fixed(c, h, bone);
    for (int32_t i = 0; i < c->vertex_count; ++i)
        vertex_move(&c->vertices[i], g, time);
}

/* 0x00fd88ec: sphere centres, collisions, constrain springs, apply, stretch limits. The client ignores its result. */
static int constrain(mu_cloth *c, const mu_cloth_host *h, const mu_cloth_globals *g)
{
    for (int32_t j = 0; j < c->sphere_count; ++j) {
        mu_cloth_sphere *s = &c->spheres[j];
        const float local[3] = {s->offset[2], -s->offset[1], s->offset[0]};
        if (!h->has_model)
            return 0;
        const float *bone = owner_bone(h, s->bone);
        if (!bone)
            return 0;
        float out[3];
        transform_position(h, bone, local, out);
        s->center[0] = out[0];
        s->center[1] = out[1];
        s->center[2] = out[2];
    }
    if (c->sphere_count > 0) {   /* 0x00fd9e98 */
        for (int32_t j = 0; j < c->sphere_count; ++j)
            for (int32_t i = 0; i < c->vertex_count; ++i)
                sphere_collide(&c->spheres[j], &c->vertices[i]);
        for (int32_t i = 0; i < c->vertex_count; ++i)
            vertex_apply(&c->vertices[i]);
    }
    for (int32_t i = 0; i < c->spring_count; ++i) {
        const mu_cloth_spring *s = &c->springs[i];
        if (s->flags & 1)
            vertex_constrain(&c->vertices[s->v0], &c->vertices[s->v1], s->length);
    }
    for (int32_t yy = 0; yy < c->rows; ++yy)
        for (int32_t xx = 0; xx < c->columns; ++xx)
            vertex_apply(&c->vertices[c->columns * yy + xx]);
    for (int32_t i = 0; i < c->spring_count; ++i) {
        const mu_cloth_spring *s = &c->springs[i];
        if (s->v1 >= c->columns && (s->flags & 4))
            if (!vertex_stretch(&c->vertices[s->v1], &c->vertices[s->v0], s, g))
                return 0;
    }
    return 1;
}

static int move(mu_cloth *c, const mu_cloth_host *h, mu_cloth_globals *g, float time)   /* 0x00fd825f */
{
    if ((c->type & 0x300) == 0x200) {
        const int32_t r = crt_rand(g) % (int32_t)c->wind_range;
        c->wind = (float)(r + c->wind_base) / 100.0f;
    } else if (g->world == 0x37) {
        const int32_t r = crt_rand(g) % 40;
        c->wind = (float)(r + 10) / 50.0f;
    } else {
        c->wind = g->wind;
    }
    if ((c->type & 0xc) == 8) {
        const int32_t r = crt_rand(g) % 10;
        c->wind = (float)(r + 25) / 50.0f;
    }
    if ((c->type & 0xfc000) == 0x20000)
        c->wind = g->wind / 2.0f;
    if (!c->owner)
        return 0;
    float a = 180.0f + h->angles[2];
    a = a * 0x1.921fb6p+1f;   /* 0x01a7df2c: binary32 pi */
    a = a / 180.0f;
    const float s = crt_sin(a);
    g->wind_vector[0] = s * c->wind;
    const float nw = -c->wind;
    const float co = crt_cos(a);
    g->wind_vector[1] = nw * co;
    integrate(c, h, g, time);
    constrain(c, h, g);
    return 1;
}

int mu_cloth_move2(mu_cloth *c, const mu_cloth_host *h, mu_cloth_globals *g, float time, int32_t count)
{
    for (int32_t i = 0; i < count; ++i)
        if (!move(c, h, g, time))
            return 0;
    return 1;
}

/* RenderVertex 0x00fd90f5(points, x, y). */
static void render_vertex(const mu_cloth *c, const mu_cloth_sink *sink, int32_t x, int32_t y)
{
    const mu_cloth_vertex *v = &c->vertices[c->columns * y + x];
    const float su = 1.0f / c->uv_scale[0];
    const float sv = 1.0f / c->uv_scale[1];
    float u = (float)x / (float)(c->columns - 1);
    u = u * su;
    u = u - c->uv_offset[0];
    float t = (float)y / (float)(c->rows - 1);
    t = t * sv;
    t = t - c->uv_offset[1];
    const float tt = t > 0.99f ? 0.99f : t;
    sink->texcoord(sink->context, u, tt);
    sink->vertex(sink->context, v->position[0], v->position[1], v->position[2]);
}

/* RenderFace 0x00fd8fba(front, bitmap, points): GL_QUADS over the grid, the back face wound the other way. */
static void render_face(const mu_cloth *c, const mu_cloth_sink *sink, int front, int32_t bitmap)
{
    sink->bind(sink->context, bitmap);
    sink->begin(sink->context, 7);
    for (int32_t y = 0; y < c->rows - 1; ++y)
        for (int32_t x = 0; x < c->columns - 1; ++x)
            if (front) {
                render_vertex(c, sink, x, y);
                render_vertex(c, sink, x + 1, y);
                render_vertex(c, sink, x + 1, y + 1);
                render_vertex(c, sink, x, y + 1);
            } else {
                render_vertex(c, sink, x, y);
                render_vertex(c, sink, x, y + 1);
                render_vertex(c, sink, x + 1, y + 1);
                render_vertex(c, sink, x + 1, y);
            }
    sink->end(sink->context);
}

int mu_cloth_render(mu_cloth *c, const mu_cloth_host *h, const float *light, const mu_cloth_sink *sink)
{
    if ((c->type & 0x40000000) || c->glow_texture != -1 || c->mesh != -1)
        return MU_CLOTH_UNSUPPORTED;
    switch (c->type & 0x3000) {
    case 0:
        sink->state(sink->context, MU_CLOTH_STATE_BLEND_OFF);
        break;
    case 0x1000:
        sink->state(sink->context, MU_CLOTH_STATE_ALPHA_TEST);
        break;
    case 0x2000:
        sink->state(sink->context, MU_CLOTH_STATE_BLEND_ONE);
        break;
    default:
        break;
    }
    if (c->alpha_from_object && c->owner)
        c->alpha = h->alpha;
    if (light)
        sink->color4(sink->context, light[0], light[1], light[2], c->alpha);
    else
        sink->color4(sink->context, 1.0f, 1.0f, 1.0f, c->alpha);
    render_face(c, sink, 1, c->texture_front);
    render_face(c, sink, 0, c->texture_back);
    return MU_CLOTH_OK;
}

void mu_cloth_wind_step(mu_cloth_globals *g)
{
    const int32_t r = crt_rand(g) % 200;
    const float delta = (float)(r - 100) * 0.001f;
    g->wind = g->wind + delta;
    const float low = -0.2f > g->wind ? -0.2f : g->wind;
    g->wind = 1.0f > low ? (-0.2f > g->wind ? -0.2f : g->wind) : 1.0f;
}

/* ---- CreateCloth 0x01357ccc's wing cases ---- */

int mu_cloth_wing_cloths(int32_t wing_type)
{
    switch (wing_type) {
    case 0x2382: case 0x2383: case 0x2394: case 0x2395:
        return 1;
    case 0x2384: case 0x2385:
        return 2;
    default:
        return 0;
    }
}

int mu_cloth_wing_create(mu_cloth out[MU_CLOTH_WINGS_MAX], int32_t wing_type, const mu_cloth_host *h)
{
    const int n = mu_cloth_wing_cloths(wing_type);
    for (int i = 0; i < n; ++i)
        mu_cloth_init(&out[i]);
    switch (wing_type) {
    case 0x2382: case 0x2383:   /* 0x0135b558: Item\texture\kundun_innocence2.tga (0x83f6) */
        mu_cloth_create(&out[0], h, 19, 0.0f, 16.0f, -10.0f, 10, 10, 140.0f, 130.0f, 0x83f6, 0x83f6, 0x1005);
        mu_cloth_add_sphere(&out[0], -10.0f, -2.0f, 18.0f, 25.0f, 17);
        mu_cloth_add_sphere(&out[0], 10.0f, -2.0f, 18.0f, 25.0f, 17);
        mu_cloth_add_sphere(&out[0], -10.0f, 0.0f, 0.0f, 28.0f, 17);
        mu_cloth_add_sphere(&out[0], 10.0f, 0.0f, 0.0f, 28.0f, 17);
        break;
    case 0x2384: case 0x2385:   /* 0x0135b79f: kundun_sparkle3.tga (0x83f7) | kundun_sparkle3_1.tga (0x83f8) */
        mu_cloth_create(&out[0], h, 19, -3.0f, 20.0f, -5.0f, 10, 10, 160.0f, 150.0f, 0x83f7, 0x83f7, 0x1005);
        out[0].uv_scale[0] = 0.5f;
        out[0].uv_scale[1] = 1.0f;
        out[0].push[0] = -0.1f;
        out[0].push[1] = -0.1f;
        mu_cloth_add_sphere(&out[0], -10.0f, -2.0f, 18.0f, 25.0f, 17);
        mu_cloth_add_sphere(&out[0], -10.0f, 0.0f, 0.0f, 28.0f, 17);
        mu_cloth_create(&out[1], h, 19, 3.0f, 20.0f, -5.0f, 10, 10, 160.0f, 150.0f, 0x83f8, 0x83f8, 0x1005);
        out[1].uv_scale[0] = 0.5f;
        out[1].uv_scale[1] = 1.0f;
        out[1].uv_offset[0] = 1.0f;
        out[1].uv_offset[1] = 0.0f;
        out[1].push[0] = 0.1f;
        out[1].push[1] = 0.1f;
        mu_cloth_add_sphere(&out[1], 10.0f, -2.0f, 18.0f, 25.0f, 17);
        mu_cloth_add_sphere(&out[1], 10.0f, 0.0f, 0.0f, 28.0f, 17);
        break;
    case 0x2394: case 0x2395:   /* 0x0135c419: Item\texture\BlackCloak_3.tga (0x846b) */
        mu_cloth_create(&out[0], h, 19, 0.0f, 20.0f, -10.0f, 10, 10, 140.0f, 130.0f, 0x846b, 0x846b, 0x1005);
        mu_cloth_add_sphere(&out[0], -10.0f, -2.0f, 18.0f, 25.0f, 17);
        mu_cloth_add_sphere(&out[0], 10.0f, -2.0f, 18.0f, 25.0f, 17);
        mu_cloth_add_sphere(&out[0], -10.0f, 0.0f, 0.0f, 28.0f, 17);
        mu_cloth_add_sphere(&out[0], 10.0f, 0.0f, 0.0f, 28.0f, 17);
        break;
    default:
        break;
    }
    return n;
}

/* ---- RenderCharacter's cloth block ---- */

static uint8_t skin_index(uint8_t class_byte)   /* 0x0139cab9 = 0x0139d6a2's skin */
{
    const uint8_t flags = (uint8_t)((class_byte >> 4) & 0xf);
    uint8_t tier = 1;
    for (int bit = 3; bit >= 0 && flags; --bit)
        if ((flags >> bit) & 1) {
            tier = (uint8_t)(bit + 2);
            break;
        }
    return (uint8_t)((class_byte & 0xf) + 16 * (tier - 1));
}

static int glow_class(int32_t index)   /* 0x0139bcdc / 0x0139bd24 */
{
    if (index >= 0x211 && index <= 0x21b)
        return 1;
    switch (index) {
    case 0x349: case 0x34a: case 0x34b: case 0x34c: case 0x371: case 0x372: case 0x373: case 0x3c1: case 0x3d5:
        return 1;
    default:
        return 0;
    }
}

void mu_cloth_gate(const mu_cloth_gate_in *in, mu_cloth_gate_out *out)
{
    uint8_t flag = 0;
    const uint8_t skin = skin_index(in->class_byte);
    const uint8_t base = (uint8_t)(in->class_byte & 0xf);
    const int cloth_class = skin == 3 || skin == 0x33 || skin == 0x43 || base == 4 || base == 6 || base == 7 ||
                            base == 0 || base == 8 || base == 9 || base == 0xb || base == 0xc || base == 0xd ||
                            base == 0xf;
    if (cloth_class && in->object_type == 0xa91) {
        if (in->c_0e == 0 || (in->c_0e == 1 && in->own_type == 0xa91))
            flag = 1;
    } else if ((in->wing_type == 0x23f1 || in->wing_type == 0x2401 || in->wing_type == 0x24c6) &&
               in->own_type == 0xa91) {
        flag = 1;
    }
    switch (in->class_index) {
    case 0x37: case 0x169: case 0x3ab: case 0x3ac: case 0x3ad: case 0x3a9:
        flag = 1;
        break;
    default:
        break;
    }
    if (glow_class(in->class_index))
        flag = 0;
    if ((in->world >= 0x12 && in->world <= 0x17) || in->world == 0x35 || in->world == 0x61)   /* 0x009dacb8 */
        flag = 0;
    out->light[0] = 1.0f;
    out->light[1] = 1.0f;
    out->light[2] = 1.0f;
    if (in->pk == 6) {
        out->light[0] = 1.0f;
        out->light[1] = 0.1f;
        out->light[2] = 0.1f;
    }
    out->arg4 = 0;
    out->render = flag;
}

int mu_cloth_draw_allowed(uint16_t action, uint16_t prior_action, int16_t class_index)
{
    if (action == 0xe4 && prior_action == 0xe4)
        return 0;
    if (class_index == 0x271 || class_index == 0x272)
        return 0;
    return 1;
}
