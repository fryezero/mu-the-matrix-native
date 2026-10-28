#include "worlds_g.h"
/* World-object creation, move pass and render pass of the client
 * (NATIVE-OBJECTS-002). See object_render.h and docs/research/client-objects-render.md.
 * Floating-point expressions keep the client's binary32 operation order
 * (built with -ffp-contract=off). */
#include "object_render.h"
#include "worlds_b.h"
#include "login_world.h"
#include "charsel_world.h"

#include <math.h>
#include <string.h>

#include "../record-math/record_math.h"
#include "../terrain/terrain.h"

/* ---- log ---- */

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

static void get_v(const uint8_t *o, uint32_t offset, float v[3])
{
    memcpy(v, o + offset, 12);
}

int32_t mu_obj_msvc_rand(uint32_t *seed)
{
    *seed = *seed * 214013u + 2531011u;
    return (int32_t)((*seed >> 16) & 0x7fff);
}

/* cvttss2si: NaN and out-of-range values give 0x80000000. */
static int32_t trunc_i32(float v)
{
    if (!(v > -2147483904.0f && v < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)v;
}

/* C remainder of a 32-bit signed division (idiv), with the INT32_MIN / -1 trap left out. */
static int32_t rem_i32(int32_t a, int32_t b) { return a % b; }

/* ---- 1. RequestTerrainLight ---- */

void mu_obj_terrain_light(const float *grid, int32_t scene_state, uint8_t terrain_ready, float x, float y,
                          float out[3])
{
    if (scene_state == 1 || scene_state == 2 || scene_state == 4 || !terrain_ready || !grid) {
        out[0] = out[1] = out[2] = 0.0f;
        return;
    }
    x = x / 100.0f;
    y = y / 100.0f;
    const int32_t xi = trunc_i32(x), yi = trunc_i32(y);
    if (xi < 0 || yi < 0 || xi > 0xfe || yi > 0xfe) {
        out[0] = out[1] = out[2] = 0.0f;
        return;
    }
    const int32_t i1 = (yi << 8) + xi, i2 = (yi << 8) + xi + 1;
    const int32_t i3 = ((yi + 1) << 8) + xi + 1, i4 = ((yi + 1) << 8) + xi;
    const float fx = x - (float)xi, fy = y - (float)yi;
    for (int c = 0; c < 3; ++c) {
        float a = grid[3 * i4 + c] - grid[3 * i1 + c];
        a = a * fy;
        a = a + grid[3 * i1 + c];
        float b = grid[3 * i3 + c] - grid[3 * i2 + c];
        b = b * fy;
        b = b + grid[3 * i2 + c];
        float r = b - a;
        r = r * fx;
        out[c] = r + a;
    }
}

/* ---- 2. body light 0x017ec3d8 ---- */

void mu_obj_body_light(uint8_t *o, uint8_t *b, const mu_obj_light_inputs *in)
{
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (type == 0x7dc) {
        for (int k = 0; k < 3; ++k)
            mu_obj_set_f32(b, MU_MDL_COLOR + 4u * (uint32_t)k, 0.6f);
        return;
    }
    if (type == 0x444) {
        const float a = in->time * 0.003f;
        const float s = in->sine ? in->sine(in->context, a) : sinf(a);
        float v = s * 0.5f;
        v = v + 0.5f;
        for (int k = 0; k < 3; ++k)
            mu_obj_set_f32(b, MU_MDL_COLOR + 4u * (uint32_t)k, v);
        return;
    }
    b[MU_MDL_LIGHTING] = o[MU_OBJF_LIGHT_ENABLE];
    const float x = mu_obj_f32(o, MU_OBJF_POSITION), y = mu_obj_f32(o, MU_OBJF_POSITION + 4);
    float light[3];
    mu_obj_terrain_light(o[MU_OBJF_LIGHT_DYNAMIC] ? in->frame : in->primary, in->scene_state, in->terrain_ready, x, y,
                         light);
    const int copy = o[MU_OBJF_LIGHT_ENABLE] || o[MU_OBJF_LIGHT_FULL];
    if (!copy || !o[MU_OBJF_LIGHT_FULL])
        for (int k = 0; k < 3; ++k)
            light[k] = 0.1f * light[k];
    for (int k = 0; k < 3; ++k)
        mu_obj_set_f32(b, MU_MDL_COLOR + 4u * (uint32_t)k, light[k] + mu_obj_f32(o, MU_OBJF_LIGHT + 4u * (uint32_t)k));
    if (copy)
        memcpy(o + MU_OBJF_LIGHT_COPY, b + MU_MDL_COLOR, 12);
}

/* ---- 3. CreateObject 0x016d8538 ---- */

static void set_v(uint8_t *o, uint32_t offset, float a, float b, float c)
{
    mu_obj_set_f32(o, offset, a);
    mu_obj_set_f32(o, offset + 4, b);
    mu_obj_set_f32(o, offset + 8, c);
}

/* Tormenta Island handler slot 0x2c (0x00e4c6ba); 0x00e54061 accepts world 0x8d. */
static void tormenta_create(uint8_t *o)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t >= 0xb4 && t <= 0xc8)
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
    if (t >= 0x24 && t <= 0x2a)
        o[MU_OBJF_LIGHT_DYNAMIC] = 0;
    switch (t) {
    case 0: case 1:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -100.0f);
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    case 2: case 3: case 4: case 5: case 6: case 7: case 8: case 9:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    case 0x1f: case 0x20:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -1000.0f);
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    case 0x21:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -175.0f);
        break;
    case 0x0c: case 0x1e: case 0x22: case 0x41: case 0x48: case 0x4b: case 0x4c: case 0x4d: case 0x4e: case 0x4f:
    case 0x50: case 0x76: case 0x79: case 0x7a: case 0x7b:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    case 0x7d: case 0x7f:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -150.0f);
        break;
    case 0x27:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -50.0f);
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);   /* falls into the 0x80 case */
        break;
    case 0x80:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        break;
    case 0xc7:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -1500.0f);
        break;
    default:
        break;
    }
}

/* NATIVE-FIDELITY-002: CreateEffect 0x013c0eaa(type, &position, o + 0x164, o + 0xec, sub, 0, -1, 0, 0, 0, 0.0f, -1, 0, 0)
 * as CreateObject's world cases call it (sub 1 in Devias, 0 in Noria); logged as type, position, then the object
 * offsets of the angle and light pointers and the ten constants. */
