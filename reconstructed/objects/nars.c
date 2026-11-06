/* Nars, world 110 (predicate 0x00e2602d: worlds 110 and 111). Create 0x00e260f0 (with its type table at
 * 0x00e26640), move 0x00e26668, visual 0x00e26ae7. None of the three tests the object (or the visual its model)
 * for null. */
#include "worlds_s2.h"
#include "worlds_r2.h"
#include "worlds_q_internal.h"
#include "../record-math/record_math.h"
#define NARS_HEIGHT 0xcc   /* f32 the create of type 0 sets to -2800 */
#define NARS_PHASE 0x64    /* i32: rest counter of types 1/2, phase of types 85/87 (create: rand % 10 * 300) */
static int nars_world(const mu_q_inputs *in) { return in->world == 110 || in->world == 111; }
static const float zero3[3] = {0.0f, 0.0f, 0.0f};

/* ---------------------------------------------------------------- create */

static void range_flag(uint8_t *o, float range, int flag)
{
    mu_obj_set_f32(o, MU_OBJF_RANGE, range);
    if (flag) o[MU_OBJF_AFTER_CHARACTER] = 1;
}
int mu_nars_create(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!nars_world(in)) return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0:
        mu_obj_set_f32(o, NARS_HEIGHT, -2800.0f);
        mu_obj_set_f32(o, MU_OBJF_SCALE, 17.0f);
        mu_obj_set_f32(o, MU_OBJF_ANGLE + 8, 340.0f);
        mu_obj_set_f32(o, MU_OBJF_RANGE, -30000.0f);
        break;
    case 6: case 11: case 12: case 28: range_flag(o, -200.0f, mu_obj_i32(o, MU_OBJF_TYPE) == 6); break;
    case 8: case 9: mu_obj_set_f32(o, MU_OBJF_RANGE, -800.0f); break;
    case 10: case 14: case 15: case 25: case 26: case 29: case 30: case 32: case 39: case 59: case 66: case 79:
    case 146:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    case 16: case 21: case 22: case 23: case 24: case 27: o[MU_OBJF_AFTER_CHARACTER] = 1; break;
    case 17: case 34: case 35: case 36: case 37: case 38: case 142: case 150: range_flag(o, -400.0f, 1); break;
    case 19: case 60: case 64: case 154: mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f); break;
    case 85: case 87:
        mu_obj_set_i32(o, NARS_PHASE, in->rand_fn(in->context) % 10 * 300);
        break;
    case 134: {
        if (!in->bone) return -1;   /* needs the type's model posed at creation */
        float p[3];
        wb_get(o, MU_OBJF_POSITION, p);
        mu_obj_event *e = wb_event(log, MU_NARS_POSE, index);   /* model +0x78, +0x74, then Animation */
        wb_vec(e, p);
        wb_float(e, mu_obj_f32(o, MU_OBJF_SCALE));
        float out[3];
        in->bone(in->context, 4, zero3, out);
        memcpy(o + MU_OBJF_START, out, 12);
        break;
    }
    default: break;
    }
    return 1;
}

/* ---------------------------------------------------------------- move */

/* rand % 5 * 0.04: (s + 0.8, s + 0.3, s + 0.2) at x/y of `at` with `range`. */
static void flame_light(const uint8_t *o, int32_t i, const mu_q_inputs *in, uint32_t at, int32_t range, mu_obj_log *log)
{
    const float s = (float)(in->rand_fn(in->context) % 5) * 0.04f;
    const float l[3] = {s + 0.8f, s + 0.3f, s + 0.2f};
    q_add_light(log, i, mu_obj_f32(o, at), mu_obj_f32(o, at + 4), l, range);
}
int mu_nars_move(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!nars_world(in)) return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 1: case 2: {
        const uint8_t *r = q_action_at(in, o);
        if (r && q_action_ended(o, r)) {
            if (mu_obj_i32(o, NARS_PHASE) <= 0) {
                mu_obj_set_i32(o, NARS_PHASE, in->rand_fn(in->context) % 3 + 5);
                q_set_action(in, o, 0);
            } else {
                q_set_action(in, o, 1);
                mu_obj_set_i32(o, NARS_PHASE, mu_obj_i32(o, NARS_PHASE) - 1);
            }
        }
        break;
    }
    case 4: case 116: case 146: flame_light(o, index, in, MU_OBJF_POSITION, 1, log); break;
    case 134: flame_light(o, index, in, MU_OBJF_START, 2, log); break;
    case 77: mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.015f); break;
    default: break;
    }
    return 1;
}

