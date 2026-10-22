/* The later mounts' class visuals (vtable +0x1c) and class steps (NATIVE-HELPERS-002). See mount_class.h. */
#include <math.h>
#include <string.h>

#include "mount_class.h"
#include "../record-math/record_math.h"

typedef struct vctx {
    mu_helpers *h;
    mu_hp_class_state *s;
    const mu_hp_class_inputs *in;
    const mu_hp_class_host *host;
    mu_hp_after_call *out;
    int32_t capacity, n;
} vctx;

static mu_hp_after_call *push(vctx *c, int32_t kind)
{
    static mu_hp_after_call sink;
    mu_hp_after_call *a = c->n < c->capacity && c->out ? &c->out[c->n] : &sink;
    c->n++;
    memset(a, 0, sizeof *a);
    a->kind = kind;
    return a;
}

static int32_t cvtt(float x)
{
    if (!(x > -2147483904.0f && x < 2147483648.0f))
        return (int32_t)0x80000000u;
    return (int32_t)x;
}

float mu_hp_rand_range(mu_helpers *h, float lo, float hi, uint32_t steps)
{
    /* 0x011ff622: the steps as an unsigned double rounded to binary32 */
    const float s = (float)(double)steps;
    const int32_t a = cvtt(s * lo), b = cvtt(s * hi);
    const int32_t r = mu_hp_rand(h);
    float x = (float)(r % (b - a + 1) + a) / s;
    if (lo > x)
        x = lo;
    else if (x > hi)
        x = hi;
    return x;
}

static float csin(float x)
{
    return (float)sin((double)x);   /* 0x009681bd */
}

static float ccos(float x)
{
    return (float)cos((double)x);   /* 0x009fa223 */
}

float mu_hp_rand_direction(mu_helpers *h, float out[3], float r_max, float r_min, float t_max, float t_min,
                           float p_max, float p_min)
{
    /* 0x00d01fc6 */
    if (0.0f > r_min)
        r_min = 0.0f;
    float r = !(r_min < r_max) ? r_min : mu_hp_rand_range(h, r_min, r_max, 0x32);
    if (1e-6f > r) {
        out[0] = out[1] = out[2] = 0.0f;
        return 0.0f;
    }
    if (t_min > t_max)
        t_min = t_max;
    if (0.0f > t_min)
        t_min = 0.0f;
    if (t_max > 180.0f)
        t_max = 180.0f;
    const float t = mu_hp_rand_range(h, t_min * 0.017453292f, t_max * 0.017453292f, 100);
    if (p_min > p_max)
        p_min = p_max;
    if (0.0f > p_min)
        p_min = 0.0f;
    if (p_max > 360.0f)
        p_max = 360.0f;
    const float p = mu_hp_rand_range(h, p_min * 0.017453292f, p_max * 0.017453292f, 100);
    const float st = csin(t) * r;
    out[0] = st * ccos(p);
    const float st2 = csin(t) * r;
    out[1] = st2 * csin(p);
    out[2] = ccos(t) * r;
    return r;
}

float mu_hp_rand_flat(mu_helpers *h, float out[3], float r_max, float r_min, int32_t mode)
{
    /* 0x00d0221e */
    if (0.0f > r_min)
        r_min = 0.0f;
    float r = r_min < r_max ? mu_hp_rand_range(h, r_min, r_max, 0x32) : r_min;
    if (!(1e-6f <= r)) {
        out[0] = out[1] = out[2] = 0.0f;
        return 0.0f;
    }
    const float a = mu_hp_rand_range(h, 0.0f, 200.0f, 0x32) * 0.01f * 3.1415927f;
    if (mode == 1) {
        out[0] = ccos(a) * r;
        out[1] = 0.0f;
        out[2] = csin(a) * r;
    } else if (mode == 2) {
        out[0] = 0.0f;
        out[1] = ccos(a) * r;
        out[2] = csin(a) * r;
    } else {
        out[0] = ccos(a) * r;
        out[1] = csin(a) * r;
        out[2] = 0.0f;
    }
    return r;
}

/* TransformByObjectBone 0x012b678d(model, out, object, bone, 0) */
static void object_bone(vctx *c, int32_t bone, float out[3])
{
    mu_hp_after_call *a = push(c, MU_HP_AC_OBJECT_BONE);
    a->mesh = bone;
    out[0] = out[1] = out[2] = 0.0f;
    if (c->host && c->host->object_bone)
        c->host->object_bone(c->host->context, bone, out);
}

