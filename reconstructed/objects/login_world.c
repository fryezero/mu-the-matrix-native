/* The login scene's world handler CGMLogInScene_Ex (NATIVE-LOGIN-001). See login_world.h and
 * docs/research/client-login-scene.md. Binary32 expressions keep the client's operation order
 * (built with -ffp-contract=off). */
#include "login_world.h"

#include <math.h>
#include <string.h>

#include "../terrain/terrain.h"

static mu_obj_event *event(mu_obj_log *log, uint32_t call, int32_t object)
{
    if (!log)
        return NULL;
    if (log->count >= log->capacity || !log->events) {
        ++log->overflow;
        return NULL;
    }
    mu_obj_event *e = &log->events[log->count++];
    memset(e, 0, sizeof *e);
    e->call = call;
    e->object = object;
    return e;
}

static void arg(mu_obj_event *e, uint32_t value)
{
    if (e && e->count < MU_OBJ_EVENT_ARGS)
        e->args[e->count++] = value;
}

static uint32_t fbits(float v)
{
    uint32_t u;
    memcpy(&u, &v, 4);
    return u;
}

static void arg_f(mu_obj_event *e, float v) { arg(e, fbits(v)); }

static void arg_v(mu_obj_event *e, const float v[3])
{
    for (int k = 0; k < 3; ++k)
        arg_f(e, v[k]);
}

static int32_t rem_i32(int32_t a, int32_t b) { return a % b; }

/* ---- 0x00cfec8d ---- */

float mu_login_pulse(float lo, float hi, float speed, uint32_t now_ms, mu_login_sin_fn sine, void *context)
{
    const float t = (float)(double)now_ms;   /* cvtsi2sd + (eax >> 31) * 2^32, cvtsd2ss */
    const float x = t * speed;
    const double widened = (double)x;        /* 0x009681bd: cvtss2sd, sin, fstp float */
    float s = (float)(sine ? sine(context, widened) : sin(widened));
    s = fabsf(s);                            /* 0x0098a647 */
    float r = 1.0f - s;
    r = r * (hi - lo);
    return r + lo;
}

/* ---- slot 0x2c 0x00e24a4d ---- */

void mu_login_create(uint8_t *o, int32_t index, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 5) {
        /* 0x00966cc4(type, 0)->0x00eaaa44 (action 0), +4 = 0.23 */
        mu_obj_event *e = event(log, MU_OBJ_CALL_PLAY_SPEED, index);
        arg(e, (uint32_t)t);
        arg(e, 0);
        arg_f(e, 0.23f);
    } else if (t == 0x26 || t == 0x36) {
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
    } else {
        mu_obj_set_f32(o, MU_OBJF_RANGE, -428.571442f);   /* 0x01aa5ad4 = 0xc3d64925 */
    }
}

/* ---- slot 0x30 0x00e24acd ---- */

int mu_login_move(uint8_t *o, uint32_t now_ms, mu_login_sin_fn sine, void *context)
{
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 1:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.005f);
        return 1;
    case 0xd:
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, mu_login_pulse(0.2f, 0.6f, 0.001f, now_ms, sine, context));
        return 1;
    default:
        return 0;
    }
}

/* ---- slot 0x34 0x00e24be1 ---- */

static void bone_event(mu_obj_log *log, int32_t index, int32_t bone, const float local[3])
{
    mu_obj_event *e = event(log, MU_OBJ_CALL_BONE_POSITION, index);
    arg(e, (uint32_t)bone);
    arg_v(e, local);
    arg(e, 0);
}

static void sprite(mu_obj_log *log, int32_t index, int32_t bitmap, const float position[3], float scale,
                   const float light[3], float rotation)
{
    mu_obj_event *e = event(log, MU_OBJ_CALL_SPRITE, index);
    arg(e, (uint32_t)bitmap);
    arg_v(e, position);
    arg_f(e, scale);
    arg_v(e, light);
    arg_f(e, rotation);
    arg(e, 1);   /* owner: the object */
    arg(e, 0);
    arg(e, 4);
}

/* One lantern block: z offset rand() % zmod / 20 + zadd, scale rand() % smod / 20 + sadd, the point on `bone`. */
static void lantern_point(int32_t index, int32_t bone, int32_t zmod, float zadd, int32_t smod, float sadd,
                          mu_obj_rand_fn rnd, mu_login_bone_fn bone_fn, void *c, mu_obj_log *log, float out[3],
                          float *scale)
{
    float z = (float)rem_i32(rnd(c), zmod);
    z = z / 20.0f;
    z = z + zadd;
    float s = (float)rem_i32(rnd(c), smod);
    s = s / 20.0f;
    *scale = s + sadd;
    const float local[3] = {0.0f, 0.0f, z};
    bone_event(log, index, bone, local);
    out[0] = out[1] = out[2] = 0.0f;
    if (bone_fn)
        bone_fn(c, bone, local, out);
}