/* ---------------------------------------------------------------- visual */

static float client_abs(float x) { return 0.0f > x ? -x : x; }   /* 0x0184f8ff: keeps -0 and NaN */
int mu_nars_visual_bones(int32_t type)
{
    switch (type) {
    case 4: case 116: return 7;
    case 11: case 133: return 2;
    case 134: return 3;
    case 85: return 4;
    case 87: return 15;
    default: return -1;
    }
}
static void bone_at(const mu_q_inputs *in, int32_t bone, float out[3]) { in->bone(in->context, bone, zero3, out); }

/* Fire family: CreateEffect 0x413 (light 1, sub 10, owner 0, word4 = (int)(scale * 0.4 * (rand % 5 + 13) * 0.1))
 * and the 0x7ef7 flame sprite (scale 2 * scale, light (1, 0.2, 0)) at `p`. The rand precedes the bone read. */
static int32_t fire_key(const uint8_t *o, const mu_q_inputs *in)
{
    const float k = mu_obj_f32(o, MU_OBJF_SCALE) * 0.4f;
    return wb_int(k * (float)(in->rand_fn(in->context) % 5 + 13) * 0.1f);
}
static void fire(const uint8_t *o, int32_t i, int32_t key, const float p[3], mu_obj_log *log)
{
    float a[3];
    wb_get(o, MU_OBJF_ANGLE, a);
    const float white[3] = {1.0f, 1.0f, 1.0f}, flame[3] = {1.0f, 0.2f, 0.0f};
    mu_obj_event *e = wb_event(log, MU_R2_EFFECT, i);
    wb_arg(e, 0x413); wb_vec(e, p); wb_vec(e, a); wb_vec(e, white); wb_arg(e, 0xa); wb_arg(e, 0);
    wb_arg(e, (uint16_t)key);
    q_sprite(log, i, 0x7ef7, p, 2.0f * mu_obj_f32(o, MU_OBJF_SCALE), flame, 0.0f);
}
/* Types 11, 133 and 134: two 0x7f6b glow sprites at each of bones 1 and 2. */
static void glow_pair(const uint8_t *o, int32_t i, const mu_q_inputs *in, mu_obj_log *log)
{
    const float s = client_abs(q_sin((float)((double)in->time * 0.0008))) * 0.6f + 0.1f;
    const float sc = mu_obj_f32(o, MU_OBJF_SCALE) * 0.3f * s;
    const float pale[3] = {s, s, s}, warm[3] = {0.2f + s, 0.1f, 0.1f};
    for (int32_t bone = 1; bone <= 2; ++bone) {
        float p[3];
        bone_at(in, bone, p);
        q_sprite(log, i, 0x7f6b, p, 0.4f, warm, 0.0f);
        q_sprite(log, i, 0x7f6b, p, sc, pale, 0.0f);
    }
}
/* 1 in `n`: CreateParticle(bitmap, position, angle, light, sub, scale, owned). */
static void emit(uint8_t *o, int32_t i, const mu_q_inputs *in, int32_t n, uint32_t bitmap, const float l[3],
                 uint32_t sub, mu_obj_log *log)
{
    if (in->rand_fn(in->context) % n) return;
    float p[3], a[3];
    wb_get(o, MU_OBJF_POSITION, p);
    wb_get(o, MU_OBJF_ANGLE, a);
    q_particle(log, i, bitmap, p, a, l, sub, mu_obj_f32(o, MU_OBJF_SCALE), 1);
}
/* Types 14 and 79: 1 in 8, an unowned 0x7f5a sub 0x45 and an owned 0x7f5a sub 0x15 with the object light. */
static void smoke(uint8_t *o, int32_t i, const mu_q_inputs *in, const float l[3], mu_obj_log *log)
{
    if (in->rand_fn(in->context) % 8) return;
    float p[3], a[3], ol[3];
    wb_get(o, MU_OBJF_POSITION, p);
    wb_get(o, MU_OBJF_ANGLE, a);
    wb_get(o, MU_OBJF_LIGHT, ol);
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    q_particle(log, i, 0x7f5a, p, a, l, 0x45, scale, 0);
    q_particle(log, i, 0x7f5a, p, a, ol, 0x15, scale * 2.0f, 1);
}
/* Types 25 and 26: 1 in 5, (0, rand % 100, 0) rotated by the yaw rand % 100 (AngleMatrix 0x00cff32a, VectorRotate
 * 0x00d000ad) from the object position; type 26 first sets the object light to (1, 0.5, 0.1). */