static void sprite(vctx *c, int32_t type, const float p[3], float scale, const float light[3])
{
    mu_hp_after_call *a = push(c, MU_HP_AC_SPRITE);
    a->type = type;
    a->scale = scale;
    memcpy(a->position, p, sizeof a->position);
    memcpy(a->light, light, sizeof a->light);
}

static void particle(vctx *c, int32_t type, const float p[3], const float light[3], int32_t subtype, float scale)
{
    mu_hp_after_call *a = push(c, MU_HP_AC_PARTICLE);
    a->type = type;
    a->subtype = subtype;
    a->scale = scale;
    memcpy(a->position, p, sizeof a->position);
    memcpy(a->angle, c->in->angle, sizeof a->angle);
    memcpy(a->light, light, sizeof a->light);
}

/* CreateEffect wrapper 0x013c0eaa(type, p, angle, light, 0, NULL, -1, 0, 0, 0, scale, -1, 0, 0) */
static void effect(vctx *c, int32_t type, const float p[3], const float light[3], float scale)
{
    mu_hp_after_call *a = push(c, MU_HP_AC_EFFECT);
    a->type = type;
    a->scale = scale;
    memcpy(a->position, p, sizeof a->position);
    memcpy(a->angle, c->in->angle, sizeof a->angle);
    memcpy(a->light, light, sizeof a->light);
}

/* RenderTerrainAlphaBitmap 0x016cdd5f(texture, x, y, size, size, light, angle x, alpha, 5, 1, 0) */
static void decal(vctx *c, int32_t texture, const float p[3], float size, const float light[3])
{
    mu_hp_after_call *a = push(c, MU_HP_AC_DECAL);
    a->type = texture;
    a->scale = size;
    a->position[0] = p[0];
    a->position[1] = p[1];
    a->angle[0] = c->in->angle[0];
    a->alpha = c->in->alpha;
    memcpy(a->light, light, sizeof a->light);
}

static void set3(float v[3], float x, float y, float z)
{
    v[0] = x;
    v[1] = y;
    v[2] = z;
}

