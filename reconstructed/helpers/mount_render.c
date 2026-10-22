/* The mounts' registry functors (NATIVE-HELPERS-002). See mount_render.h. */
#include <math.h>
#include <string.h>

#include "mount_render.h"

typedef struct ctx {
    mu_helpers *h;
    const mu_hp_object *o;
    const mu_hp_after_inputs *in;
    const mu_hp_after_host *host;
    mu_hp_after_call *out;
    int32_t capacity, n;
    float color[3];
    uint8_t m94;
} ctx;

static mu_hp_after_call *push(ctx *c, int32_t kind)
{
    static mu_hp_after_call sink;
    mu_hp_after_call *a = c->n < c->capacity && c->out ? &c->out[c->n] : &sink;
    c->n++;
    memset(a, 0, sizeof *a);
    a->kind = kind;
    a->color[0] = c->color[0];
    a->color[1] = c->color[1];
    a->color[2] = c->color[2];
    a->model_94 = c->m94;
    return a;
}

static void color(ctx *c, float r, float g, float b)
{
    c->color[0] = r;
    c->color[1] = g;
    c->color[2] = b;
}

static void mesh(ctx *c, int32_t mesh_index, uint32_t flags, float alpha, int32_t blend_mesh, float blend_light,
                 float u, float v, int32_t texture)
{
    mu_hp_after_call *a = push(c, MU_HP_AC_MESH);
    a->mesh = mesh_index;
    a->flags = flags;
    a->alpha = alpha;
    a->blend_mesh = blend_mesh;
    a->blend_light = blend_light;
    a->u = u;
    a->v = v;
    a->texture = texture;
}

static void body(ctx *c, uint32_t flags, float alpha, int32_t blend_mesh, float blend_light, float u, float v,
                 int32_t hidden, int32_t texture)
{
    mu_hp_after_call *a = push(c, MU_HP_AC_BODY);
    a->flags = flags;
    a->alpha = alpha;
    a->blend_mesh = blend_mesh;
    a->blend_light = blend_light;
    a->u = u;
    a->v = v;
    a->hidden = hidden;
    a->texture = texture;
}

/* the object's own pass arguments */
#define A (c->o->alpha)
#define BM (c->o->blend_mesh)
#define BL (c->o->blend_light)
#define OU (c->in->object_u)
#define OV (c->in->object_v)
#define O68 (c->o->field_68)
#define O_MESH(m, f, t) mesh(c, (m), (f), A, BM, BL, OU, OV, (t))

/* cvttss2si: truncation, 0x80000000 for NaN and out-of-range values */
static int32_t cvtt(float x)
{
    if (!(x > -2147483904.0f && x < 2147483648.0f))
        return (int32_t)0x80000000u;
    return (int32_t)x;
}

static float wave(ctx *c, float period)
{
    return mu_hp_wave(period, 0.0f, c->in->world_time);
}

static int world_16a88ae(int32_t world)
{
    return mu_hp_world_16a88ae(world);
}

/* the shared tail of the Dark Horse, Fenrir and Divine Horse functors: a second blob shadow */
static void shadow(ctx *c, int32_t first, int32_t end)
{
    const mu_hp_after_inputs *in = c->in;
    if (in->world == 10 || in->world == 0x84 || in->world_9b0418 || in->event_block)
        return;
    mu_hp_after_call *a = push(c, MU_HP_AC_ALPHA_TEST);
    a->mesh = 1;
    a = push(c, MU_HP_AC_COLOR4);
    a->scale = world_16a88ae(in->world) ? 0.2f : 0.7f;
    a = push(c, MU_HP_AC_SHADOW);
    a->mesh = first;
    a->texture = end;
}

float mu_hp_wave(float period, float phase, float world_time)
{
    /* 0x0185bdc4 */
    float a = phase * 0.017453292f;
    a = (a * 1000.0f) / period + world_time;
    int32_t t = !(a > -2147483904.0f && a < 2147483648.0f) ? (int32_t)0x80000000u : (int32_t)a;
    int32_t m = (int32_t)(6283.1855f / period);
    float x = (float)(t % m) * 0.001f * period;
    float w;
    if (3.1415927f > x)
        w = -(float)cos((double)x);
    else
        w = (float)cos((double)x);
    return (w + 1.0f) * 0.5f;
}