static void orbit(uint8_t *o, int32_t i, const mu_q_inputs *in, uint32_t bitmap, uint32_t sub, mu_obj_log *log)
{
    if (in->rand_fn(in->context) % 5) return;
    float v[3] = {0.0f, 0.0f, 0.0f}, yaw[3] = {0.0f, 0.0f, 0.0f}, m[12], p[3], a[3], ol[3];
    v[1] = (float)(in->rand_fn(in->context) % 100);
    yaw[2] = (float)(in->rand_fn(in->context) % 100);
    mu_angle_matrix(yaw, m);
    mu_vector_rotate(v, m, p);
    for (int q = 0; q < 3; ++q)
        p[q] = p[q] + mu_obj_f32(o, MU_OBJF_POSITION + 4 * (uint32_t)q);
    if (sub == 2) {
        mu_obj_set_f32(o, MU_OBJF_LIGHT, 1.0f);
        mu_obj_set_f32(o, MU_OBJF_LIGHT + 4, 0.5f);
        mu_obj_set_f32(o, MU_OBJF_LIGHT + 8, 0.1f);
    }
    wb_get(o, MU_OBJF_ANGLE, a);
    wb_get(o, MU_OBJF_LIGHT, ol);
    q_particle(log, i, bitmap, p, a, ol, sub, 1.0f, 0);
}
/* Type 32: a band 30 * ((int)x % 3 + 1) .. + width (10 at 90, else 40) of 50 * (sin(T * 0.001) + 1); inside it,
 * twenty owned 0x801b sub 7. */
static void band(uint8_t *o, int32_t i, const mu_q_inputs *in, mu_obj_log *log)
{
    const float s = (q_sin(in->time * 0.001f) + 1.0f) * 0.5f * 100.0f;
    const int32_t lo = 30 * (wb_int(mu_obj_f32(o, MU_OBJF_POSITION)) % 3 + 1);
    const int32_t width = (float)lo == 90.0f ? 10 : 40;
    if (!(s >= (float)lo) || !((float)(lo + width) >= s)) return;
    const float l[3] = {0.9f, 0.2f, 0.2f};
    float p[3], a[3];
    wb_get(o, MU_OBJF_POSITION, p);
    wb_get(o, MU_OBJF_ANGLE, a);
    for (int k = 0; k < 20; ++k)
        q_particle(log, i, 0x801b, p, a, l, 7, mu_obj_f32(o, MU_OBJF_SCALE), 1);
}
/* Type 85: bone 4 with a 1-in-7 spark, the 0x7ef7 flame of 1.5 + 0.1 sin, and while sin(T * 0.001 + phase) > 0.5
 * an upward 0x7f26. */