/* Shining Tail 0x01057fb0 (vtable +0x1c of 0x01ab6e3c) */
static void shining_tail(vctx *c)
{
    const mu_hp_class_inputs *in = c->in;
    float light[3], p[3], v[3];
    float l = mu_hp_wave(-4.0f, 0.0f, in->world_time) * 0.7f + 0.3f;
    set3(light, l * 1.0f, l * 1.0f, l * 1.0f);
    object_bone(c, 0x28, p);
    sprite(c, 0x8108, p, 0.45f, light);
    const float k = (float)(mu_hp_rand(c->h) % 0x14) / 25.0f + 0.15f;
    set3(light, k, k, k);
    sprite(c, 0x8179, p, 0.2f, light);
    const int32_t tick = (cvtt(in->world_time) / 100) % 600;
    set3(light, 0.75f, 0.8f, 1.0f);
    object_bone(c, 0x27, p);
    sprite(c, 0x7f68, p, 1.0f, light);
    object_bone(c, 0x26, p);
    sprite(c, 0x7f68, p, 1.0f, light);
    push(c, MU_HP_AC_EYES);   /* 0x0137a948(object, model, 0x27, 0x26, -1, -1, -1, -1): object +0x194 / +0x188 */
    if (!c->s->flag_48) {
        c->s->flag_48 = 1;
        static const int32_t subs[2] = {0x43, 0x44};
        for (int32_t i = 0; i < 2; ++i) {   /* CreateJoint(0x7fd6, pos, pos, angle, sub, object, 30, -1, ...) */
            mu_hp_after_call *a = push(c, MU_HP_AC_JOINT);
            a->type = 0x7fd6;
            a->subtype = subs[i];
            a->scale = 30.0f;
            memcpy(a->position, in->position, sizeof a->position);
            memcpy(a->angle, in->angle, sizeof a->angle);
            set3(a->light, 0.6f, 0.4f, 0.9f);
        }
    }
    l = mu_hp_wave(-2.0f, 0.0f, in->world_time) * 0.5f + 0.5f;
    set3(light, l * 0.5f, l * 0.8f, l * 0.7f);
    for (int32_t b = 0x2b; b <= 0x2e; ++b) {
        object_bone(c, b, p);
        sprite(c, 0x8109, p, 0.5f, light);
    }
    l = mu_hp_wave(-2.0f, 180.0f, in->world_time) * 0.8f + 0.2f;
    set3(light, l * 0.5f, l * 0.8f, l * 0.7f);
    for (int32_t b = 0x4b; b <= 0x50; ++b) {
        object_bone(c, b, p);
        sprite(c, 0x8109, p, 0.5f, light);
    }
    set3(light, 0.7f, 1.0f, 0.9f);
    object_bone(c, 0x51, p);
    sprite(c, 0x7ef7, p, 1.5f, light);
    object_bone(c, 0x52, p);
    sprite(c, 0x7ef7, p, 1.0f, light);
    set3(light, 0.3f, 0.3f, 0.35f);
    static const struct { int32_t bone; float scale; } dim[7] = {
        {0x70, 7.5f}, {0x7f, 7.5f}, {0x61, 5.0f}, {0x98, 5.0f}, {0x69, 5.0f}, {0x90, 5.0f}, {0x59, 5.0f}};
    for (int32_t i = 0; i < 7; ++i) {
        object_bone(c, dim[i].bone, p);
        sprite(c, 0x7ef7, p, dim[i].scale, light);
    }
    /* the tails' mist and sparks around bone 0x6f */
    static const struct { float r_max, r_min; int32_t type, sub; float scale, light[3]; } puffs[3] = {
        {120.0f, 50.0f, 0x7f5a, 0x7f, 2.0f, {0.1f, 0.25f, 0.6f}},
        {80.0f, 20.0f, 0x831d, 6, 1.5f, {0.4f, 0.6f, 0.5f}},
        {150.0f, 80.0f, 0x83b3, 6, 0.7f, {0.4f, 0.4f, 1.0f}}};
    for (int32_t i = 0; i < 3; ++i) {
        if (mu_hp_rand(c->h) % 5 != 0)
            continue;
        mu_hp_rand_direction(c->h, v, puffs[i].r_max, puffs[i].r_min, 180.0f, 0.0f, 360.0f, 0.0f);
        object_bone(c, 0x6f, p);
        p[0] = p[0] + v[0];
        p[1] = p[1] + v[1];
        p[2] = p[2] + v[2];
        particle(c, puffs[i].type, p, puffs[i].light, puffs[i].sub, puffs[i].scale);
    }
    if (mu_hp_rand(c->h) % 3 == 0) {
        float m[12], w[3];
        mu_hp_rand_flat(c->h, v, 80.0f, 20.0f, 1);
        v[1] = mu_hp_rand_range(c->h, 100.0f, 120.0f, 1);
        mu_angle_matrix(in->angle, m);
        mu_vector_rotate(v, m, w);
        object_bone(c, 0x6f, p);
        p[0] = p[0] + w[0];
        p[1] = p[1] + w[1];
        p[2] = p[2] + w[2];
        set3(light, 0.7f, 0.9f, 0.6f);
        particle(c, 0x7f26, p, light, 0x2a, 2.0f);
    }
    if (mu_hp_rand(c->h) % 10 == 0) {
        mu_hp_rand_flat(c->h, v, 200.0f, 100.0f, 0);
        v[2] = mu_hp_rand_range(c->h, 30.0f, 200.0f, 1);
        p[0] = in->position[0] + v[0];
        p[1] = in->position[1] + v[1];
        p[2] = in->position[2] + v[2];
        set3(light, 0.1f, 0.56f, 0.77f);
        effect(c, 0x6f6, p, light, 0.5f);
    }
    set3(light, 0.1f, 0.6f, 0.45f);
    static const int32_t sparks[4] = {0x32, 0x40, 7, 0x15};
    for (int32_t i = 0; i < 4; ++i) {
        if (mu_hp_rand(c->h) % 3 != 0)
            continue;
        object_bone(c, sparks[i], p);
        particle(c, 0x8086, p, light, 0x13, 1.15f);
    }
    /* the paws' rune circles: fade in while it stands, out while it walks or runs */
    static const int32_t paws[4] = {0x3c, 0x4a, 0x11, 0x1f};
    float *a4 = &c->s->a4;
    if (in->action == 2 || in->action == 3) {
        if (*a4 > 0.0f)
            *a4 = *a4 - 0.05f;
        else if (0.0f > *a4)
            *a4 = 0.0f;
    } else {
        if (!(*a4 >= 1.0f))
            *a4 = *a4 + 0.05f;
        else if (*a4 > 1.0f)
            *a4 = 1.0f;
        if (tick % 10 == 0) {
            set3(light, 0.2f, 0.4f, 1.0f);
            for (int32_t i = 0; i < 4; ++i) {
                object_bone(c, paws[i], p);
                effect(c, 0x8438, p, light, 1.5f);
            }
        }
    }
    if (*a4 > 0.0f) {
        l = mu_hp_wave(-4.0f, 0.0f, in->world_time) * 0.5f + 0.5f;
        set3(light, l * *a4 * 0.2f, l * *a4 * 0.8f, l * *a4 * 0.6f);
        mu_hp_after_call *a = push(c, MU_HP_AC_BLEND);
        a->flags = 0x0184aa2b;   /* EnableAlphaBlend */
        for (int32_t i = 0; i < 4; ++i) {
            object_bone(c, paws[i], p);
            decal(c, 0x8438, p, 1.0f, light);
        }
        set3(light, *a4 * 0.2f, *a4 * 0.2f, *a4 * 0.8f);
        for (int32_t i = 0; i < 4; ++i) {
            object_bone(c, paws[i], p);
            decal(c, 0x7ef7, p, 2.0f, light);
        }
        a = push(c, MU_HP_AC_BLEND);
        a->flags = 0x0184a7f3;   /* DisableAlphaBlend */
    }
}