static void create_effect(mu_obj_log *log, int32_t index, const uint8_t *o, int32_t type, float dy, float dz,
                          uint32_t sub)
{
    mu_obj_event *e = event(log, MU_OBJ_CALL_CREATE_EFFECT, index);
    float p[3];
    get_v(o, MU_OBJF_POSITION, p);
    arg(e, (uint32_t)type);
    arg_f(e, p[0]);
    arg_f(e, p[1] + dy);
    arg_f(e, p[2] + dz);
    const uint32_t rest[12] = {MU_OBJF_ANGLE, MU_OBJF_LIGHT, sub, 0, 0xffffffffu, 0, 0, 0, 0, 0xffffffffu, 0, 0};
    for (int k = 0; k < 12; ++k)
        arg(e, rest[k]);
}

/* CreateEffect with the object's position pointer itself (MoveObject's cases): (type, o + 0x158, o + 0x164, o + 0xec,
 * 0, 0, -1, 0, 0, 0, 0.0f, -1, 0, 0). */
static void create_effect_here(mu_obj_log *log, int32_t index, const uint8_t *o, int32_t type)
{
    mu_obj_event *e = event(log, MU_OBJ_CALL_CREATE_EFFECT, index);
    float p[3];
    get_v(o, MU_OBJF_POSITION, p);
    arg(e, (uint32_t)type);
    arg_v(e, p);
    static const uint32_t rest[12] = {MU_OBJF_ANGLE, MU_OBJF_LIGHT, 0, 0, 0xffffffffu, 0, 0, 0, 0, 0xffffffffu, 0, 0};
    for (int k = 0; k < 12; ++k)
        arg(e, rest[k]);
}

static void register_object(mu_obj_log *log, int32_t index) { arg(event(log, MU_OBJ_CALL_REGISTER, index), 1); }

static void hide_box_160(uint8_t *o)
{
    set_v(o, MU_OBJF_BOX_MAX, 40.0f, 40.0f, 160.0f);
    mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
}

/* CreateObject's own cases of worlds 1, 2, 3, 7, 8 and 0x37 (0x016d8e3a..0x016d99bf) and the default chain's hooks
 * of Kanturu (0x00e74a58, world 0x25) and Elbeland (0x00e30a02, world 0x33). Returns 0 when the world has none of
 * these. */
static int world_create(uint8_t *o, int32_t world, int32_t index, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (world) {
    case 1:   /* Dungeon */
        if (t == 0x3b)
            register_object(log, index);
        else if (t == 0x3c) {
            register_object(log, index);
            hide_box_160(o);
        }
        return 1;
    case 2:   /* Devias */
        switch (t) {
        case 0x16: case 0x19: case 0x28: case 0x2d: case 0x37: case 0x49: register_object(log, index); break;
        case 0x13: case 0x5c: case 0x5d: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0); break;
        case 0x36: case 0x38: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 1); break;
        case 0x4e: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 3); break;
        case 0x5b: register_object(log, index); hide_box_160(o); break;
        case 0x64: mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2); break;
        case 0x7a: case 0x7b: mu_obj_set_f32(o, MU_OBJF_RANGE, -600.0f); break;
        case 0x14: case 0x41: case 0x56: case 0x58: {   /* angle z wrapped to (-360, 360), head angle and +0x17c */
            mu_obj_set_f32(o, MU_OBJF_ANGLE + 8, (float)rem_i32(trunc_i32(mu_obj_f32(o, MU_OBJF_ANGLE + 8)), 360));
            memcpy(o + MU_OBJF_HEAD_ANGLE, o + MU_OBJF_ANGLE, 12);
            memcpy(o + 0x17c, o + MU_OBJF_POSITION, 12);
            break;
        }
        case 0x1a8:
            create_effect(log, index, o, 0x1a8, 0.0f, 360.0f, 1);
            create_effect(log, index, o, 0x1a9, 4.0f, 360.0f, 1);
            create_effect(log, index, o, 0x1aa, 20.0f, 360.0f, 1);
            break;
        default: break;
        }
        return 1;
    case 3:   /* Noria */
        switch (t) {
        case 1: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 1); break;
        case 8: register_object(log, index); break;
        case 9: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 3); break;
        case 0x11: case 0x13: case 0x25: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0); break;
        case 0x12: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 2); break;
        case 0x26: register_object(log, index); mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2); break;
        case 0x1a8:
            create_effect(log, index, o, 0x1a8, 0.0f, 350.0f, 0);
            create_effect(log, index, o, 0x1a9, 4.0f, 350.0f, 0);
            create_effect(log, index, o, 0x1a8, 8.0f, 350.0f, 0);
            create_effect(log, index, o, 0x1a9, 12.0f, 350.0f, 0);
            create_effect(log, index, o, 0x1aa, 20.0f, 350.0f, 0);
            break;
        default: break;
        }
        return 1;
    case 7:   /* Atlans */
        if (t == 0x27) {
            register_object(log, index);
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        }
        return 1;
    case 8:   /* Tarkan */
        switch (t) {
        case 0x4e: register_object(log, index); break;
        case 0x59: o[MU_OBJF_AFTER_CHARACTER] = 1; mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.05f); break;
        case 0x5d: o[MU_OBJF_AFTER_CHARACTER] = 1; break;
        case 0x61: case 0x68: mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2); break;
        default: break;
        }
        return 1;
    case 0x37:
        if (t == 0x56 || t == 0x5a) {
            set_v(o, MU_OBJF_POSITION, 8600.0f, 25000.0f, 5000.0f);
            mu_obj_set_f32(o, MU_OBJF_SCALE, t == 0x5a ? 110.0f : 60.0f);
            set_v(o, MU_OBJF_ANGLE, 0.0f, 0.0f, 0.0f);
        }
        return 1;
    case 0x25:   /* Kanturu: 0x00e74a58 */
        if (t == 0x55 || t == 0x38)
            mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f);
        if (t == 0x20 || t == 0x44 || t == 0x4b || t == 0x5f || t == 0x7c)
            mu_obj_set_f32(o, MU_OBJF_RANGE, -100.0f);
        return 1;
    case 0x33:   /* Elbeland: 0x00e30a02 (its worlds 0x49/0x4a branch asks a runtime singleton; not here) */
        if (t == 0x67)
            register_object(log, index);
        else if (t == 0x8f || t == 0xa5)
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        switch (t) {
        case 0xf: case 0x19: case 0x1b: case 0x2d: case 0x2e: case 0x2f: case 0x30: case 0x35: case 0x62: case 0x6b:
        case 0x73: case 0x7a: case 0x82:
            mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
            break;
        default: break;
        }
        return 1;
    default:
        return 0;
    }
}

