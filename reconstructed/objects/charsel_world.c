/* The character-select scene's world handler CGMCharacterScene_Ex (NATIVE-CHARSEL-002). See charsel_world.h
 * and docs/research/client-character-select.md section 9. Binary32 expressions keep the client's operation
 * order (built with -ffp-contract=off). */
#include "charsel_world.h"

#include <math.h>
#include <string.h>

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

/* cvttss2si: out-of-range values give the integer indefinite 0x80000000 */
static int32_t trunc_i32(float v)
{
    if (!(v > -2147483904.0f && v < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)v;
}

static void set3(float v[3], float x, float y, float z)
{
    v[0] = x;
    v[1] = y;
    v[2] = z;
}

/* ---- slot 0x2c 0x00daa2b2 ---- */

/* 0x00daa47c..: constants 0x01aa73cc, 0x01a7fb1c, 0x01aa73c8, 0x01a7e93c, 0x01a7fca4 (as charsel.c) */
static const float marker_yaw[MU_CSW_MARKERS] = {115.0f, 90.0f, 75.0f, 60.0f, 35.0f};

void mu_csw_create(uint8_t *o, int32_t index, mu_csw_scene *scene, mu_obj_log *log)
{
    mu_obj_set_i32(o, 0x64, 0);
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 0x0d: case 0x0e: case 0x0f: case 0x10: case 0x11: {
        const int32_t k = t - 0x0d;
        if (scene) {
            memcpy(scene->position[k], o + MU_OBJF_POSITION, 12);
            set3(scene->angle[k], 0.0f, 0.0f, marker_yaw[k]);
        }
        arg(event(log, MU_OBJ_CALL_SET_CHARACTER_POSITION, index), (uint32_t)k);
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    }
    case 0x26: case 0x27: case 0x28: case 0x36: case 0x37: case 0x38: case 0x39: case 0x45: case 0x50:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    case 0x3c: case 0x3d:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -428.571442f);   /* 0x01aa5ad4 = 0xc3d64925 */
        break;
    default:
        break;
    }
}

/* ---- slot 0x30 0x00daa82b ---- */

int mu_csw_move(uint8_t *o, int32_t index, mu_obj_rand_fn rnd, void *c, mu_obj_log *log)
{
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x18:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.02f);
        return 1;
    case 0x19: case 0x1a:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.03f);
        return 1;
    case 0x49: {
        /* 0x00daa923: rand() % 4 (and 0x80000003 with the sign fix-up) + 3, times 0.1 */
        float l = (float)(rem_i32(rnd ? rnd(c) : 0, 4) + 3);
        l = l * 0.1f;
        float light[3] = {l * 0.2f, l * 0.6f, l};
        mu_obj_event *e = event(log, MU_OBJ_CALL_ADD_LIGHT, index);
        arg_f(e, mu_obj_f32(o, MU_OBJF_POSITION));
        arg_f(e, mu_obj_f32(o, MU_OBJF_POSITION + 4));
        arg_v(e, light);
        arg(e, 3);
        return 1;
    }
    default:
        return 0;
    }
}

/* ---- slot 0x34 0x00daa9dd ---- */

