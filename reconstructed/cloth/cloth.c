/* RENDER-ITEMS-CLOAK / CLOAK-002: the client's physics cloth. See cloth.h and docs/research/client-render-items.md
 * parts 25 and 27.
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
static void transform_with(float scale, const float origin[3], const float *matrix, const float in[3], float out[3])
{
    float t[3];
    mu_vector_transform(in, matrix, t);
    for (int k = 0; k < 3; ++k)
        t[k] = scale * t[k];
    for (int k = 0; k < 3; ++k)
        out[k] = t[k] + origin[k];
}

static void transform_position(const mu_cloth_host *h, const float *matrix, const float in[3], float out[3])
{
    transform_with(h->body_scale, h->body_origin, matrix, in, out);
}

/* SetFixed's model (0x00fd7c73 / 0x00fd805b): Models[OBJECT +0x60] for the sub-types 0x5bc / 0x5bd, else
 * Models[OBJECT +0x5c]. 0 = the lookup fails. */
static int fixed_model(const mu_cloth_host *h, float *scale, const float **origin)
{
    if (h->subtype == 0x5bc || h->subtype == 0x5bd) {
        *scale = h->sub_body_scale;
        *origin = h->sub_body_origin;
        return h->sub_has_model;
    }
    *scale = h->body_scale;
    *origin = h->body_origin;
    return h->has_model;
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

static void set_fixed_custom(mu_cloth *c, const mu_cloth_host *h, const float *matrix);

/* SetFixed (virtual slot 4, 0x00fd79bb): the top row hangs from the matrix (slot 5 for the custom variant). */
static void set_fixed(mu_cloth *c, const mu_cloth_host *h, const float *matrix)
{
    if (c->custom) {
        set_fixed_custom(c, h, matrix);
        return;
    }
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
        float scale;
        const float *origin;
        if (!fixed_model(h, &scale, &origin))
            return;
        float out[3];
        transform_with(scale, origin, matrix, p, out);
        vertex_set(&c->vertices[x], out[0], out[1], out[2], 1);
    }
}

/* SetFixed of the angle-matrix variant (virtual slot 5, 0x00fd7d2a): each top-row point is rotated by the cloth's
 * own matrix (+0x48); the origin goes through the bone's rotation (RotatePosition 0x012b7019) and is added. */
static void set_fixed_custom(mu_cloth *c, const mu_cloth_host *h, const float *matrix)
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
        float q[3], p[3], o[3];
        const float a = (float)x * step;
        const float b = 0.5f * width;
        q[0] = a - b;
        q[1] = 10.0f;
        q[2] = 0.0f;
        if ((c->type & 0x30) == 0x10) {
            q[0] = q[0] + 5.0f;
            q[1] = q[1] + 10.0f;
        }
        if ((c->type & 3) == 1) {
            const float e = fabsf((float)x / (float)(c->columns - 1) - 0.5f);
            const float f = e * 2.0f;
            float drop = 10.0f * f;
            drop = drop * f;
            q[1] = q[1] - drop;
        }
        mu_vector_rotate(q, c->matrix, p);
        o[0] = c->origin[0];
        if (curve) {
            const float s = crt_sin((float)x / (float)(c->columns - 1) * 3.14f);
            const float t = s * 130.0f;
            o[1] = t - 110.0f;
        } else {
            o[1] = c->origin[1];
        }
        o[2] = c->origin[2];
        const float pp[3] = {p[0], p[1], p[2]}, oo[3] = {o[0], o[1], o[2]};
        p[0] = pp[2];
        p[1] = -pp[1];
        p[2] = pp[0];
        o[0] = oo[2];
        o[1] = -oo[1];
        o[2] = oo[0];
        float scale;
        const float *origin;
        if (!fixed_model(h, &scale, &origin))
            return;
        float out[3], r[3], rr[3];
        transform_with(scale, origin, matrix, p, out);
        mu_vector_rotate(o, matrix, rr);
        for (int k = 0; k < 3; ++k)
            r[k] = scale * rr[k];
        for (int k = 0; k < 3; ++k)
            out[k] = out[k] + r[k];
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