int mu_obj_create(const mu_object_record *r, int32_t world, uint8_t *o, int32_t *sector_out, int32_t index,
                  mu_obj_log *log)
{
    if (!r || !o)
        return MU_OBJ_BAD_ARGUMENT;
    const int32_t sx = trunc_i32(r->position[0] / 1600.0f), sy = trunc_i32(r->position[1] / 1600.0f);
    if (sx < 0 || sy < 0 || sx >= 16 || sy >= 16)
        return MU_OBJ_SKIPPED;
    const uint8_t sector = (uint8_t)((sx << 4) + sy);
    if (sector_out)
        *sector_out = sector;
    o[MU_OBJF_LIVE] = 1;                              /* 0x0129f4a5(1) */
    o[MU_OBJF_VISIBLE] = 0;
    o[MU_OBJF_ALPHA_LINEAR] = 0;
    o[MU_OBJF_LIGHT_ENABLE] = r->flag_2c;
    o[MU_OBJF_LIGHT_FULL] = r->flag_2d;
    o[MU_OBJF_LIGHT_DYNAMIC] = r->flag_2e;
    o[MU_OBJF_FLAG_E] = 0;
    o[MU_OBJF_BONE_BUFFER] = 0;
    o[2] = 0;
    mu_obj_set_i32(o, MU_OBJF_TYPE, r->type);
    mu_obj_set_f32(o, MU_OBJF_SCALE, r->scale);
    mu_obj_set_f32(o, MU_OBJF_ALPHA, 1.0f);
    mu_obj_set_f32(o, MU_OBJF_ALPHA_TARGET, 1.0f);
    mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.16f);
    mu_obj_set_f32(o, MU_OBJF_C4, 50.0f);
    mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, r->hidden ? -2 : -1);
    mu_obj_set_f32(o, MU_OBJF_VALUE_E4, r->value_30);
    mu_obj_set_f32(o, MU_OBJF_VALUE_E8, r->value_34);
    mu_obj_set_u16(o, MU_OBJF_ACTION, 0);
    mu_obj_set_u16(o, MU_OBJF_PRIOR_ACTION, 0);
    mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
    mu_obj_set_f32(o, MU_OBJF_PRIOR_FRAME, 0.0f);
    o[MU_OBJF_SECTOR] = sector;
    mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, -1);
    mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, 1.0f);
    mu_obj_set_f32(o, MU_OBJF_BLEND_U, 0.0f);
    mu_obj_set_f32(o, MU_OBJF_BLEND_V, 0.0f);
    /* 0x01295f18 initialises the buff list at +0x358 (not modelled) */
    mu_obj_set_f32(o, MU_OBJF_RANGE, -30.0f);
    mu_obj_set_f32(o, MU_OBJF_TIMER, 0.0f);
    mu_obj_set_i32(o, 0x368, 0);
    o[MU_OBJF_AFTER_CHARACTER] = 0;
    mu_obj_set_i32(o, 0x14, 0);
    mu_obj_set_i32(o, 0x18, -1);
    mu_obj_set_i32(o, 0x1c, -1);
    o[0x28] = 0;
    memcpy(o + MU_OBJF_POSITION, r->position, 12);
    memcpy(o + MU_OBJF_START, r->position, 12);
    memcpy(o + MU_OBJF_ANGLE, r->angle, 12);
    memcpy(o + MU_OBJF_LIGHT, r->vector, 12);
    set_v(o, MU_OBJF_HEAD_ANGLE, 0.0f, 0.0f, 0.0f);
    set_v(o, MU_OBJF_DIRECTION, 0.0f, 0.0f, 0.0f);
    set_v(o, MU_OBJF_BOX_MIN, -40.0f, -40.0f, 0.0f);
    set_v(o, MU_OBJF_BOX_MAX, 40.0f, 40.0f, 80.0f);
    const int32_t t = r->type;
    if (world == 0) {
        switch (t) {
        case 0x50: mu_obj_set_f32(o, MU_OBJF_RANGE, -50.0f); break;
        case 0x75: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 4); break;
        case 0x76: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 8); break;
        case 0x77: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 2); break;
        case 0x7a: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 4); break;
        case 0x69: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 3); break;
        case 0x34: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 1); break;
        case 0x62: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 2); break;
        case 0: case 1: {
            set_v(o, MU_OBJF_BOX_MIN, -150.0f, -150.0f, 0.0f);
            set_v(o, MU_OBJF_BOX_MAX, 150.0f, 150.0f, 500.0f);
            float v = 1.0f / mu_obj_f32(o, MU_OBJF_SCALE);
            mu_obj_set_f32(o, MU_OBJF_VELOCITY, v * 0.4f);
            break;
        }
        case 0x5a: case 0x96:
            mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 1);
            mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.3f);
            break;
        case 0x3b: mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.0f); break;
        case 0x60: case 0x61: mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.3f); break;
        case 0x85: {
            mu_obj_event *e = event(log, MU_OBJ_CALL_REGISTER, index);
            arg(e, 1);
            set_v(o, MU_OBJF_BOX_MAX, 40.0f, 40.0f, 160.0f);
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
            break;
        }
        case 6: case 0x91: case 0x92:
            arg(event(log, MU_OBJ_CALL_REGISTER, index), 1);
            break;
        default:
            break;
        }
        return MU_OBJ_OK;
    }
    if (world == 0x8d) {
        tormenta_create(o);
        return MU_OBJ_OK;
    }
    if (world_create(o, world, index, log))   /* NATIVE-FIDELITY-002 */
        return MU_OBJ_OK;
    if (world == 57 || world == 58) {
        mu_raklion_create(o, index, log);
        return MU_OBJ_OK;
    }
    if (world == 62 || world == 63) {
        if (world == 62) mu_santa_create(o);
        else mu_vulcanus_create(o, world);
        return MU_OBJ_OK;
    }
    if (world == MU_LOGIN_WORLD) {   /* CGMLogInScene_Ex slot 0x2c */
        mu_login_create(o, index, log);
        return MU_OBJ_OK;
    }
    if (world == MU_CSW_WORLD) {     /* CGMCharacterScene_Ex slot 0x2c (NATIVE-CHARSEL-002) */
        mu_csw_create(o, index, NULL, log);
        return MU_OBJ_OK;
    }
    return MU_OBJ_UNSUPPORTED;
}

/* ---- 4. MoveObjects 0x016d82c7 ---- */