int mu_login_visual(const uint8_t *o, int32_t index, mu_obj_rand_fn rnd, mu_login_bone_fn bone_fn, void *c,
                    mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    float p[3], s;
    if (t == 5) {
        const float warm[3] = {1.0f, 0.3f, 0.0f}, cold[3] = {0.2f, 0.5f, 0.8f};
        /* bone 37 (0x25) */
        lantern_point(index, 0x25, 60, -1.5f, 10, 1.4f, rnd, bone_fn, c, log, p, &s);
        sprite(log, index, MU_LOGIN_BITMAP_SHINY02, p, s, warm, 0.0f);
        sprite(log, index, MU_LOGIN_BITMAP_SHINY02, p, s - 0.3f, warm, 20.0f);
        lantern_point(index, 0x25, 60, -1.5f, 10, 1.0f, rnd, bone_fn, c, log, p, &s);
        sprite(log, index, MU_LOGIN_BITMAP_FLARE01, p, s + 0.3f, warm, 0.0f);
        lantern_point(index, 0x25, 40, -1.0f, 8, 0.4f, rnd, bone_fn, c, log, p, &s);
        sprite(log, index, MU_LOGIN_BITMAP_SHINY02, p, s, warm, 0.0f);
        sprite(log, index, MU_LOGIN_BITMAP_SHINY02, p, s - 0.2f, warm, 90.0f);
        /* bone 98 (0x62) */
        lantern_point(index, 0x62, 60, 2.8f, 10, 2.0f, rnd, bone_fn, c, log, p, &s);
        sprite(log, index, MU_LOGIN_BITMAP_SHINY02, p, s, cold, 0.0f);
        sprite(log, index, MU_LOGIN_BITMAP_SHINY02, p, s - 0.3f, cold, 20.0f);
        lantern_point(index, 0x62, 60, -1.5f, 10, 1.0f, rnd, bone_fn, c, log, p, &s);
        sprite(log, index, MU_LOGIN_BITMAP_FLARE01, p, s + 0.3f, cold, 0.0f);
        lantern_point(index, 0x62, 40, -1.0f, 8, 0.4f, rnd, bone_fn, c, log, p, &s);
        sprite(log, index, MU_LOGIN_BITMAP_SHINY02, p, s, cold, 0.0f);
        sprite(log, index, MU_LOGIN_BITMAP_SHINY02, p, s - 0.2f, cold, 90.0f);
        return 1;
    }
    if (t == 0x26 || t == 0x36) {
        const int mist = t == 0x26;
        const float light[3] = {mist ? 0.02f : 0.22f, mist ? 0.02f : 0.15f, mist ? 0.05f : 0.15f};
        if (rem_i32(rnd(c), mist ? 6 : 2) == 0) {
            mu_obj_event *e = event(log, MU_OBJ_CALL_PARTICLE, index);
            arg(e, mist ? MU_LOGIN_BITMAP_CLOUDS : MU_LOGIN_BITMAP_WATERFALL);
            arg_v(e, (const float *)(const void *)(o + MU_OBJF_POSITION));
            arg_v(e, (const float *)(const void *)(o + MU_OBJF_ANGLE));
            arg_v(e, light);
            arg(e, mist ? 0x14u : 2u);
            arg_f(e, mu_obj_f32(o, MU_OBJF_SCALE));
            arg(e, mist ? 1u : 0u);   /* owner */
        }
        return 1;
    }
    return 0;
}

/* ---- slot 0x38 0x00e254bb ---- */

static void body(mu_obj_log *log, int32_t index, const uint8_t *o)
{
    mu_obj_event *e = event(log, MU_OBJ_CALL_BODY, index);
    arg(e, 2);
    arg_f(e, mu_obj_f32(o, MU_OBJF_ALPHA));
    arg(e, (uint32_t)mu_obj_i32(o, MU_OBJF_BLEND_MESH));
    arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_LIGHT));
    arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_U));
    arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_V));
    arg(e, (uint32_t)mu_obj_i32(o, MU_OBJF_HIDDEN_MESH));
    arg(e, 0xffffffffu);
}

int mu_login_custom_render(uint8_t *o, int32_t index, mu_obj_log *log)
{
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 1: case 2: case 3: case 7: case 8: case 0xa: case 0xb: case 0xc: case 0x12: case 0x13: case 0x14:
    case 0x1d: case 0x37: case 0x38:
        body(log, index, o);
        o[MU_OBJF_AFTER_CHARACTER] = 0;
        return 1;
    case 5: case 0xd:
        body(log, index, o);
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        return 1;
    default:
        return 0;
    }
}

/* ---- slot 0x3c 0x00e25639 ---- */

static void mesh(mu_obj_log *log, int32_t index, int32_t m, uint32_t flags, float alpha, int32_t blend, float light,
                 float u, float v, int32_t texture)
{
    mu_obj_event *e = event(log, MU_OBJ_CALL_MESH, index);
    arg(e, (uint32_t)m);
    arg(e, flags);
    arg_f(e, alpha);
    arg(e, (uint32_t)blend);
    arg_f(e, light);
    arg_f(e, u);
    arg_f(e, v);
    arg(e, (uint32_t)texture);
}