/* ---------------------------------------------------------------- functors */

/* 0x00a2eaa2 */
static int dark_horse(ctx *c)
{
    if (c->o->subtype == 1) {
        color(c, 0.2f, 0.2f, 0.2f);
        body(c, 0x42, A, BM, BL, OU, OV, O68, -1);
        return 1;
    }
    color(c, 1.0f, 1.0f, 1.0f);
    body(c, 2, A, BM, BL, OU, OV, O68, -1);
    color(c, 1.0f, 0.8f, 0.3f);
    for (int32_t m = 0xc; m <= 0xf; ++m)   /* the model has 13 meshes: 0xd..0xf draw nothing */
        O_MESH(m, 0x44, O68);
    shadow(c, 8, 9);
    return 1;
}

/* 0x00a318b8 */
static int dinorant(ctx *c)
{
    body(c, 2, A, BM, BL, OU, OV, O68, -1);
    return 1;
}

static void bone(ctx *c, int32_t index, const float in[3], float out[3])
{
    mu_hp_after_call *a = push(c, MU_HP_AC_BONE);
    a->mesh = index;
    a->position[0] = in[0];
    a->position[1] = in[1];
    a->position[2] = in[2];
    if (c->host && c->host->bone)
        c->host->bone(c->host->context, index, in, out);
}

static void sprite(ctx *c, int32_t type, const float p[3], float scale, const float light[3])
{
    mu_hp_after_call *a = push(c, MU_HP_AC_SPRITE);
    a->type = type;
    a->scale = scale;
    memcpy(a->position, p, sizeof a->position);
    memcpy(a->light, light, sizeof a->light);
}

static void particle(ctx *c, int32_t type, const float p[3], const float light[3], int32_t subtype, float scale)
{
    mu_hp_after_call *a = push(c, MU_HP_AC_PARTICLE);
    a->type = type;
    a->subtype = subtype;
    a->scale = scale;
    memcpy(a->position, p, sizeof a->position);
    memcpy(a->angle, c->o->angle, sizeof a->angle);
    memcpy(a->light, light, sizeof a->light);
}

static void effect(ctx *c, int32_t type, const float p[3], const float light[3], int32_t subtype)
{
    mu_hp_after_call *a = push(c, MU_HP_AC_EFFECT);
    a->type = type;
    a->subtype = subtype;
    memcpy(a->position, p, sizeof a->position);
    memcpy(a->angle, c->o->angle, sizeof a->angle);
    memcpy(a->light, light, sizeof a->light);
}

/* Fenrir's sparks at bone 14 while it attacks (action 4) */
static void fenrir_sparks(ctx *c, float k)
{
    const float light[3] = {1.0f, 0.0f, 0.0f};
    float v[3], out[3] = {0.0f, 0.0f, 0.0f};
    int32_t r1 = mu_hp_rand(c->h), r2 = mu_hp_rand(c->h);
    v[0] = (float)(r1 % 10 - 10) * 0.5f;
    v[1] = 0.0f;
    v[2] = (float)(r2 % 40 - 20) * 0.5f;
    bone(c, 14, v, out);
    particle(c, 0x7f26, out, light, 0xf, k * 0.05f + 0.7f);
}