int mu_cloth_create_angles(mu_cloth *c, const mu_cloth_host *h, int32_t bone, float x, float y, float z,
                           const float angles[3], int32_t columns, int32_t rows, float width, float height,
                           int32_t texture_front, int32_t texture_back, uint32_t type)
{
    const int r = mu_cloth_create(c, h, bone, x, y, z, columns, rows, width, height, texture_front, texture_back,
                                  type);
    if (r == MU_CLOTH_OK) {
        mu_angle_matrix(angles, c->matrix);
        c->custom = 1;
    }
    return r;
}

void mu_cloth_set_glow(mu_cloth *c, int32_t texture, float speed, float minimum, float maximum)
{
    c->glow_texture = texture;
    c->glow[0] = speed;
    c->glow[1] = minimum;
    c->glow[2] = maximum;
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

/* The glow wave 0x0185bdc4(period, 0) (reconstructed/helpers mu_hp_wave): the cosine of WorldTime folded into
 * 2000*pi/|period| ms, mapped to [0, 1]. */
static float glow_wave(float period, float world_time)
{
    float a = 0.0f * 0.017453292f;
    a = (a * 1000.0f) / period + world_time;
    const int32_t t = !(a > -2147483904.0f && a < 2147483648.0f) ? (int32_t)0x80000000u : (int32_t)a;
    const int32_t m = (int32_t)(6283.1855f / period);
    const float x = (float)(t % m) * 0.001f * period;
    const float w = 3.1415927f > x ? -crt_cos(x) : crt_cos(x);
    return (w + 1.0f) * 0.5f;
}

/* The glow pass 0x00fd9663(points): additive, the glow bitmap, one front-wound quad stream. */
static void render_glow(const mu_cloth *c, const mu_cloth_globals *g, const mu_cloth_sink *sink)
{
    if (c->glow_texture == -1)
        return;
    sink->state(sink->context, MU_CLOTH_STATE_BLEND_ONE);
    sink->bind(sink->context, c->glow_texture);
    float bright = 1.0f;
    if (c->glow[0] > 0.0f) {
        const float range = c->glow[2] - c->glow[1];
        const float w = glow_wave(-c->glow[0], g->time);
        bright = w * range + c->glow[1];
    }
    sink->color4(sink->context, bright, bright, bright, c->alpha);
    sink->begin(sink->context, 7);
    for (int32_t y = 0; y < c->rows - 1; ++y)
        for (int32_t x = 0; x < c->columns - 1; ++x) {
            render_vertex(c, sink, x, y);
            render_vertex(c, sink, x + 1, y);
            render_vertex(c, sink, x + 1, y + 1);
            render_vertex(c, sink, x, y + 1);
        }
    sink->end(sink->context);
}

int mu_cloth_render(mu_cloth *c, const mu_cloth_host *h, const mu_cloth_globals *g, const float *light,
                    const mu_cloth_sink *sink)
{
    if ((c->type & 0x40000000) || c->mesh != -1)
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
    render_glow(c, g, sink);
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

/* ---- CreateCloth 0x01357ccc ---- */

typedef struct cloth_sphere_def {
    float x, y, z, radius;
    int8_t bone;
} cloth_sphere_def;

/* One cloth of a case: Create (slot 2) and its setters, in the client's order (the setters write their own fields,
 * the spheres append). */
typedef struct cloth_def {
    int16_t wing;                   /* the case's first wing type (wing_case maps its aliases) */
    int8_t index;                   /* the cloth's slot (+0xe8 apart) */
    int8_t bone;
    float x, y, z;
    int8_t columns, rows;
    float width, height;
    int32_t texture_front, texture_back;
    uint32_t type;
    float uv_scale[2];              /* 0x013bb4a2 */
    float uv_offset[2];             /* 0x013bb477 */
    float push;                     /* 0x013bb44c (both components) */
    int32_t glow;                   /* SetGlow 0x00fd9f50: bitmap (-1 none), speed, minimum, maximum */
    float glow_speed, glow_min, glow_max;
    int8_t glow_level;              /* SetGlow only when CHARACTER +0x21a6 >= this */
    int8_t sphere_count;
    cloth_sphere_def spheres[7];
} cloth_def;

/* The table cases, lifted from the case bodies (0x01358cbe..0x0135e9c4); every value is the immediate the client
 * pushes. */
static const cloth_def cloth_defs[] = {
    {0x2368, 0, 19, 0.0f, 8.0f, 10.0f, 10, 10, 100.0f, 100.0f, 0x7912, 0x7912, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -10.0f, -10.0f, 25.0f, 17}, {10.0f, -10.0f, -10.0f, 25.0f, 17}, {-10.0f, -10.0f, 20.0f, 27.0f, 17}, {10.0f, -10.0f, 20.0f, 27.0f, 17}}},
    {0x2490, 0, 19, 0.0f, 8.0f, 10.0f, 10, 10, 180.0f, 180.0f, 0x7912, 0x7912, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -10.0f, -10.0f, 25.0f, 17}, {10.0f, -10.0f, -10.0f, 25.0f, 17}, {-10.0f, -10.0f, 20.0f, 27.0f, 17}, {10.0f, -10.0f, 20.0f, 27.0f, 17}}},
    {0x230e, 0, 19, 0.0f, 8.0f, 10.0f, 10, 10, 180.0f, 180.0f, 0x7914, 0x7914, 0x1405, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -10.0f, -10.0f, 25.0f, 17}, {10.0f, -10.0f, -10.0f, 25.0f, 17}, {-10.0f, -10.0f, 20.0f, 27.0f, 17}, {10.0f, -10.0f, 20.0f, 27.0f, 17}}},
    {0x230e, 1, 19, 30.0f, 15.0f, 10.0f, 2, 5, 12.0f, 200.0f, 0x7915, 0x7915, 0x1000, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 2, {{0.0f, -15.0f, -10.0f, 35.0f, 2}, {0.0f, 0.0f, 0.0f, 35.0f, 17}}},
    {0x230e, 2, 19, -30.0f, 20.0f, 10.0f, 2, 5, 12.0f, 200.0f, 0x7915, 0x7915, 0x1000, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 2, {{0.0f, -15.0f, -10.0f, 35.0f, 2}, {0.0f, 0.0f, 0.0f, 35.0f, 17}}},
    {0x2488, 0, 19, 0.0f, 25.0f, -10.0f, 10, 10, 130.0f, 160.0f, 0x794c, 0x794c, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x794e, 3.0f, 0.4f, 1.0f, -128, 4, {{-10.0f, 5.0f, -25.0f, 25.0f, 17}, {10.0f, 5.0f, -25.0f, 25.0f, 17}, {-10.0f, -5.0f, -35.0f, 28.0f, 17}, {10.0f, -5.0f, -35.0f, 28.0f, 17}}},
    {0x2488, 1, 19, 45.0f, 34.0f, -10.0f, 2, 5, 12.0f, 140.0f, 0x794d, 0x794d, 0x1000, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x794f, 1.0f, 0.1f, 1.0f, -128, 2, {{0.0f, -15.0f, 10.0f, 35.0f, 10}, {20.0f, 5.0f, 10.0f, 35.0f, 17}}},
    {0x2488, 2, 19, -45.0f, 30.0f, -10.0f, 2, 5, 12.0f, 140.0f, 0x794d, 0x794d, 0x1000, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x794f, 1.0f, 0.0f, 1.0f, -128, 2, {{0.0f, -15.0f, 10.0f, 35.0f, 3}, {-20.0f, 5.0f, 10.0f, 35.0f, 17}}},
    {0x236d, 0, 19, 0.0f, 15.0f, 5.0f, 10, 10, 150.0f, 130.0f, 0x80ed, 0x80ed, 0x1405, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -10.0f, -10.0f, 35.0f, 17}, {10.0f, -10.0f, -10.0f, 35.0f, 17}, {-10.0f, -10.0f, 20.0f, 37.0f, 17}, {10.0f, -10.0f, 20.0f, 37.0f, 17}}},
    {0x2317, 0, 19, 0.0f, 15.0f, 5.0f, 10, 10, 180.0f, 170.0f, 0x80ed, 0x80ed, 0x1405, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -10.0f, -10.0f, 35.0f, 17}, {10.0f, -10.0f, -10.0f, 35.0f, 17}, {-10.0f, -10.0f, 20.0f, 37.0f, 17}, {10.0f, -10.0f, 20.0f, 37.0f, 17}}},
    {0x2318, 0, 19, 0.0f, 15.0f, 5.0f, 10, 10, 180.0f, 170.0f, 0x80ef, 0x80ef, 0x1405, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -10.0f, -10.0f, 35.0f, 17}, {10.0f, -10.0f, -10.0f, 35.0f, 17}, {-10.0f, -10.0f, 20.0f, 37.0f, 17}, {10.0f, -10.0f, 20.0f, 37.0f, 17}}},
    {0x2318, 1, 19, 25.0f, 15.0f, 2.0f, 2, 5, 12.0f, 180.0f, 0x80ee, 0x80ee, 0x9000, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 2, {{0.0f, -15.0f, -20.0f, 35.0f, 2}, {0.0f, 0.0f, 0.0f, 45.0f, 17}}},
    {0x2318, 2, 19, -25.0f, 15.0f, 2.0f, 2, 5, 12.0f, 180.0f, 0x80ee, 0x80ee, 0x11000, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 2, {{0.0f, -15.0f, -20.0f, 35.0f, 2}, {0.0f, 0.0f, 0.0f, 50.0f, 17}}},
    {0x248a, 0, 19, 0.0f, 28.0f, 0.0f, 10, 10, 180.0f, 150.0f, 0x7950, 0x7950, 0x1405, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x7952, 3.0f, 0.5f, 1.0f, -128, 4, {{-10.0f, -10.0f, -10.0f, 30.0f, 17}, {10.0f, -10.0f, -10.0f, 35.0f, 17}, {-10.0f, -10.0f, 20.0f, 37.0f, 17}, {10.0f, -10.0f, 20.0f, 37.0f, 17}}},
    {0x23fc, 0, 19, 0.0f, 20.0f, -2.0f, 10, 10, 100.0f, 120.0f, 0x81e8, 0x81e8, 0x1405, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -10.0f, -10.0f, 25.0f, 17}, {10.0f, -10.0f, -10.0f, 25.0f, 17}, {-10.0f, -10.0f, 20.0f, 27.0f, 17}, {10.0f, -10.0f, 20.0f, 27.0f, 17}}},
    {0x23f3, 0, 19, 0.0f, 20.0f, 5.0f, 10, 10, 130.0f, 150.0f, 0x81e8, 0x81e8, 0x1405, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -10.0f, -10.0f, 25.0f, 17}, {10.0f, -10.0f, -10.0f, 25.0f, 17}, {-10.0f, -10.0f, 20.0f, 27.0f, 17}, {10.0f, -10.0f, 20.0f, 27.0f, 17}}},
    {0x23f4, 0, 19, 0.0f, 15.0f, 5.0f, 10, 10, 160.0f, 160.0f, 0x81e9, 0x81e9, 0x1405, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -10.0f, -10.0f, 25.0f, 17}, {10.0f, -10.0f, -10.0f, 25.0f, 17}, {-10.0f, -10.0f, 20.0f, 27.0f, 17}, {10.0f, -10.0f, 20.0f, 27.0f, 17}}},
    {0x248b, 0, 19, 0.0f, 20.0f, -8.0f, 10, 10, 130.0f, 160.0f, 0x7953, 0x7953, 0x1401, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x7954, 3.0f, 0.27f, 1.0f, -128, 4, {{-10.0f, -10.0f, -10.0f, 25.0f, 17}, {10.0f, -10.0f, -10.0f, 25.0f, 17}, {-10.0f, -10.0f, -20.0f, 27.0f, 17}, {10.0f, -10.0f, -20.0f, 27.0f, 17}}},
    {0x2380, 0, 19, 0.0f, 22.0f, 3.0f, 10, 10, 100.0f, 100.0f, 0x83f3, 0x83f3, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x2381, 0, 19, 0.0f, 25.0f, 0.0f, 10, 10, 140.0f, 140.0f, 0x83f3, 0x83f3, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x83f5, 4.0f, 0.0f, 1.0f, -128, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x2382, 0, 19, 0.0f, 16.0f, -10.0f, 10, 10, 140.0f, 130.0f, 0x83f6, 0x83f6, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x2384, 0, 19, -3.0f, 20.0f, -5.0f, 10, 10, 160.0f, 150.0f, 0x83f7, 0x83f7, 0x1005, {0.5f, 1.0f}, {0.0f, 0.0f}, -0.1f, -1, 0.0f, 0.0f, 0.0f, -128, 2, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x2384, 1, 19, 3.0f, 20.0f, -5.0f, 10, 10, 160.0f, 150.0f, 0x83f8, 0x83f8, 0x1005, {0.5f, 1.0f}, {1.0f, 0.0f}, 0.1f, -1, 0.0f, 0.0f, 0.0f, -128, 2, {{10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x2386, 0, 19, -13.0f, 23.0f, -26.0f, 10, 10, 150.0f, 150.0f, 0x83fa, 0x83fa, 0x1005, {0.5f, 1.0f}, {0.0f, 0.0f}, -0.2f, 0x842d, 4.0f, 0.0f, 1.0f, -128, 2, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x2386, 1, 19, 13.0f, 23.0f, -26.0f, 10, 10, 150.0f, 150.0f, 0x83fb, 0x83fb, 0x1005, {0.5f, 1.0f}, {1.0f, 0.0f}, 0.2f, 0x842e, 4.0f, 0.0f, 1.0f, -128, 2, {{10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x2392, 0, 19, 0.0f, 22.0f, -5.0f, 10, 10, 100.0f, 100.0f, 0x8469, 0x8469, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x2393, 0, 19, 0.0f, 20.0f, 0.0f, 10, 10, 140.0f, 130.0f, 0x8469, 0x8469, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x2394, 0, 19, 0.0f, 20.0f, -10.0f, 10, 10, 140.0f, 130.0f, 0x846b, 0x846b, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x2396, 0, 19, 0.0f, 16.0f, -10.0f, 10, 10, 140.0f, 140.0f, 0x846c, 0x846c, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x846d, 4.0f, 0.0f, 1.0f, 9, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x2398, 0, 19, 0.0f, 16.0f, -10.0f, 10, 10, 140.0f, 140.0f, 0x846e, 0x846e, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x846f, 2.0f, 0.0f, 1.0f, -128, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x239e, 0, 19, -18.0f, 30.0f, 8.0f, 10, 10, 110.0f, 125.0f, 0x84f2, 0x84f2, 0x1005, {0.5f, 1.0f}, {0.0f, 0.0f}, -0.2f, 0x8503, 4.0f, 0.0f, 1.0f, 11, 2, {{-27.0f, 0.0f, 6.0f, 24.0f, 17}, {-42.0f, 73.0f, 15.0f, 52.0f, 19}}},
    {0x239e, 1, 19, 18.0f, 30.0f, 8.0f, 10, 10, 110.0f, 125.0f, 0x84f1, 0x84f1, 0x1005, {0.5f, 1.0f}, {1.0f, 0.0f}, 0.2f, 0x8504, 4.0f, 0.0f, 1.0f, 11, 2, {{27.0f, 0.0f, 6.0f, 24.0f, 17}, {42.0f, 73.0f, 15.0f, 52.0f, 19}}},
    {0x239e, 2, 19, 0.0f, 25.0f, 10.0f, 10, 10, 130.0f, 160.0f, 0x84f3, 0x84f3, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x8502, 4.0f, 0.0f, 1.0f, 11, 5, {{0.0f, 60.0f, 0.0f, 35.0f, 19}, {-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, -30.0f, 28.0f, 17}, {10.0f, 0.0f, -30.0f, 28.0f, 17}}},
    {0x23a0, 0, 19, 0.0f, 25.0f, 5.0f, 10, 10, 160.0f, 150.0f, 0x84f9, 0x84f9, 0x1405, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x84fa, 3.0f, 0.3f, 1.0f, 11, 5, {{-10.0f, -10.0f, -20.0f, 27.0f, 17}, {10.0f, -10.0f, -20.0f, 27.0f, 17}, {0.0f, 50.0f, 0.0f, 30.0f, 19}, {-20.0f, 50.0f, 0.0f, 30.0f, 19}, {20.0f, 50.0f, 0.0f, 30.0f, 19}}},
    {0x23a1, 0, 19, 0.0f, 20.0f, -3.0f, 10, 10, 160.0f, 165.0f, 0x84f5, 0x84f5, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x84f6, 4.0f, 0.0f, 1.0f, 11, 7, {{-10.0f, -10.0f, -10.0f, 25.0f, 17}, {10.0f, -10.0f, -10.0f, 25.0f, 17}, {-10.0f, -10.0f, -20.0f, 27.0f, 17}, {10.0f, -10.0f, -20.0f, 27.0f, 17}, {0.0f, 50.0f, 0.0f, 30.0f, 19}, {-20.0f, 50.0f, 0.0f, 30.0f, 19}, {20.0f, 50.0f, 0.0f, 30.0f, 19}}},
    {0x23a5, 0, 19, -0.0f, 23.0f, 0.0f, 10, 10, 150.0f, 150.0f, 0x84ec, 0x84ec, 0x1005, {0.5f, 1.0f}, {0.0f, 0.0f}, -0.2f, 0x84ef, 4.0f, 0.0f, 1.0f, 11, 2, {{-10.0f, 0.0f, -15.0f, 28.0f, 17}, {-15.0f, 50.0f, -10.0f, 30.0f, 19}}},
    {0x23a5, 1, 19, 0.0f, 23.0f, 0.0f, 10, 10, 150.0f, 150.0f, 0x84ed, 0x84ed, 0x1005, {0.5f, 1.0f}, {1.0f, 0.0f}, 0.2f, 0x84ee, 4.0f, 0.0f, 1.0f, 11, 2, {{10.0f, 0.0f, -15.0f, 28.0f, 17}, {15.0f, 50.0f, -10.0f, 30.0f, 19}}},
    {0x23a7, 0, 19, 0.0f, 15.0f, 0.0f, 10, 10, 270.0f, 150.0f, 0x84f4, 0x84f4, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, 0x8505, 4.0f, 0.0f, 1.0f, 11, 7, {{0.0f, 73.0f, -5.0f, 50.0f, 19}, {-10.0f, -10.0f, -10.0f, 25.0f, 17}, {10.0f, -10.0f, -10.0f, 25.0f, 17}, {-10.0f, -10.0f, -20.0f, 27.0f, 17}, {10.0f, -10.0f, -20.0f, 27.0f, 17}, {-13.0f, 0.0f, 20.0f, 25.0f, 17}, {13.0f, 0.0f, 20.0f, 25.0f, 17}}},
    {0x34e6, 0, 19, 0.0f, 20.0f, -10.0f, 10, 10, 180.0f, 130.0f, 0x8605, 0x8605, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x34e7, 0, 19, 0.0f, 19.5f, -8.0f, 10, 10, 160.0f, 140.0f, 0x8607, 0x8607, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x34e9, 0, 19, 0.0f, 20.0f, -8.0f, 10, 10, 180.0f, 140.0f, 0x8609, 0x8609, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
    {0x34eb, 0, 19, 0.0f, 20.0f, -8.0f, 10, 10, 180.0f, 140.0f, 0x860b, 0x860b, 0x1005, {1.0f, 1.0f}, {0.0f, 0.0f}, 0.0f, -1, 0.0f, 0.0f, 0.0f, -128, 4, {{-10.0f, -2.0f, 18.0f, 25.0f, 17}, {10.0f, -2.0f, 18.0f, 25.0f, 17}, {-10.0f, 0.0f, 0.0f, 28.0f, 17}, {10.0f, 0.0f, 0.0f, 28.0f, 17}}},
};
enum { CLOTH_DEFS = (int)(sizeof cloth_defs / sizeof cloth_defs[0]) };

/* The switch 0x01357e5c..0x0135810d and its byte table 0x0135ea14: the case's first wing type, 0 = none. */
static int32_t wing_case(int32_t wing)
{
    switch (wing) {
    case 0x230e: case 0x2498: return 0x230e;
    case 0x2317: case 0x2492: return 0x2317;
    case 0x2318: case 0x249a: return 0x2318;
    case 0x2368: return 0x2368;
    case 0x236d: return 0x236d;
    case 0x2380: return 0x2380;
    case 0x2381: return 0x2381;
    case 0x2382: case 0x2383: return 0x2382;
    case 0x2384: case 0x2385: return 0x2384;
    case 0x2386: case 0x2387: return 0x2386;
    case 0x2392: return 0x2392;
    case 0x2393: return 0x2393;
    case 0x2394: case 0x2395: return 0x2394;
    case 0x2396: case 0x2397: return 0x2396;
    case 0x2398: case 0x2399: return 0x2398;
    case 0x239e: return 0x239e;
    case 0x23a0: return 0x23a0;
    case 0x23a1: return 0x23a1;
    case 0x23a5: return 0x23a5;
    case 0x23a7: return 0x23a7;
    case 0x23ec: case 0x23fd: case 0x2402: return 0x23ec;
    case 0x23f1: case 0x2401: return 0x23f1;
    case 0x23f3: case 0x2493: return 0x23f3;
    case 0x23f4: case 0x249b: return 0x23f4;
    case 0x23fc: return 0x23fc;
    case 0x2488: case 0x24a0: return 0x2488;
    case 0x248a: case 0x24a2: return 0x248a;
    case 0x248b: case 0x24a3: return 0x248b;
    case 0x2490: case 0x2504: return 0x2490;
    case 0x24c6: return 0x24c6;
    case 0x34e6: return 0x34e6;
    case 0x34e7: case 0x34e8: return 0x34e7;
    case 0x34e9: case 0x34ea: return 0x34e9;
    case 0x34eb: return 0x34eb;
    default: return 0;
    }
}

int mu_cloth_wing_cloths(const mu_cloth_wing_in *in)
{
    if (in->arg4)
        return 1;
    if (in->wing_type == -1)
        return 0;
    const int32_t w = wing_case(in->wing_type);
    switch (w) {
    case 0:
        return 0;
    case 0x23ec:
        return 3;
    case 0x23f1:
        return 1;
    case 0x24c6:
        return 2;
    default: {
        int n = 0;
        for (int i = 0; i < CLOTH_DEFS; ++i)
            if (cloth_defs[i].wing == w)
                n++;
        return n;
    }
    }
}

static void def_create(mu_cloth *c, const cloth_def *d, const mu_cloth_wing_in *in, const mu_cloth_host *h)
{
    mu_cloth_create(c, h, d->bone, d->x, d->y, d->z, d->columns, d->rows, d->width, d->height, d->texture_front,
                    d->texture_back, d->type);
    if (d->uv_scale[0] != 1.0f || d->uv_scale[1] != 1.0f) {
        c->uv_scale[0] = d->uv_scale[0];
        c->uv_scale[1] = d->uv_scale[1];
    }
    if (d->uv_offset[0] != 0.0f || d->uv_offset[1] != 0.0f) {
        c->uv_offset[0] = d->uv_offset[0];
        c->uv_offset[1] = d->uv_offset[1];
    }
    if (d->push != 0.0f) {
        c->push[0] = d->push;
        c->push[1] = d->push;
    }
    if (d->glow != -1 && in->wing_level >= d->glow_level)
        mu_cloth_set_glow(c, d->glow, d->glow_speed, d->glow_min, d->glow_max);
    for (int k = 0; k < d->sphere_count; ++k) {
        const cloth_sphere_def *s = &d->spheres[k];
        mu_cloth_add_sphere(c, s->x, s->y, s->z, s->radius, s->bone);
    }
}

/* 0x23ec / 0x23fd / 0x2402 (0x01358112): three cloths scaled by OBJECT +0xa0 / 0.9 (/ 1.2 in character select). */
static void case_23ec(mu_cloth out[3], const mu_cloth_wing_in *in, const mu_cloth_host *h)
{
    float s;
    if (in->scene == 5)
        s = in->object_scale / 1.2f;
    else
        s = in->object_scale / 0.9f;
    mu_cloth_create(&out[0], h, 19, s * 0.0f, s * 20.0f, s * 10.0f, 10, 10, 170.0f * s, 160.0f * s, 0x7916, 0x7916,
                    0x1405);
    mu_cloth_add_sphere(&out[0], s * -10.0f, s * -10.0f, s * -10.0f, 35.0f * s, 17);
    mu_cloth_add_sphere(&out[0], -(s * -10.0f), s * -10.0f, s * -10.0f, 35.0f * s, 17);
    mu_cloth_add_sphere(&out[0], s * -10.0f, s * -10.0f, s * 20.0f, 37.0f * s, 17);
    mu_cloth_add_sphere(&out[0], -(s * -10.0f), s * -10.0f, s * 20.0f, 37.0f * s, 17);
    mu_cloth_create(&out[1], h, 19, s * 15.0f, s * 5.0f, s * 10.0f, 2, 5, 12.0f * s, 170.0f * s, 0x7917, 0x7917,
                    0x9000);
    mu_cloth_create(&out[2], h, 19, -(s * 15.0f), s * 5.0f, s * 10.0f, 2, 5, 12.0f * s, 170.0f * s, 0x7917, 0x7917,
                    0x11000);
    for (int i = 1; i < 3; ++i)
        mu_cloth_add_sphere(&out[i], s * 0.0f, s * -10.0f, s * -15.0f, 30.0f * s, 2);
    for (int i = 1; i < 3; ++i)
        mu_cloth_add_sphere(&out[i], 0.0f, 0.0f, 0.0f, 40.0f * s, 17);
}

int mu_cloth_wing_create(mu_cloth out[MU_CLOTH_WINGS_MAX], const mu_cloth_wing_in *in, const mu_cloth_host *h)
{
    const int n = mu_cloth_wing_cloths(in);
    for (int i = 0; i < n; ++i)
        mu_cloth_init(&out[i]);
    if (in->arg4) {   /* 0x01357d1d: Player\Robe01.jpg (0x790b) front, Robe02.jpg (0x790c) back */
        mu_cloth_create(&out[0], h, 19, 0.0f, 10.0f, 0.0f, 10, 10, 75.0f, 120.0f, 0x790b, 0x790c, 0x405);
        return n;
    }
    if (n == 0)
        return 0;
    const int32_t w = wing_case(in->wing_type);
    switch (w) {
    case 0x23ec:
        case_23ec(out, in, h);
        break;
    case 0x23f1:   /* 0x0135897e -> 0x013a0242: Item\Texture\admangto.tga (0x7918) */
        mu_cloth_create(&out[0], h, 19, 0.0f, 20.0f, -10.0f, 10, 10, 100.0f, 150.0f, 0x7918, 0x7918, 0x1405);
        mu_cloth_add_sphere(&out[0], 0.0f, -10.0f, -40.0f, 37.0f, 17);
        break;
    case 0x24c6: {   /* 0x01358a40: the angle-matrix variant on bone 47, season_wing_periodc(2).tga (0x830c / 0x830d) */
        static const float angles[3] = {0.0f, 90.0f, 0.0f};
        for (int i = 0; i < 2; ++i) {
            const int32_t bitmap = i ? 0x830d : 0x830c;
            mu_cloth_create_angles(&out[i], h, 47, 32.0f, -24.0f, i ? -32.0f : 32.0f, angles, 10, 10, 65.0f, 125.0f,
                                   bitmap, bitmap, 0x1404);
            mu_cloth_add_sphere(&out[i], 0.0f, -10.0f, -40.0f, 37.0f, 17);
        }
        break;
    }
    default:
        for (int i = 0; i < CLOTH_DEFS; ++i)
            if (cloth_defs[i].wing == w)
                def_create(&out[cloth_defs[i].index], &cloth_defs[i], in, h);
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

static int skin3_hidden(uint8_t class_byte, int32_t subtype)   /* 0x009a0989 */
{
    if (skin_index(class_byte) != 3)
        return 0;
    switch (subtype) {
    case 0x429: case 0x3ed: case 0x3e9: case 0xa5e: case 0x541: case 0x552: case 0x5ba: case 0x5bb: case 0x5bc:
    case 0x5bd: case 0x5be: case 0x5bf: case 0x5c4: case 0x5c5:
        return 1;
    default:
        return 0;
    }
}

int mu_cloth_draw_allowed(uint8_t class_byte, int32_t subtype, uint16_t action, uint16_t prior_action,
                          int16_t class_index)
{
    if (subtype == 0x431 || subtype == 0x432)   /* 0x01362e1d */
        return 0;
    if (action == 0xe4 && prior_action == 0xe4)
        return 0;
    if (skin3_hidden(class_byte, subtype))   /* 0x01362e87 */
        return 0;
    if (class_index == 0x271 || class_index == 0x272)
        return 0;
    return 1;
}