void mu_obj_move_pass(mu_obj_world *w, int32_t world, mu_obj_answer_fn handler_moves, void *context, mu_obj_log *log)
{
    (void)world;
    event(log, MU_OBJ_CALL_MOVE_PRE, -1);
    for (int32_t i = 0; i < 16; ++i)
        for (int32_t j = 0; j < 16; ++j) {
            const int32_t s = i * 16 + j;
            if (w->block_visible[s]) {
                for (int32_t k = w->head[s]; k >= 0; k = w->next[k]) {
                    uint8_t *o = w->objects[k];
                    if (o[MU_OBJF_LIVE] && o[MU_OBJF_VISIBLE]) {
                        event(log, MU_OBJ_CALL_MOVE_OBJECT, k);
                        event(log, MU_OBJ_CALL_MOVE_WORLD10, k);
                        event(log, MU_OBJ_CALL_MOVE_EVENT, k);
                    }
                }
            } else {
                for (int32_t k = w->head[s]; k >= 0; k = w->next[k]) {
                    uint8_t *o = w->objects[k];
                    if (handler_moves && handler_moves(context, k))
                        event(log, MU_OBJ_CALL_MOVE_OBJECT, k);
                    if (o[MU_OBJF_LIVE])
                        event(log, MU_OBJ_CALL_MOVE_EVENT, k);
                    o[MU_OBJF_VISIBLE] = 0;
                }
            }
        }
}

uint8_t mu_obj_handler_moves(const uint8_t *o, int32_t world, const float *x2d, const float *y2d, int32_t scene_state)
{
    if (world != 0x8d)
        return 0;   /* base class slot 0x1c 0x00d5cbbc */
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t != 0x1f && t != 0x20)
        return 0;
    const float x = mu_obj_f32(o, MU_OBJF_POSITION) * 0.01f, y = mu_obj_f32(o, MU_OBJF_POSITION + 4) * 0.01f;
    return (uint8_t)mu_terrain_test_frustum_2d(x2d, y2d, scene_state, x, y, mu_obj_f32(o, MU_OBJF_RANGE));
}

/* ---- 5. MoveObject 0x017ff238 ---- */

void mu_obj_alpha_step(uint8_t *o)
{
    float alpha = mu_obj_f32(o, MU_OBJF_ALPHA);
    const float target = mu_obj_f32(o, MU_OBJF_ALPHA_TARGET);
    if (o[MU_OBJF_ALPHA_LINEAR]) {
        if (target > alpha) {
            alpha = alpha + 0.05f;
            if (alpha > 1.0f)
                alpha = 1.0f;
        } else if (alpha > target) {
            alpha = alpha - 0.05f;
            if (0.0f > alpha)
                alpha = 0.0f;
        }
    } else {
        float d = target - alpha;
        d = d * mu_obj_f32(o, MU_OBJF_ALPHA_RATE);
        alpha = d + alpha;
    }
    mu_obj_set_f32(o, MU_OBJF_ALPHA, alpha);
    if (mu_obj_f32(o, MU_OBJF_BLEND_LIGHT) > alpha)
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, alpha);
}

static double trig_sin(double x) { return sin(x); }
static double trig_cos(double x) { return cos(x); }

void mu_obj_create_fire(int32_t type, const uint8_t *o, int32_t index, float x, float y, float z,
                        mu_obj_rand_fn rand_fn, void *context, mu_obj_log *log)
{
    float matrix[12], p[3] = {x, y, z}, position[3], angle[3], light[3];
    get_v(o, MU_OBJF_ANGLE, angle);
    mu_angle_matrix_using(angle, matrix, trig_sin, trig_cos);
    mu_vector_rotate(p, matrix, position);
    for (int k = 0; k < 3; ++k)
        position[k] = position[k] + mu_obj_f32(o, MU_OBJF_POSITION + 4u * (uint32_t)k);
    for (int k = 0; k < 3; ++k) {
        const int32_t r = rem_i32(rand_fn(context), 16) - 8;
        position[k] = (float)r + position[k];
    }
    if (type == 0) {
        float l = (float)(rem_i32(rand_fn(context), 6) + 6);
        l = l * 0.1f;
        light[0] = l;
        light[1] = l * 0.6f;
        light[2] = l * 0.4f;
        if (rem_i32(rand_fn(context), 2) == 0) {
            const int32_t sub = rem_i32(rand_fn(context), 4);
            mu_obj_event *e = event(log, MU_OBJ_CALL_PARTICLE, index);
            arg(e, MU_OBJ_BITMAP_FIRE);
            arg_v(e, position);
            arg_v(e, angle);
            arg_v(e, light);
            arg(e, (uint32_t)sub);
            arg_f(e, 1.0f);
        }
        mu_obj_event *e = event(log, MU_OBJ_CALL_ADD_LIGHT, index);
        arg_f(e, position[0]);
        arg_f(e, position[1]);
        arg_v(e, light);
        arg(e, 4);
    } else if (type == 1 || type == 2) {
        if (rem_i32(rand_fn(context), 2) == 0) {
            float own[3];
            get_v(o, MU_OBJF_LIGHT, own);
            mu_obj_event *e = event(log, MU_OBJ_CALL_PARTICLE, index);
            arg(e, MU_OBJ_BITMAP_SMOKE);
            arg_v(e, position);
            arg_v(e, angle);
            arg_v(e, own);
            arg(e, type == 1 ? 0u : 2u);
            arg_f(e, 1.0f);
        }
    }
}

static void add_light(mu_obj_log *log, int32_t index, const uint8_t *o, const float light[3], int32_t range)
{
    mu_obj_event *e = event(log, MU_OBJ_CALL_ADD_LIGHT, index);
    arg_f(e, mu_obj_f32(o, MU_OBJF_POSITION));
    arg_f(e, mu_obj_f32(o, MU_OBJF_POSITION + 4));
    arg_v(e, light);
    arg(e, (uint32_t)range);
}