/* 0x00a335e9 / 0x00a34652 / 0x00a356bb / 0x00a36724 */
static int fenrir(ctx *c)
{
    const mu_hp_object *o = c->o;
    float k = (float)sin((double)(c->in->world_time * 0.002f)) * 0.2f;
    push(c, MU_HP_AC_PUSH);
    color(c, 1.0f, 1.0f, 1.0f);
    if (o->type == 0x4ab) {
        c->m94 = 0;
        O_MESH(0, 2, -1);
        O_MESH(0, 0x46, -1);
        O_MESH(1, 2, -1);
        if (o->action == 4)
            fenrir_sparks(c, k);
    } else {
        c->m94 = 0;
        O_MESH(0, 2, -1);
        O_MESH(1, 2, -1);
        if (o->action == 4) {
            color(c, 1.0f, 1.0f, 1.0f);
            O_MESH(1, 0x46, -1);
            fenrir_sparks(c, k);
        }
    }
    c->m94 = 0xff;
    push(c, MU_HP_AC_POP);
    shadow(c, -1, -1);
    /* the eyes and the mane: flares at bones 11 and 13 */
    float light[3], v[3], out[3] = {0.0f, 0.0f, 0.0f};
    light[0] = 0.9f + k;
    light[1] = k * 0.5f + 0.2f;
    light[2] = k * 0.5f + 0.1f;
    v[0] = 50.0f, v[1] = 2.0f, v[2] = 11.0f;
    bone(c, 11, v, out);
    sprite(c, 0x7ef7, out, k * 0.1f + 0.5f, light);
    sprite(c, 0x7ef7, out, k * 0.1f + 0.5f, light);
    v[0] = 50.0f, v[1] = 2.0f, v[2] = -11.0f;
    bone(c, 11, v, out);
    sprite(c, 0x7ef7, out, k * 0.1f + 0.5f, light);
    sprite(c, 0x7ef7, out, k * 0.1f + 0.5f, light);
    light[0] = 1.0f, light[1] = 0.3f, light[2] = 0.2f;
    v[0] = 40.0f, v[1] = 15.0f, v[2] = 0.0f;
    bone(c, 13, v, out);
    sprite(c, 0x7ef7, out, 1.5f, light);
    sprite(c, 0x7ef7, out, 1.0f, light);
    /* the body lightning (effect 0x4ac, twice) in the state's colour */
    int32_t sub;
    if (o->type == 0x4a9) {
        light[0] = 0.8f, light[1] = 0.0f, light[2] = 0.0f, sub = 1;
    } else if (o->type == 0x4aa) {
        light[0] = 0.1f, light[1] = 0.1f, light[2] = 0.8f, sub = 2;
    } else if (o->type == 0x4ab) {
        light[0] = 0.8f, light[1] = 0.8f, light[2] = 0.1f, sub = 4;
    } else {
        light[0] = 1.0f, light[1] = 1.0f, light[2] = 0.2f, sub = 3;
    }
    effect(c, 0x4ac, o->position, light, 0);
    effect(c, 0x4ac, o->position, light, 0);
    /* the paws' thunder (effect 0x4ad) at the steps */
    light[0] = light[1] = light[2] = 1.0f;
    const float zero[3] = {0.0f, 0.0f, 0.0f};
    float f = o->frame;
    if (o->action == 1) {
        if (0.0f <= f && f <= 1.5f) {
            static const int32_t paws[4] = {22, 28, 36, 44};
            for (int32_t i = 0; i < 4; ++i) {
                bone(c, paws[i], zero, out);
                effect(c, 0x4ad, out, light, sub);
            }
        }
    } else if (o->action == 2) {
        if (f <= 1.0f || 1.4f < f) {
            if (4.8f < f && f <= 5.2f) {
                bone(c, 36, zero, out);
                effect(c, 0x4ad, out, light, sub);
                bone(c, 44, zero, out);
                effect(c, 0x4ad, out, light, sub);
            }
        } else {
            bone(c, 22, zero, out);
            effect(c, 0x4ad, out, light, sub);
            bone(c, 28, zero, out);
            effect(c, 0x4ad, out, light, sub);
        }
    }
    return 1;
}