static void color(uint8_t *model, mu_obj_log *log, int32_t index, float r, float g, float b)
{
    mu_obj_set_f32(model, MU_MDL_COLOR, r);
    mu_obj_set_f32(model, MU_MDL_COLOR + 4, g);
    mu_obj_set_f32(model, MU_MDL_COLOR + 8, b);
    mu_obj_event *e = event(log, MU_OBJ_CALL_COLOR, index);
    arg_f(e, r);
    arg_f(e, g);
    arg_f(e, b);
}

int mu_login_after_render(uint8_t *o, uint8_t *model, int32_t index, uint32_t now_ms, mu_login_sin_fn sine,
                          void *context, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
#define A mu_obj_f32(o, MU_OBJF_ALPHA)
#define U mu_obj_f32(o, MU_OBJF_BLEND_U)
#define V mu_obj_f32(o, MU_OBJF_BLEND_V)
#define BM mu_obj_i32(o, MU_OBJF_BLEND_MESH)
#define BL mu_obj_f32(o, MU_OBJF_BLEND_LIGHT)
    if (t == 5) {
        float l = mu_login_pulse(0.2f, 0.6f, 0.0005f, now_ms, sine, context);
        mesh(log, index, 0x12, 2, A, -2, l, U, V, MU_LOGIN_BITMAP_SAILBOAT);
        l = mu_login_pulse(0.2f, 0.5f, 0.0001f, now_ms, sine, context);
        mesh(log, index, 2, 2, A, -2, l, U, V, -1);
        mesh(log, index, 2, 2, A, -2, l, U, V, MU_LOGIN_BITMAP_SAILBOAT);
        mesh(log, index, 2, 0x46, A, BM, l, U, V, MU_LOGIN_BITMAP_CHROME01);
        mu_obj_set_f32(o, MU_OBJF_ALPHA, 0.7f);
        mesh(log, index, 0, 0x42, A, BM, BL, U, V, -1);
        mesh(log, index, 0, 0x44, A, BM, BL, U, V, -1);
        color(model, log, index, 0.8f, 0.7f, 0.3f);
        mesh(log, index, 0x18, 0x42, A, BM, BL, U, V, -1);
        mesh(log, index, 0x18, 0x44, A, BM, BL, U, V, MU_LOGIN_BITMAP_CHROME01);
        mesh(log, index, 0x19, 0x42, A, BM, BL, U * 0.5f, V * 0.5f, -1);
        mesh(log, index, 0x19, 0x44, A, BM, BL, U, V, MU_LOGIN_BITMAP_CHROME01);
        for (int32_t m = 0x1a; m <= 0x1c; ++m) {
            mesh(log, index, m, 0x42, A, BM, BL, U, V, -1);
            mesh(log, index, m, 0x44, A, BM, BL, U, V, MU_LOGIN_BITMAP_CHROME01);
        }
        mu_obj_set_f32(o, MU_OBJF_ALPHA, 1.0f);
        color(model, log, index, 1.0f, 1.0f, 1.0f);
        return 1;
    }
    if (t == 0xd) {
        mesh(log, index, 0x16, 2, A, -2, BL, U, V, -1);
        return 1;
    }
#undef A
#undef U
#undef V
#undef BM
#undef BL
    return 0;
}

/* ---- RenderObjects_AfterCharacter 0x016d6949, world 0x5e ---- */

int mu_login_after_pass(mu_obj_world *w, const mu_obj_render_inputs *in, int32_t *counter, mu_obj_log *log)
{
    if (in->world != MU_LOGIN_WORLD)
        return MU_OBJ_UNSUPPORTED;
    if (counter) {
        if (*counter > 0x28)
            *counter = 0;
        ++*counter;
    }
    for (int32_t i = 0; i < 16; ++i)
        for (int32_t j = 0; j < 16; ++j) {
            const int32_t s = i * 16 + j;
            w->block_visible[s] = (uint8_t)mu_terrain_test_frustum_2d(in->x2d, in->y2d, in->scene_state,
                                                                      (float)(i * 16 + 8), (float)(j * 16 + 8),
                                                                      -180.0f);
            for (int32_t k = w->head[s]; k >= 0; k = w->next[k]) {
                uint8_t *o = w->objects[k];
                if (!w->block_visible[s] && !in->top_view)
                    continue;
                if (!o[MU_OBJF_LIVE] || o[MU_OBJF_AFTER_CHARACTER] != 1)
                    continue;
                const float x = mu_obj_f32(o, MU_OBJF_POSITION) * 0.01f;
                const float y = mu_obj_f32(o, MU_OBJF_POSITION + 4) * 0.01f;
                o[MU_OBJF_VISIBLE] = (uint8_t)mu_terrain_test_frustum_2d(in->x2d, in->y2d, in->scene_state, x, y,
                                                                         mu_obj_f32(o, MU_OBJF_RANGE));
                if (o[MU_OBJF_VISIBLE] || in->top_view) {
                    mu_obj_event *e = event(log, MU_OBJ_CALL_AFTER_DRAW, k);
                    arg(e, 0);
                    arg(e, 0);
                    arg(e, 0);
                }
            }
        }
    return MU_OBJ_OK;
}