static void lorencia_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    mu_obj_rand_fn rnd = in->rand_fn;
    void *c = in->context;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x32: mu_obj_create_fire(0, o, index, 0.0f, 0.0f, 200.0f, rnd, c, log); break;
    case 0x33: mu_obj_create_fire(0, o, index, 0.0f, -30.0f, 60.0f, rnd, c, log); break;
    case 0x34:
        mu_obj_create_fire(0, o, index, 0.0f, 0.0f, 60.0f, rnd, c, log);
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, (float)(rem_i32(rnd(c), 6) + 4) * 0.1f);
        break;
    case 0x37:
        mu_obj_create_fire(0, o, index, -150.0f, -150.0f, 140.0f, rnd, c, log);
        mu_obj_create_fire(0, o, index, 150.0f, -150.0f, 140.0f, rnd, c, log);
        break;
    case 0x50:
        mu_obj_create_fire(0, o, index, 90.0f, -200.0f, 30.0f, rnd, c, log);
        mu_obj_create_fire(0, o, index, 90.0f, 200.0f, 30.0f, rnd, c, log);
        break;
    case 0x5a: {
        float l = (float)(rem_i32(rnd(c), 2) + 6);
        l = l * 0.1f;
        const float light[3] = {l, l * 0.8f, l * 0.6f};
        add_light(log, index, o, light, 3);
        break;
    }
    case 0x96: {
        float l = (float)(rem_i32(rnd(c), 4) + 3);
        l = l * 0.1f;
        const float light[3] = {l, l * 0.6f, l * 0.2f};
        add_light(log, index, o, light, 3);
        break;
    }
    case 0x75: case 0x7a:
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, (float)(rem_i32(rnd(c), 4) + 4) * 0.1f);
        break;
    case 0x76: case 0x77: {
        const int32_t t = trunc_i32(in->time);
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, (float)rem_i32((int32_t)(0u - (uint32_t)t), 1000) * 0.001f);
        break;
    }
    case 0x82: case 0x83: case 0x84:
        mu_obj_create_fire(mu_obj_i32(o, MU_OBJF_TYPE) - 0x82, o, index, 0.0f, 0.0f, 0.0f, rnd, c, log);
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    default:   /* 0x61 fills a local vector and returns */
        break;
    }
}

/* NATIVE-FIDELITY-002: (float)(t % 1000) * 0.001 and its variants on the clock 0x06fce370 (cvttss2si, idiv). */
static float clock_mod_1000(float time, int negate_first)
{
    const int32_t t = trunc_i32(time);
    return (float)rem_i32(negate_first ? (int32_t)(0u - (uint32_t)t) : t, 1000) * 0.001f;
}

static float wave_light(float time, float rate, float amplitude)   /* 0x009681bd sin, fstp dword */
{
    const float s = (float)sin((double)(time * rate));
    return s * amplitude + 0.5f;
}

static void particle_here(mu_obj_log *log, int32_t index, const uint8_t *o, uint32_t bitmap, const float position[3],
                          const float light[3], uint32_t sub, float scale)
{
    float angle[3];
    get_v(o, MU_OBJF_ANGLE, angle);
    mu_obj_event *e = event(log, MU_OBJ_CALL_PARTICLE, index);
    arg(e, bitmap);
    arg_v(e, position);
    arg_v(e, angle);
    arg_v(e, light);
    arg(e, sub);
    arg_f(e, scale);
}

static float sine_f(float time, float rate) { return (float)sin((double)(time * rate)); }   /* 0x009681bd */

static void sound_event(mu_obj_log *log, int32_t index, uint32_t id)
{
    mu_obj_event *e = event(log, MU_OBJ_CALL_SOUND, index);
    arg(e, id);
    arg(e, 0);
    arg(e, 0);
}

/* (rand() % 4 + 3) * 0.1 */
static float flicker(mu_obj_rand_fn rnd, void *c) { return (float)(rem_i32(rnd(c), 4) + 3) * 0.1f; }

/* The default chain's move hooks: Kanturu 0x00e74ae0 (worlds 0x25 and 0x28) and Aida 0x00d6202f (0x21, 0x36), and
 * the Karutan handler's slot 0x30 0x00e13a9e (0x50, 0x51, through the world manager). */
static int hook_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    mu_obj_rand_fn rnd = in->rand_fn;
    void *c = in->context;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE), w = in->world;
    if (w == 0x21 || w == 0x36) {   /* Aida */
        switch (t) {
        case 0x19: case 0x1c: mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.015f); break;
        case 0x1e: case 0x47: {
            const float k = (float)rem_i32(rnd(c), 5) * 0.01f;
            const float light[3] = {t == 0x1e ? k + 0.4f : k + 0.9f, t == 0x1e ? k + 0.6f : k + 0.2f,
                                    t == 0x1e ? k + 0.4f : k + 0.2f};
            add_light(log, index, o, light, 2);
            break;
        }
        case 0x29: mu_obj_set_f32(o, MU_OBJF_ALPHA, 0.5f); break;
        case 0x38: case 0x39: case 0x3a: case 0x3b: case 0x3e: case 0x3f: case 0x43: case 0x46:
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
            break;
        case 0x40: mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.05f); break;
        default: break;
        }
        sound_event(log, index, 0x248);
        return 1;
    }
    if (w == 0x25 || w == 0x28) {   /* Kanturu */
        switch (t) {
        case 0x3b: case 0x3e: case 0x51: case 0x52: case 0x53: case 0x6b: case 0x6c:
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
            break;
        case 0x2c: mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.02f); break;
        case 0x2e:
            mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.01f);
            mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, sine_f(in->time, 0.0015f) * 0.8f + 1.0f);
            sound_event(log, index, 0x26a);
            break;
        case 0x3c: case 0x3d: {
            const float l = flicker(rnd, c);
            const float light[3] = {t == 0x3c ? l * 0.9f : l, t == 0x3c ? l * 0.2f : l * 0.6f,
                                    t == 0x3c ? l * 0.1f : l * 0.2f};
            add_light(log, index, o, light, 3);
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
            break;
        }
        case 0x46: {
            mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.04f);
            const float l = sine_f(in->time, 0.002f) * 0.45f + 0.55f;
            const float light[3] = {l * 1.4f, l * 0.7f, l * 0.4f};
            add_light(log, index, o, light, 4);
            break;
        }
        case 0x4c: case 0x60: mu_obj_set_f32(o, MU_OBJF_ALPHA, 0.5f); break;
        case 0x4d: {
            const int32_t tt = trunc_i32(in->time);
            mu_obj_set_f32(o, MU_OBJF_BLEND_V, (float)rem_i32((int32_t)(0u - (uint32_t)tt), 10000) * 0.0002f);
            sound_event(log, index, 0x268);
            break;
        }
        case 0x5a: mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.04f); break;
        case 0x5c: sound_event(log, index, 0x269); break;
        case 0x61: {
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
            float timer = mu_obj_f32(o, MU_OBJF_TIMER) + 0.1f;
            mu_obj_set_f32(o, MU_OBJF_TIMER, timer);
            if (timer > 10.0f)
                mu_obj_set_f32(o, MU_OBJF_TIMER, 0.0f);
            if (mu_obj_f32(o, MU_OBJF_TIMER) > 5.0f) {
                float p[3], light[3];
                get_v(o, MU_OBJF_POSITION, p);
                get_v(o, MU_OBJF_LIGHT, light);
                particle_here(log, index, o, 0x7fcd, p, light, 5, 1.0f);
            }
            break;
        }
        case 0x62: sound_event(log, index, 0x26b); break;
        case 0x66: mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, sine_f(in->time, 0.001f) + 1.0f); break;
        default: break;
        }
        sound_event(log, index, 0x26c);
        return 1;
    }
    if (w == 0x50 || w == 0x51) {   /* Karutan handler slot 0x30 */
        switch (t) {
        case 0x71: {
            const float l = flicker(rnd, c);
            const float light[3] = {l, l * 0.6f, l * 0.2f};
            add_light(log, index, o, light, 3);
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
            break;
        }
        case 0x72: case 0x73: case 0x74: case 0x76: mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2); break;
        case 0x87:
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
            sound_event(log, index, 0x5a5);
            break;
        default: break;
        }
        return 1;
    }
    return 0;
}