/* 0x00a477ec */
static int ghost_horse(ctx *c)
{
    const mu_hp_object *o = c->o;
    float saved[3] = {c->color[0], c->color[1], c->color[2]};
    color(c, 0.5f, 0.5f, 0.5f);
    mesh(c, 2, 0x42, A, 2, wave(c, -4.0f) * 0.3f + 0.2f, OU, OV, -1);
    color(c, 0.05f, 0.45f, 0.05f);
    O_MESH(2, 0x44, 0x82e3);
    color(c, saved[0], saved[1], saved[2]);
    O_MESH(3, 2, -1);
    if (o->subtype < 2) {
        if (o->subtype < 1)
            color(c, 0.2f, 0.24f, 0.3f);
        else
            color(c, 0.35f, 0.39f, 0.45f);
    } else {
        color(c, 0.6f, 0.6f, 0.7f);
    }
    O_MESH(3, 0x44, 0x82e4);
    O_MESH(0, 0x44, 0x82e4);
    color(c, 1.0f, 1.0f, 1.0f);
    mesh(c, 4, 0x42, A, 4, wave(c, -4.0f) * 0.7f + 0.2f, OU, OV, -1);
    color(c, saved[0], saved[1], saved[2]);
    O_MESH(0, 2, -1);
    O_MESH(1, 2, -1);
    if (0 < o->subtype) {
        color(c, 1.0f, 1.0f, 1.0f);
        if (o->subtype == 1) {
            float l = wave(c, -4.0f) * 0.5f + 0.3f;
            mesh(c, 5, 0x42, A, 5, l, OU, OV, -1);
            mesh(c, 7, 0x42, A, 7, l, OU, OV, -1);
        } else {
            mesh(c, 5, 0x42, A, 5, BL, OU, OV, -1);
            mesh(c, 7, 0x42, A, 7, BL, OU, OV, -1);
        }
    }
    if (1 < o->subtype) {
        float l = wave(c, -4.0f) * 0.7f + 0.3f;
        color(c, 0.7f, 0.7f, 0.8f);
        mesh(c, 6, 0x42, A, 6, l, OU, OV, -1);
    }
    color(c, saved[0], saved[1], saved[2]);
    return 1;
}

/* 0x00a480f9 (rare: 0x00a48462) */
static int ice_dragon(ctx *c, int rare)
{
    float saved[3] = {c->color[0], c->color[1], c->color[2]};
    O_MESH(1, 2, -1);
    if (rare)
        color(c, 0.8f, 0.8f, 0.8f);
    else
        color(c, 0.25f, 0.15f, 0.55f);
    O_MESH(1, 0x44, rare ? 0x831a : 0x82e4);
    float l = wave(c, -4.0f) * 0.5f + 0.5f;
    color(c, 0.5f, 0.5f, 0.5f);
    mesh(c, 0, 0x42, A, 0, l, OU, OV, -1);
    if (rare)
        color(c, 0.75f, 0.75f, 0.9f);
    else
        color(c, 0.85f, 0.85f, 0.75f);
    mesh(c, 0, 0x46, 0.5f, BM, BL, OU, OV, -1);
    color(c, saved[0], saved[1], saved[2]);
    mesh(c, 2, 0x42, A, 2, BL, OU, OV, -1);
    return 1;
}

/* 0x00a4cd20 (rare: 0x00a4cfed) */
static int pierce_lion(ctx *c, int rare)
{
    color(c, 1.0f, 1.0f, 1.0f);
    body(c, 2, A, BM, BL, OU, OV, -1, -1);
    float a = wave(c, -4.0f) * 0.6f + 0.4f;
    float b = rare ? wave(c, -4.0f) * 0.4f + 0.6f : wave(c, -4.0f) * 0.6f + 0.4f;
    mesh(c, 0, 2, A, 0, rare ? a * 0.5f : a, OU, OV, rare ? 0x83eb : 0x83ea);
    mesh(c, 1, 0x42, A, 1, b, OU, OV, rare ? 0x83ed : 0x83ec);
    mesh(c, 2, 0x46, A, 2, b, OU, OV, -1);
    float saved[3] = {c->color[0], c->color[1], c->color[2]};
    if (rare)
        color(c, 1.0f, 0.65f, 0.4f);
    else
        color(c, 0.2f, 0.5f, 0.7f);
    O_MESH(3, 0x44, 0x82e4);
    color(c, saved[0], saved[1], saved[2]);
    return 1;
}