static void bone_point(mu_obj_log *log, int32_t index, int32_t bone, mu_login_bone_fn bone_fn, void *c,
                       float out[3])
{
    const float local[3] = {0.0f, 0.0f, 0.0f};   /* [ebp-0x30], zeroed at entry */
    mu_obj_event *e = event(log, MU_OBJ_CALL_BONE_POSITION, index);
    arg(e, (uint32_t)bone);
    arg_v(e, local);
    arg(e, 0);
    if (bone_fn)
        bone_fn(c, bone, local, out);
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

static void particle(mu_obj_log *log, int32_t index, int32_t bitmap, const float position[3], const float angle[3],
                     const float light[3], int32_t subtype, float scale, int owner)
{
    mu_obj_event *e = event(log, MU_OBJ_CALL_PARTICLE, index);
    arg(e, (uint32_t)bitmap);
    arg_v(e, position);
    arg_v(e, angle);
    arg_v(e, light);
    arg(e, (uint32_t)subtype);
    arg_f(e, scale);
    arg(e, owner ? 1u : 0u);
}

/* CreateEffect wrapper 0x013c0eaa(type, position, angle, light, subtype, the object, -1, 0, 0, 0, 0.0, -1, 0, 0) */
static void effect(mu_obj_log *log, int32_t index, int32_t type, const uint8_t *o, const float light[3],
                   int32_t subtype)
{
    mu_obj_event *e = event(log, MU_OBJ_CALL_EFFECT, index);
    arg(e, (uint32_t)type);
    arg_v(e, (const float *)(const void *)(o + MU_OBJF_POSITION));
    arg_v(e, (const float *)(const void *)(o + MU_OBJF_ANGLE));
    arg_v(e, light);
    arg(e, (uint32_t)subtype);
    arg(e, 1);   /* owner: the object */
}

int mu_csw_visual(const uint8_t *o, int32_t index, float world_time, mu_obj_rand_fn rnd, mu_login_bone_fn bone_fn,
                  mu_login_sin_fn sine, void *c, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float *position = (const float *)(const void *)(o + MU_OBJF_POSITION);
    const float *angle = (const float *)(const void *)(o + MU_OBJF_ANGLE);
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    float p[3] = {0.0f, 0.0f, 0.0f};       /* [ebp-0x20] */
    float light[3] = {0.0f, 0.0f, 0.0f};   /* [ebp-0xc] */
#define R(n) rem_i32(rnd ? rnd(c) : 0, (n))
    switch (t) {
    case 0x1f:   /* 0x00daab4a: three Spark04 glows on bones 6, 7, 8 */
        set3(light, 0.98f, 0.94f, 0.94f);
        bone_point(log, index, 6, bone_fn, c, p);
        sprite(log, index, MU_CSW_BITMAP_SPARK04, p, 1.0f, light, 0.0f);
        set3(light, 0.78f, 0.44f, 0.75f);
        bone_point(log, index, 7, bone_fn, c, p);
        sprite(log, index, MU_CSW_BITMAP_SPARK04, p, 1.2f, light, 0.0f);
        set3(light, 0.58f, 0.07f, 0.56f);
        bone_point(log, index, 8, bone_fn, c, p);
        sprite(log, index, MU_CSW_BITMAP_SPARK04, p, 0.8f, light, 0.0f);
        return 1;
    case 0x26:   /* 0x00daad11 */
        if (R(6) == 0) {
            set3(light, 0.02f, 0.02f, 0.05f);
            particle(log, index, MU_CSW_BITMAP_CLOUDS, position, angle, light, 0x14, scale, 1);
        }
        return 1;
    case 0x27:   /* 0x00daadab */
        if (R(100) == 0) {
            set3(light, 0.2f, 0.2f, 0.5f);
            effect(log, index, MU_CSW_EFFECT_STARDR, o, light, 0);
        }
        return 1;
    case 0x28:   /* 0x00daae49 */
        if (R(200) == 0) {
            set3(light, 0.2f, 0.2f, 0.5f);
            effect(log, index, MU_CSW_EFFECT_STARDR, o, light, 1);
        }
        return 1;
    case 0x36:   /* 0x00daaee9: rand() & 0x80000001 with the sign fix-up */
        if (R(2) == 0) {
            set3(light, 1.0f, 1.0f, 1.0f);
            particle(log, index, MU_CSW_BITMAP_WATERFALL1, position, angle, light, 2, scale, 0);
        }
        return 1;
    case 0x37:   /* 0x00daaf88: every frame, twice the scale */
        set3(light, 1.0f, 1.0f, 1.0f);
        particle(log, index, MU_CSW_BITMAP_WATERFALL3, position, angle, light, 0xe, scale * 2.0f, 0);
        return 1;
    case 0x38:   /* 0x00dab016 */
        if (R(3) == 0) {
            set3(light, 1.0f, 1.0f, 1.0f);
            particle(log, index, MU_CSW_BITMAP_WATERFALL2, position, angle, light, 2, scale, 0);
        }
        return 1;
    case 0x39:   /* 0x00dab0af */
        if (R(100) == 0) {
            set3(light, 1.0f, 1.0f, 1.0f);
            effect(log, index, MU_CSW_EFFECT_SEALEAF, o, light, 3);
        }
        return 1;
    case 0x45:   /* 0x00dab14d */
        if (R(3) == 0) {
            set3(light, 0.4f, 0.6f, 0.7f);
            particle(log, index, MU_CSW_BITMAP_WATER, position, angle, light, 1, 1.0f, 0);
        }
        return 1;
    case 0x49: { /* 0x00dab1df: the lamps */
        bone_point(log, index, 1, bone_fn, c, p);
        light[0] = 0.4f;
        const float x = world_time * 0.7f;
        float s = (float)(sine ? sine(c, (double)x) : sin((double)x));   /* 0x009681bd, fstp dword */
        s = s * 0.2f;
        s = s + 0.3f;
        light[1] = s + 0.5f;
        light[2] = 0.4f;
        float jitter = (float)R(30);
        jitter = jitter / 90.0f;
        /* cvttss2si WorldTime, signed % 3600, times 0.1 */
        const int32_t ticks = trunc_i32(world_time);
        const float rotation = (float)rem_i32(ticks, 3600) * 0.1f;
        sprite(log, index, MU_CSW_BITMAP_SHINY02, p, 1.2f + jitter, light, -rotation);
        set3(light, 0.5f, 1.0f, 0.98f);
        sprite(log, index, MU_CSW_BITMAP_MAGIC_GROUND13, p, 0.2f, light, rotation);
        if (R(3) == 0) {
            set3(light, 1.0f, 1.0f, 1.0f);
            const float size = scale * 1.8f;
            p[2] = p[2] + 15.0f;
            particle(log, index, MU_CSW_BITMAP_FANTA_B, p, angle, light, 0, size, 0);
        }
        return 1;
    }
    case 0x50: { /* 0x00dab431: rand() & 0x80000007 with the sign fix-up */
        if (R(8) == 0) {
            const float smoke[3] = {0.98f, 0.9f, 0.9f};   /* [ebp-0x44] */
            particle(log, index, MU_CSW_BITMAP_SMOKE01, position, angle, smoke, 0x45, scale, 0);
        }
        return 1;
    }
    default:
        return 0;
    }
#undef R
}

/* ---- slots 0x38 0x00dab4d7 and 0x3c 0x00dab5ed ---- */

static int after_type(int32_t t)
{
    switch (t) {
    case 4: case 7: case 8: case 0xc: case 0x18: case 0x19: case 0x1a: case 0x1f: case 0x21: case 0x24:
    case 0x3d: case 0x47:
        return 1;
    default:
        return 0;
    }
}

static void mesh(mu_obj_log *log, int32_t index, const uint8_t *o, int32_t m, int32_t blend)
{
    mu_obj_event *e = event(log, MU_OBJ_CALL_MESH, index);
    arg(e, (uint32_t)m);
    arg(e, 2);
    arg_f(e, mu_obj_f32(o, MU_OBJF_ALPHA));
    arg(e, (uint32_t)blend);
    arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_LIGHT));
    arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_U));
    arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_V));
    arg(e, 0xffffffffu);
}

int mu_csw_custom_render(uint8_t *o, int32_t index, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 0x3c) {
        mesh(log, index, o, 1, mu_obj_i32(o, MU_OBJF_BLEND_MESH));
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        return 1;
    }
    if (after_type(t)) {
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        return 1;
    }
    return 0;
}

int mu_csw_after_render(const uint8_t *o, int32_t index, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 0x3c) {
        mesh(log, index, o, 0, -2);
        return 1;
    }
    if (!after_type(t))
        return 0;
    mu_obj_event *e = event(log, MU_OBJ_CALL_BODY, index);
    arg(e, 2);
    arg_f(e, mu_obj_f32(o, MU_OBJF_ALPHA));
    arg(e, (uint32_t)mu_obj_i32(o, MU_OBJF_BLEND_MESH));
    arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_LIGHT));
    arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_U));
    arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_V));
    arg(e, (uint32_t)mu_obj_i32(o, MU_OBJF_HIDDEN_MESH));
    arg(e, 0xffffffffu);
    return 1;
}