/* MoveObject's own cases of worlds 1, 3, 4 and 7 (0x017ffe04..0x01800bf3). Returns 0 for other worlds. */
static int world_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    mu_obj_rand_fn rnd = in->rand_fn;
    void *c = in->context;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (in->world) {
    case 1:   /* Dungeon */
        switch (t) {
        case 0x34:
            if (rem_i32(rnd(c), 3) == 0)
                create_effect_here(log, index, o, 0x1a5);
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
            break;
        case 0x16: case 0x17: case 0x18:
            arg(event(log, MU_OBJ_CALL_MODEL_STREAM, index), 1);   /* model +0x94 = 1 */
            mu_obj_set_f32(o, MU_OBJF_BLEND_V, -(float)rem_i32(trunc_i32(in->time), 1000) * 0.001f);
            break;
        case 0x27: case 0x28: case 0x33: mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2); break;
        case 0x29: mu_obj_create_fire(0, o, index, 0.0f, -30.0f, 240.0f, rnd, c, log); break;
        case 0x2a: mu_obj_create_fire(0, o, index, 0.0f, 0.0f, 190.0f, rnd, c, log); break;
        case 0x3d:
            mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 4);
            mu_obj_set_f32(o, MU_OBJF_BLEND_U, clock_mod_1000(in->time, 1));
            break;
        default: break;
        }
        return 1;
    case 3:   /* Noria */
        if (t == 0x12)
            mu_obj_set_f32(o, MU_OBJF_BLEND_V, clock_mod_1000(in->time, 0));
        else if (t == 0x1a8) {
            float p[3];
            get_v(o, MU_OBJF_POSITION, p);
            p[1] = p[1] - 50.0f;
            p[2] = p[2] + 350.0f;
            const float light[3] = {0.5f, 0.5f, 0.5f};
            particle_here(log, index, o, 0x7f26, p, light, 9, 1.4f);
        }
        return 1;
    case 4:   /* Lost Tower */
        switch (t) {
        case 3: case 4: mu_obj_set_f32(o, MU_OBJF_BLEND_U, clock_mod_1000(in->time, 1)); break;
        case 0x12: case 0x17: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 1); break;
        case 0x13: case 0x14:
            mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 4);
            mu_obj_set_f32(o, MU_OBJF_BLEND_U, clock_mod_1000(in->time, 1));
            break;
        case 0x18:
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
            if (rem_i32(rnd(c), 64) == 0)
                create_effect_here(log, index, o, 0x7f42);
            break;
        case 0x19: mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2); break;
        case 0x26: case 0x27: event(log, MU_OBJ_CALL_LOSTTOWER_VISUAL, index); break;
        default: break;
        }
        return 1;
    case 7:   /* Atlans */
        switch (t) {
        case 0x16: {
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
            float timer = mu_obj_f32(o, MU_OBJF_TIMER) + 0.1f;
            mu_obj_set_f32(o, MU_OBJF_TIMER, timer);
            if (timer > 10.0f)
                mu_obj_set_f32(o, MU_OBJF_TIMER, 0.0f);
            if (mu_obj_f32(o, MU_OBJF_TIMER) > 5.0f) {
                float p[3], light[3];
                get_v(o, MU_OBJF_POSITION, p);
                get_v(o, MU_OBJF_LIGHT, light);
                particle_here(log, index, o, 0x7fcd, p, light, 0, 1.0f);
            }
            break;
        }
        case 0x17:
            mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
            mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, wave_light(in->time, 0.002f, 0.3f));
            break;
        case 0x20: case 0x22:
            mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 1);
            mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, wave_light(in->time, 0.004f, 0.5f));
            break;
        case 0x26: mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0); break;
        case 0x28:
            mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
            mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, wave_light(in->time, 0.004f, 0.3f));
            mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.05f);
            break;
        default: break;
        }
        return 1;
    default:
        return 0;
    }
}

/* Tormenta handler slot 0x30 (0x00e4c95e): sounds when the hero is near. sqrt 0x00961a07
 * takes the widened sum and rounds the root to binary32 (as in AddTerrainLight). */
static void tormenta_move(const uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t != 6 && t != 0xb7 && t != 0xc8)
        return;
    const float dx = in->hero[0] - mu_obj_f32(o, MU_OBJF_POSITION);
    const float dy = in->hero[1] - mu_obj_f32(o, MU_OBJF_POSITION + 4);
    float sum = dx * dx;
    sum = sum + dy * dy;
    const float distance = (float)sqrt((double)sum);
    float limit;
    uint32_t sound;
    if (t == 6) {
        limit = 1300.0f * mu_obj_f32(o, MU_OBJF_SCALE);
        sound = 0x581;
    } else if (t == 0xb7) {
        limit = 450.0f;
        sound = 0x584;
    } else {
        limit = 800.0f;
        sound = 0x583;
    }
    if (limit >= distance) {   /* comiss limit, distance; jb skips */
        mu_obj_event *e = event(log, MU_OBJ_CALL_SOUND, index);
        arg(e, sound);
        arg(e, 0);
        arg(e, 0);
    }
}