/* 0x00a4f699 (rare: 0x00a4fa6d) */
static int shining_tail(ctx *c, int rare)
{
    color(c, 1.0f, 1.0f, 1.0f);
    body(c, 2, A, BM, BL, OU, OV, -1, -1);
    float l = wave(c, -4.0f) * 0.7f + 0.3f;
    if (!rare) {
        mesh(c, 0, 0x42, A, 0, l * 0.5f, OU, OV, -1);
        mesh(c, 2, 0x42, A, 2, l * 0.5f, OU, OV, -1);
        mesh(c, 3, 0x42, A, 3, l * 0.5f, OU, OV, -1);
        mesh(c, 0, 0x42, A, 0, l, OU, OV, 0x8430);
        mesh(c, 1, 0x42, A, 1, l, OU, OV, 0x8433);
        mesh(c, 2, 0x42, A, 2, l, OU, OV, 0x8431);
        mesh(c, 3, 0x42, A, 3, l, OU, OV, 0x8432);
        color(c, 0.75f, 0.9f, 0.8f);
        O_MESH(1, 0x44, 0x82e3);
    } else {
        mesh(c, 1, 0x42, A, 1, l * 0.25f, OU, OV, -1);
        mesh(c, 2, 0x42, A, 2, l * 0.25f, OU, OV, -1);
        mesh(c, 3, 0x42, A, 3, l * 0.25f, OU, OV, -1);
        mesh(c, 0, 0x42, A, 0, l, OU, OV, 0x8437);
        mesh(c, 1, 0x42, A, 1, l, OU, OV, 0x8435);
        mesh(c, 2, 0x42, A, 2, l, OU, OV, 0x8434);
        mesh(c, 2, 0x42, A, 2, l, OU, OV, 0x8434);
        mesh(c, 3, 0x42, A, 3, l, OU, OV, 0x8436);
        color(c, 1.0f, 0.7f, 0.55f);
        O_MESH(0, 0x44, 0x82e3);
    }
    return 1;
}

/* 0x00a527d1 (rare: 0x00a52da0) */
static int ur(ctx *c, int rare)
{
    color(c, 1.0f, 1.0f, 1.0f);
    static const int32_t plain[6] = {0, 1, 2, 4, 5, 6}, plain_rare[7] = {0, 1, 2, 4, 5, 6, 7};
    for (int32_t i = 0; i < (rare ? 7 : 6); ++i)
        O_MESH(rare ? plain_rare[i] : plain[i], 2, -1);
    float l = wave(c, -4.0f) * 0.9f + 0.3f;
    int32_t second = rare ? 7 : 6;
    mesh(c, 1, 0x42, A, 1, l, OU, OV, rare ? 0x848c : 0x848a);
    mesh(c, second, 0x42, A, second, l, OU, OV, rare ? 0x848d : 0x848b);
    color(c, 0.3f, 0.45f, 0.63f);
    mesh(c, 0, 0x44, A, 0, BL, OU, OV, -1);
    mesh(c, second, 0x44, A, second, BL, OU, OV, -1);
    float d = rare ? 0.2f : 0.1f;
    color(c, d, d, d);
    int32_t third = rare ? 6 : 5;
    mesh(c, third, 0x44, A, third, BL, OU, OV, -1);
    float a = wave(c, -4.0f) * 0.4f + 0.6f;
    float g = rare ? 0.4f : 0.6f;
    color(c, g, g, g);
    float s = (float)(cvtt(c->in->world_time) % 10000) * 0.0003f;
    mesh(c, 3, 0x44, rare ? A : a, 3, rare ? a : BL, s, s, rare ? 0x800c : 0x8239);
    return 1;
}

/* 0x00a54b97 (rare: 0x00a54e60) */
static int leviathan(ctx *c, int rare)
{
    color(c, 1.0f, 1.0f, 1.0f);
    body(c, 2, A, BM, BL, OU, OV, -1, -1);
    if (!rare) {
        color(c, 0.3f, 0.6f, 0.9f);
        O_MESH(0, 0x44, -1);
        color(c, 0.1f, 0.3f, 0.65f);
        mesh(c, 1, 0x42, A, 1, wave(c, -4.0f) * 0.7f + 0.3f, OU, OV, -1);
        color(c, 0.1f, 0.3f, 0.65f);
        O_MESH(1, 0x46, -1);
    } else {
        color(c, 0.6f, 0.4f, 0.3f);
        O_MESH(0, 0x46, -1);
        color(c, 1.0f, 1.0f, 1.0f);
        mesh(c, 0, 0x42, A, 0, wave(c, -4.0f) * 0.6f + 0.4f, OU, OV, 0x853d);
        color(c, 0.7f, 0.7f, 0.6f);
        mesh(c, 1, 0x42, A, 1, wave(c, -4.0f) * 0.6f + 0.4f, OU, OV, -1);
        color(c, 0.4f, 0.3f, 0.2f);
        mesh(c, 1, 0x46, A, 1, BL, OU, OV, -1);
    }
    return 1;
}