static void lamp(const uint8_t *o, int32_t i, const mu_q_inputs *in, mu_obj_log *log)
{
    const float s = q_sin((float)(wb_int(in->time) % 3000) * 0.0010466667590662837f) * 0.1f;
    float p[3], a[3];
    bone_at(in, 4, p);
    wb_get(o, MU_OBJF_ANGLE, a);
    if (in->rand_fn(in->context) % 7 == 0) {
        const float l[3] = {0.6f, 1.0f, 1.0f};
        q_particle(log, i, 0x7efa, p, a, l, 2, 0.25f, 0);
    }
    const float flame[3] = {0.2f, 0.65f, 0.65f};
    q_sprite(log, i, 0x7ef7, p, 1.5f + s, flame, 0.0f);
    const float rise = q_sin(in->time * 0.001f + (float)mu_obj_i32(o, NARS_PHASE)) - 0.5f;
    if (rise > 0.0f) {
        const float up[3] = {0.0f, 0.0f, 1.0f}, l[3] = {0.3f, 0.95f, 0.95f};
        q_particle(log, i, 0x7f26, p, up, l, 0xe, 0.06f, 0);
    }
}
/* Type 87: two 0x7f26 sprites at each of bones 5, 6, 7, 11, 14, 15 with |sin((phase + T) * 0.0002 * k)| * 0.4. */
static const int32_t lantern_bones[7] = {6, 5, 6, 7, 11, 14, 15};   /* the client reads entries 1..6 */
static void lanterns(const uint8_t *o, int32_t i, const mu_q_inputs *in, mu_obj_log *log)
{
    for (int32_t k = 0; k < 6; ++k) {
        const float x = (float)mu_obj_i32(o, NARS_PHASE) + in->time;
        const float s = client_abs(q_sin((float)((double)x * 0.0002 * (double)k))) * 0.4f;
        const float blue[3] = {s * 1.3f, s * 1.3f, s * 1.9f}, dim[3] = {0.15f, 0.15f, 0.15f};
        float p[3];
        bone_at(in, lantern_bones[k + 1], p);
        q_sprite(log, i, 0x7f26, p, 2.0f, blue, 0.0f);
        q_sprite(log, i, 0x7f26, p, 1.5f, dim, 0.0f);
    }
}
int mu_nars_visual(uint8_t *o, int32_t i, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!nars_world(in)) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (mu_nars_visual_bones(t) >= 0 && !in->bone) return -1;
    switch (t) {
    case 4: case 116: {
        const int32_t key = fire_key(o, in);
        float p[3];
        bone_at(in, 7, p);
        fire(o, i, key, p, log);
        break;
    }
    case 146: {
        const int32_t key = fire_key(o, in);
        float p[3];
        wb_get(o, MU_OBJF_POSITION, p);
        fire(o, i, key, p, log);
        break;
    }
    case 134: {
        glow_pair(o, i, in, log);
        const int32_t key = fire_key(o, in);
        float p[3];
        bone_at(in, 3, p);
        fire(o, i, key, p, log);
        break;
    }
    case 11: case 133: glow_pair(o, i, in, log); break;
    case 10: {
        const float l[3] = {0.05f, 0.05f, 0.05f};
        emit(o, i, in, 12, 0x822a, l, 0, log);
        break;
    }
    case 14: { const float l[3] = {0.78f, 0.0f, 1.0f}; smoke(o, i, in, l, log); break; }
    case 79: { const float l[3] = {0.9f, 0.5f, 0.5f}; smoke(o, i, in, l, log); break; }
    case 15: { const float l[3] = {0.05f, 0.02f, 0.01f}; emit(o, i, in, 6, 0x7f89, l, 0x19, log); break; }
    case 29: { const float l[3] = {0.01f, 0.02f, 0.05f}; emit(o, i, in, 6, 0x7f89, l, 0x19, log); break; }
    case 39: { const float l[3] = {0.06f, 0.05f, 0.0f}; emit(o, i, in, 6, 0x7f89, l, 0x19, log); break; }
    case 59: { const float l[3] = {0.01f, 0.03f, 0.0f}; emit(o, i, in, 6, 0x7f89, l, 0x19, log); break; }
    case 66: { const float l[3] = {0.03f, 0.0f, 0.04f}; emit(o, i, in, 6, 0x7f89, l, 0x19, log); break; }
    case 30: { const float l[3] = {0.9f, 0.2f, 0.2f}; emit(o, i, in, 3, 0x7f5a, l, 0x45, log); break; }
    case 25: orbit(o, i, in, 0x7fdd, 3, log); break;
    case 26: orbit(o, i, in, 0x8184, 2, log); break;
    case 32: band(o, i, in, log); break;
    case 85: lamp(o, i, in, log); break;
    case 87: lanterns(o, i, in, log); break;
    default: break;
    }
    return 1;
}