int mu_obj_move_generic(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    const int32_t world = in->world, type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (world == 9)
        return MU_OBJ_UNSUPPORTED;   /* hero-centred light flashes before the generic part */
    if (world == 0 && (type == 0x7d || type == 0x7e))
        mu_obj_set_f32(o, MU_OBJF_ALPHA_TARGET, in->hero_tile == 4 ? 0.0f : 1.0f);
    if (world == 2 && (type == 0x51 || type == 0x52 || type == 0x60 || type == 0x62 || type == 0x63))
        mu_obj_set_f32(o, MU_OBJF_ALPHA_TARGET, in->hero_tile == 3 || in->hero_tile >= 10 ? 0.0f : 1.0f);
    mu_obj_alpha_step(o);
    if (0.01f > mu_obj_f32(o, MU_OBJF_ALPHA))
        return MU_OBJ_SKIPPED;
    if (!in->has_model)
        return MU_OBJ_SKIPPED;
    const uint16_t action = mu_obj_u16(o, MU_OBJF_ACTION);
    float v = mu_obj_f32(o, MU_OBJF_VELOCITY);
    if (world == 8) {
        if (type == 8)
            v = v * 4.0f;
    } else if ((world == 0x39 || world == 0x3a) && (type == 0x10 || type == 0x11 || type == 0x44)) {
        v = in->speed(in->context, type, action);
    } else if ((world == 0x50 || world == 0x51) && (type == 0x42 || type == 0x6b)) {
        v = in->speed(in->context, type, action);
    } else if ((world == 0x5b || world == 0x5c) && (type == 0x10 || type == 0x34 || type == 0x39 || type == 0x65)) {
        v = in->speed(in->context, type, action);
    } else if (world == 0x5e && type == 5) {
        v = in->speed(in->context, type, 0);
    } else if (world == 0x73 && type == 0x3c) {
        v = 0.16f;
    } else if ((world == 0x87 || world == 0x88) && in->model_has_actions) {
        if ((type == 0x16 || type == 0x29 || type == 0x5c || type == 0x74 || type == 0x77 || type == 0x81) &&
            action == 1)
            v = in->speed(in->context, type, action);
        else if (type == 0xb5 && action == 2)
            v = in->speed(in->context, type, action);
    }
    mu_obj_event *e = event(log, MU_OBJ_CALL_TICK, index);
    arg_f(e, v);
    if (in->scene_state == 3 || in->scene_state == 5) {
        if (type == 0x12d || type == 0x12e) {
            const int32_t t = trunc_i32(in->time);
            float s = (float)rem_i32(t, 4000) * 0.00025f;
            mu_obj_set_f32(o, MU_OBJF_BLEND_V, -s);
        } else if (type == 0x12f) {
            return MU_OBJ_UNSUPPORTED;   /* login-scene light from 0x0bdc5e6c / 0x01cf17b8 */
        }
    }
    return MU_OBJ_OK;
}

int mu_obj_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    const int status = mu_obj_move_generic(o, index, in, log);
    if (status != MU_OBJ_OK)
        return status;
    const int32_t world = in->world;
    if (world == 0) {
        lorencia_move(o, index, in, log);
        return MU_OBJ_OK;
    }
    if (world == 0x8d) {
        tormenta_move(o, index, in, log);
        return MU_OBJ_OK;
    }
    if (world == 2) {
        mu_devias_move(o, index, in, log);
        return MU_OBJ_OK;
    }
    if (world == 8) {
        mu_tarkan_move(o, index, in, log);
        return MU_OBJ_OK;
    }
    if (world == 51) {
        mu_elbeland_move(o, index, in, log);
        return MU_OBJ_OK;
    }
    if (world == 57 || world == 58) {
        mu_raklion_move(o, in->time);
        return MU_OBJ_OK;
    }
    if (world_move(o, index, in, log) || hook_move(o, index, in, log))   /* NATIVE-FIDELITY-002 */
        return MU_OBJ_OK;
    if (world == 62 || world == 63) {
        if (world == 62) mu_santa_move(o, world);
        else mu_vulcanus_move(o, world);
        return MU_OBJ_OK;
    }
    if (world == MU_LOGIN_WORLD) {   /* CGMLogInScene_Ex slot 0x30 */
        mu_login_move(o, in->now_ms, NULL, NULL);
        return MU_OBJ_OK;
    }
    if (world == MU_CSW_WORLD) {     /* CGMCharacterScene_Ex slot 0x30 (NATIVE-CHARSEL-002) */
        mu_csw_move(o, index, in->rand_fn, in->context, log);
        return MU_OBJ_OK;
    }
    return MU_OBJ_UNSUPPORTED;
}

int mu_obj_move_pre_sky(int32_t world, const float hero[3], mu_obj_rand_fn rnd, void *c, mu_obj_log *log)
{
    if (world != 10 && world != 0x84)
        return 0;
    event(log, MU_OBJ_CALL_SKY, -1);
    if (world == 0x84 || rem_i32(rnd(c), 10) != 0)
        return 1;
    float p[3];
    p[0] = (float)(rem_i32(rnd(c), 5000) - 2500) + hero[0];
    p[1] = (float)(rem_i32(rnd(c), 5000) - 2500) + hero[1];
    p[2] = hero[2] - 1000.0f;
    const float zero[3] = {0.0f, 0.0f, 0.0f}, one[3] = {1.0f, 1.0f, 1.0f};
    mu_obj_event *e = event(log, MU_OBJ_CALL_CREATE_EFFECT, -1);
    arg(e, 0x7ef7);
    arg_v(e, p);
    arg_v(e, zero);
    arg_v(e, one);
    arg(e, 0);   /* subtype */
    arg(e, 0);   /* no owner */
    return 1;
}

int mu_obj_visual(uint8_t *o, int32_t world, float time)
{
    if (world != 0 || mu_obj_i32(o, MU_OBJF_TYPE) != 0x69)
        return MU_OBJ_UNSUPPORTED;
    mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, 1.0f);
    const int32_t t = trunc_i32(time);
    mu_obj_set_f32(o, MU_OBJF_BLEND_V, (float)rem_i32((int32_t)(0u - (uint32_t)t), 1000) * 0.001f);
    return MU_OBJ_OK;
}

/* ---- 6. RenderObjects 0x016d5020 ---- */

static float sector_range(int32_t world)
{
    if (world == 0x86 || world == 0x87 || world == 0x88 || world == 0x8a || world == 0x8c || world == 0x8d)
        return -300.0f;
    if (world == 0x89)
        return -200.0f;
    return -180.0f;
}

static void render_draw(mu_obj_world *w, int32_t k, const mu_obj_render_inputs *in, mu_obj_log *log)
{
    (void)w;
    mu_obj_event *e = event(log, MU_OBJ_CALL_RENDER_OBJECT, k);
    arg(e, 0);
    arg(e, 0);
    arg(e, 0);
    arg(e, 0xffffffffu);
    arg(e, 0xffffffffu);
    event(log, MU_OBJ_CALL_VISUAL, k);
    if (in->has_effects && in->has_effects(in->context, k))
        arg_f(event(log, MU_OBJ_CALL_EFFECTS, k), in->frame_time);
}

static uint8_t object_test(const uint8_t *o, const mu_obj_render_inputs *in, float bias)
{
    const float x = mu_obj_f32(o, MU_OBJF_POSITION) * 0.01f, y = mu_obj_f32(o, MU_OBJF_POSITION + 4) * 0.01f;
    const float range = mu_obj_f32(o, MU_OBJF_RANGE) + bias;
    return (uint8_t)mu_terrain_test_frustum_2d(in->x2d, in->y2d, in->scene_state, x, y, range);
}