/* 0x00a551fe (rare: 0x00a55883) */
static int tauros(ctx *c, int rare)
{
    float saved[3] = {c->color[0], c->color[1], c->color[2]};
    O_MESH(2, 2, -1);
    float l = rare ? wave(c, -3.0f) * 0.3f : wave(c, -3.0f) * 0.7f + 0.6f;
    mesh(c, 2, 0x42, A, 2, l, OU, OV, rare ? 0x8544 : -1);
    l = wave(c, -3.0f) * 1.2f + 0.5f;
    mesh(c, 2, 0x42, A, 2, l, OU, OV, rare ? 0x853f : 0x853e);
    O_MESH(4, 2, -1);
    l = rare ? wave(c, -2.0f) * 0.2f + 0.8f : wave(c, -2.0f) * 0.4f + 0.6f;
    mesh(c, 4, 0x42, A, 4, l, OU, OV, rare ? 0x8543 : 0x8541);
    if (rare)
        color(c, 0.8f, 0.6f, 0.2f);
    else
        color(c, 0.7f, 0.4f, 0.2f);
    O_MESH(4, 0x44, 0x82e3);
    color(c, saved[0], saved[1], saved[2]);
    O_MESH(1, 2, -1);
    if (rare)
        color(c, 0.6f, 0.35f, 0.12f);
    else
        color(c, 0.5f, 0.2f, 0.1f);
    O_MESH(1, 0x44, 0x82e3);
    color(c, saved[0], saved[1], saved[2]);
    O_MESH(3, 2, -1);
    float u = (float)(-cvtt(c->in->world_time) % 0xc80) * 0.0003125f;
    mesh(c, 3, 0x42, A, 3, BL, u, OV, 0x8531);
    O_MESH(0, 2, -1);
    l = wave(c, -2.0f) * 0.6f + 0.4f;
    mesh(c, 0, 0x42, A, 0, l, OU, OV, rare ? 0x8542 : 0x8540);
    color(c, 0.7f, 0.4f, 0.2f);
    O_MESH(0, 0x44, 0x82e3);
    color(c, saved[0], saved[1], saved[2]);
    return 1;
}

/* 0x00a5aee8 */
static int divine_horse(ctx *c)
{
    color(c, 1.0f, 1.0f, 1.0f);
    body(c, 2, A, BM, BL, OU, OV, O68, -1);
    float l = wave(c, -4.0f) * 0.2f + 0.4f;
    mesh(c, 2, 2, A, 2, l, OU, OV, -1);
    mesh(c, 3, 2, A, 3, l * 0.5f, OU, OV, -1);
    l = wave(c, -4.0f) * 0.7f + 0.3f;
    mesh(c, 0, 0x42, A, 0, l, OU, OV, 0x8530);
    mesh(c, 1, 0x42, A, 1, l * 0.5f, OU, OV, -1);
    float u = wave(c, 1.0f);
    mesh(c, 0, 2, A, 0, BL, u, OV, 0x8531);
    color(c, 0.3f, 0.3f, 0.3f);
    mesh(c, 3, 0x44, A, 3, BL, OU, OV, -1);
    color(c, 1.0f, 1.0f, 1.0f);
    shadow(c, 1, 3);
    return 1;
}