int mu_hp_mount_class_visuals(mu_helpers *h, int32_t cls, mu_hp_class_state *state, const mu_hp_class_inputs *in,
                              const mu_hp_class_host *host, mu_hp_after_call *out, int32_t capacity, int32_t *count)
{
    vctx c;
    memset(&c, 0, sizeof c);
    c.h = h;
    c.s = state;
    c.in = in;
    c.host = host;
    c.out = out;
    c.capacity = capacity;
    int r = 1;
    switch (cls) {
    case MU_HP_MOUNT_SHINING_TAIL:
        shining_tail(&c);
        break;
    default:
        r = 0;   /* the classic four: 0x0103d8be (nothing); the others are not reconstructed */
        break;
    }
    if (count)
        *count = c.n;
    return r;
}

int mu_hp_mount_class_step(mu_helpers *h, int32_t cls, const mu_hp_class_inputs *in, const mu_hp_class_host *host,
                           mu_hp_after_call *out, int32_t capacity, int32_t *count)
{
    vctx c;
    memset(&c, 0, sizeof c);
    c.h = h;
    c.in = in;
    c.host = host;
    c.out = out;
    c.capacity = capacity;
    int r = 0;
    if (cls == MU_HP_MOUNT_SHINING_TAIL && (in->action == 2 || in->action == 3)) {
        /* 0x0105a0bb from the class move 0x01057e4d: the claws' steps (effect 0x6f3) at two frames */
        static const char *const names[4] = {"leg_nailfront", "leg_nailfront001", "leg_rear", "leg_rear001"};
        for (int32_t pair = 0; pair < 2; ++pair) {
            const float lo = pair ? 9.0f : 4.0f, hi = pair ? 10.0f : 5.0f;
            if (!(lo <= in->frame && in->frame <= hi))
                continue;
            for (int32_t i = 0; i < 2; ++i) {
                float p[3] = {0.0f, 0.0f, 0.0f};
                mu_hp_after_call *a = push(&c, MU_HP_AC_NAMED_BONE);
                a->mesh = 2 * pair + i;
                if (host && host->named_bone)
                    host->named_bone(host->context, names[2 * pair + i], p);
                a = push(&c, MU_HP_AC_EFFECT);
                a->type = 0x6f3;
                a->subtype = 2;
                a->scale = 1.0f;
                memcpy(a->position, p, sizeof a->position);
                memcpy(a->angle, in->angle, sizeof a->angle);
                set3(a->light, 0.35f, 0.44f, 1.0f);
            }
        }
        r = 1;
    }
    if (count)
        *count = c.n;
    return r;
}