void mu_obj_render_pass(mu_obj_world *w, const mu_obj_render_inputs *in, int32_t *counter, mu_obj_log *log)
{
    const float bias = in->world == 10 ? -10.0f : 0.0f;
    if (counter) {
        if (*counter > 0x28)
            *counter = 0;
        ++*counter;
    }
    const float range = sector_range(in->world);
    for (int32_t i = 0; i < 16; ++i)
        for (int32_t j = 0; j < 16; ++j) {
            const int32_t s = i * 16 + j;
            w->block_visible[s] = (uint8_t)mu_terrain_test_frustum_2d(in->x2d, in->y2d, in->scene_state,
                                                                      (float)(i * 16 + 8), (float)(j * 16 + 8), range);
            for (int32_t k = w->head[s]; k >= 0; k = w->next[k]) {
                uint8_t *o = w->objects[k];
                const int view = w->block_visible[s] || in->top_view;
                if (in->render_first && in->render_first(in->context, k)) {
                    render_draw(w, k, in, log);
                    if (view && o[MU_OBJF_LIVE])
                        o[MU_OBJF_VISIBLE] = object_test(o, in, bias);
                } else if (view && o[MU_OBJF_LIVE]) {
                    o[MU_OBJF_VISIBLE] = object_test(o, in, bias);
                    if (o[MU_OBJF_VISIBLE])
                        render_draw(w, k, in, log);
                }
            }
        }
}

/* ---- 7. RenderObject 0x016d4fe4 ---- */

int mu_obj_render(uint8_t *o, int32_t index, uint8_t *b, uint8_t translate, const mu_obj_draw_inputs *in,
                  mu_obj_log *log)
{
    const int32_t world = in->world, type = mu_obj_i32(o, MU_OBJF_TYPE);
    /* setup 0x017ec896 */
    const int chaos = (world >= 0x12 && world <= 0x17) || world == 0x35 || world == 0x61;   /* 0x009dacb8 */
    if (chaos && in->chaos_hero_flag == 1)
        mu_obj_set_f32(o, MU_OBJF_ALPHA, mu_obj_f32(o, MU_OBJF_ALPHA) - 0.15f);
    if (0.01f > mu_obj_f32(o, MU_OBJF_ALPHA))
        return MU_OBJ_SKIPPED;
    if (!in->has_model)
        return MU_OBJ_SKIPPED;
    mu_obj_set_f32(b, MU_MDL_HEIGHT, 0.0f);
    b[MU_MDL_FLAG_51] = o[MU_OBJF_FLAG_E];
    mu_obj_body_light(o, b, &in->light);
    memcpy(b + MU_MDL_SCALE, o + MU_OBJF_SCALE, 4);
    memcpy(b + MU_MDL_ACTION, o + MU_OBJF_ACTION, 2);
    memcpy(b + MU_MDL_ORIGIN, o + MU_OBJF_POSITION, 12);
    b[MU_MDL_SECONDARY] = o[0x3b];
    if (type == 0x7e2 || type == 0x7e1 || ((world == 0x6e || world == 0x6f) && type == 0) ||
        (world == 0x84 && type == 0x1e))
        return MU_OBJ_UNSUPPORTED;
    if (mu_obj_i32(o, MU_OBJF_OWNER) != 0)
        return MU_OBJ_UNSUPPORTED;   /* owner's buffs may stop the frame */
    mu_obj_event *e = event(log, MU_OBJ_CALL_ANIMATION, index);
    arg(e, o[MU_OBJF_BONE_BUFFER] ? 1u : 0u);   /* 1: the object's own bone buffer, 0: 0x06fce398 */
    arg_f(e, mu_obj_f32(o, MU_OBJF_FRAME));
    arg_f(e, mu_obj_f32(o, MU_OBJF_PRIOR_FRAME));
    arg(e, mu_obj_u16(o, MU_OBJF_PRIOR_ACTION));
    arg(e, 0);
    arg(e, translate ? 0u : 1u);
    /* bone scale 0x01cf104c = 1 (select 0) */
    e = event(log, MU_OBJ_CALL_TRANSFORM, index);
    arg(e, o[MU_OBJF_BONE_BUFFER] ? 1u : 0u);
    arg(e, translate);
    arg(e, 0);
    arg_f(e, 0.4f);
    arg_f(e, mu_obj_f32(o, MU_OBJF_VALUE_E4));
    arg_f(e, mu_obj_f32(o, MU_OBJF_VALUE_E8));
    /* draw 0x017edf43 */
    if (in->bounds_mode == 0 && mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) == -2)
        return MU_OBJ_SKIPPED;
    const float alpha = mu_obj_f32(o, MU_OBJF_ALPHA);
    if (mu_obj_i32(o, MU_OBJF_RENDER_MODE) == 0x80) {
        e = event(log, MU_OBJ_CALL_BODY, index);
        arg(e, 0x82);
        arg_f(e, alpha);
        arg(e, (uint32_t)mu_obj_i32(o, MU_OBJF_BLEND_MESH));
        arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_LIGHT));
        arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_U));
        arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_V));
        arg(e, (uint32_t)mu_obj_i32(o, MU_OBJF_HIDDEN_MESH));
        arg(e, 0xffffffffu);
        return MU_OBJ_OK;
    }
    event(log, MU_OBJ_CALL_TINT, index);
    const int kalima = (world >= 0x18 && world <= 0x1d) || world == 0x24;   /* 0x009b0418 */
    if (o[MU_OBJF_SHADOW] && world != 10 && world != 0x84 && !kalima && !in->option_flag)
        return MU_OBJ_UNSUPPORTED;   /* RenderBodyShadow block: object methods 0x0103ec05/0x0103ebf3 */
    int handled = in->custom_render && in->custom_render(in->context, index);
    event(log, MU_OBJ_CALL_CUSTOM, index);
    if (!handled && in->registry && in->registry(in->context, index))
        handled = 1;
    if (!handled) {
        e = event(log, MU_OBJ_CALL_BODY, index);
        arg(e, 2);
        arg_f(e, alpha);
        arg(e, (uint32_t)mu_obj_i32(o, MU_OBJF_BLEND_MESH));
        arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_LIGHT));
        arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_U));
        arg_f(e, mu_obj_f32(o, MU_OBJF_BLEND_V));
        arg(e, (uint32_t)mu_obj_i32(o, MU_OBJF_HIDDEN_MESH));
        arg(e, 0xffffffffu);
    }
    event(log, MU_OBJ_CALL_AFTER, index);
    return MU_OBJ_OK;
}