/* 0x00a53c44 / 0x00a540ba / 0x00a54490: the ride-state transformations */
static int giant(ctx *c, int which)
{
    float a4 = c->in->object_a4;
    color(c, 1.0f, 1.0f, 1.0f);
    O_MESH(0, 2, -1);
    O_MESH(1, 2, -1);
    O_MESH(2, 2, -1);
    if (which == 3)
        O_MESH(3, 2, -1);
    float l = wave(c, -4.0f) * 0.6f + 0.4f;
    if (which == 1) {
        mesh(c, 2, 0x42, A, 2, l, OU, OV, 0x84e8);
        color(c, 0.3f, 0.1f, 1.0f);
        mesh(c, 3, 0x42, A, 3, a4, OU, OV, -1);
        color(c, 1.0f, 1.0f, 1.0f);
        mesh(c, 4, 0x42, A, 4, a4, OU, OV, -1);
        color(c, 0.8f, 0.7f, 0.45f);
        O_MESH(0, 0x44, 0x7f1f);
        color(c, 0.2f, 0.1f, 0.1f);
        O_MESH(1, 0x44, 0x7f1f);
    } else if (which == 2) {
        mesh(c, 2, 0x42, A, 2, l, OU, OV, 0x84e9);
        color(c, 0.7f, 0.5f, 0.5f);
        mesh(c, 3, 0x42, A, 3, a4, OU, OV, -1);
        color(c, 0.8f, 0.7f, 0.45f);
        O_MESH(0, 0x44, 0x7f1f);
        color(c, 0.2f, 0.1f, 0.1f);
        O_MESH(1, 0x44, 0x7f1f);
    } else {
        mesh(c, 2, 0x42, A, 2, l, OU, OV, 0x84ea);
        mesh(c, 3, 0x42, A, 3, l, OU, OV, 0x84eb);
        color(c, 1.0f, 1.0f, 0.2f);
        mesh(c, 4, 0x42, A, 4, a4, OU, OV, -1);
        color(c, 1.0f, 1.0f, 1.0f);
        mesh(c, 5, 0x42, A, 5, a4, OU, OV, -1);
        color(c, 0.2f, 0.1f, 0.1f);
        O_MESH(0, 0x44, 0x7f1f);
        color(c, 0.5f, 0.3f, 0.3f);
        O_MESH(1, 0x44, 0x7f1f);
    }
    return 1;
}

int mu_hp_mount_after_known(int32_t type)
{
    switch (type) {
    case 0x410: case 0x417: case 0x473: case 0x4a8: case 0x4a9: case 0x4aa: case 0x4ab: case 0x671:
    case 0x69a: case 0x69b: case 0x6cb: case 0x6cc: case 0x6f4: case 0x6f5: case 0x736: case 0x737:
    case 0x749: case 0x74a: case 0x77c: case 0x77d: case 0x753: case 0x73f: case 0x740: case 0x741:
        return 1;
    default:
        return 0;
    }
}

int mu_hp_mount_after(mu_helpers *h, const mu_hp_object *o, const mu_hp_after_inputs *in,
                      const mu_hp_after_host *host, mu_hp_after_call *out, int32_t capacity, int32_t *count)
{
    ctx c;
    memset(&c, 0, sizeof c);
    c.h = h;
    c.o = o;
    c.in = in;
    c.host = host;
    c.out = out;
    c.capacity = capacity;
    c.color[0] = in->color[0];
    c.color[1] = in->color[1];
    c.color[2] = in->color[2];
    c.m94 = in->model_94;
    int r;
    switch (o->type) {
    case 0x410: r = dark_horse(&c); break;
    case 0x417: r = 0; break;                       /* 0x00a2f501 */
    case 0x473: r = dinorant(&c); break;
    case 0x4a8: case 0x4a9: case 0x4aa: case 0x4ab: r = fenrir(&c); break;
    case 0x671: r = ghost_horse(&c); break;
    case 0x69a: case 0x69b: r = ice_dragon(&c, o->type == 0x69b); break;
    case 0x6cb: case 0x6cc: r = pierce_lion(&c, o->type == 0x6cc); break;
    case 0x6f4: case 0x6f5: r = shining_tail(&c, o->type == 0x6f5); break;
    case 0x736: case 0x737: r = ur(&c, o->type == 0x737); break;
    case 0x749: case 0x74a: r = leviathan(&c, o->type == 0x74a); break;
    case 0x77c: case 0x77d: r = tauros(&c, o->type == 0x77d); break;
    case 0x753: r = divine_horse(&c); break;
    case 0x73f: r = giant(&c, 1); break;
    case 0x740: r = giant(&c, 2); break;
    case 0x741: r = giant(&c, 3); break;
    default: r = -1; break;
    }
    if (count)
        *count = c.n;
    return r;
}
