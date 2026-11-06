/* Imperial Guardian (Varka), worlds 69..72: one class per world (vtables 0x01aa7dd4, 0x01aa7f84, 0x01aa8038,
 * 0x01aa8230). Create 0x00dc6fab / 0x00dd3c76 / 0x00dd8d6d / 0x00dde9e0, move 0x00dc7136 / 0x00dd3e01 /
 * 0x00dd8ef8 / 0x00ddeb8a, visual 0x00dc73d0 / 0x00dd4097 / 0x00dd9192 / 0x00ddee5e. The four bodies of each slot
 * are the same code apart from the world predicate and the deltas named below (docs/research/client-worlds-s3.md).
 */
#include "worlds_s3.h"
#include "worlds_q_internal.h"
#include "worlds_r2.h"
#include "icarus.h"
#include "../record-math/record_math.h"

int mu_imperial_create(uint8_t *o, int32_t cls, mu_obj_rand_fn rnd, void *context)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 0x73 || t == 0x75) {
        mu_obj_set_i32(o, 0x60, 100);
        return 1;
    }
    if (cls == 72 && t == 10) {   /* class 72 only */
        mu_obj_set_i32(o, 0x60, rnd(context) % 50);
        return 1;
    }
    if (t < 0x81 || t > 0x84)
        return 0;
    mu_obj_set_f32(o, MU_OBJF_ANGLE + 8, (float)(wb_int(mu_obj_f32(o, MU_OBJF_ANGLE + 8)) % 360));
    memcpy(o + MU_OBJF_HEAD_ANGLE, o + MU_OBJF_ANGLE, 12);     /* dword copies: bits, NaN payloads included */
    memcpy(o + MU_OBJF_POSITION_COPY, o + MU_OBJF_POSITION, 12);
    return 1;
}

/* The predicates 0x00dd38c5 / 0x00dd897d / 0x00dde62f test their own world; class 72's 0x00de5519 accepts 72, 73
 * and 74 (the factory registers no class for 73 and 74). */
static int imperial_world(int32_t cls, int32_t world)
{
    return cls == 72 ? world >= 72 && world <= 74 : world == cls;
}

int mu_imperial_move_tick(uint8_t *o, int32_t index, int32_t cls, int32_t world, int has_model, mu_obj_log *log)
{
    if (!imperial_world(cls, world))
        return 0;
    mu_obj_alpha_step(o);   /* again: MoveObject stepped it before calling slot 0x30 */
    if (0.01f > mu_obj_f32(o, MU_OBJF_ALPHA) || !has_model)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    float speed = mu_obj_f32(o, MU_OBJF_VELOCITY);
    if (cls == 72 && t == 10) {
        if (mu_obj_i32(o, 0x60) > 0) {
            mu_obj_set_i32(o, 0x60, mu_obj_i32(o, 0x60) - 1);
            mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
            mu_obj_set_f32(o, MU_OBJF_PRIOR_FRAME, 0.0f);
        }
    } else if (t == 20) {
        speed = speed * 2.0f;
    } else if (t >= 122 && t <= 124) {
        speed = speed * 3.0f;
    } else if (t == 128) {
        speed = speed * 6.0f;
    }
    wb_float(wb_event(log, MU_OBJ_CALL_TICK, index), speed);   /* PlayAnimation(frame, prior, prior action, speed) */
    return 1;
}

int mu_imperial_move_cases(uint8_t *o, int32_t cls, float *frame_lock)
{
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 20: {   /* every type-20 object of the class follows the first one that leads (the class static) */
        const float frame = mu_obj_f32(o, MU_OBJF_FRAME);
        if (*frame_lock - frame > 10.0f || frame > *frame_lock)
            *frame_lock = frame;
        else
            mu_obj_set_f32(o, MU_OBJF_FRAME, *frame_lock);
        return 1;
    }
    case 64:
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, cls == 71 ? 0.44f : 0.64f);
        return 1;
    case 0x24:
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.02f);
        return 1;
    case 0x4f: case 0x50: case 0x52: case 0x53: case 0x54: case 0x55: case 0x56:
    case 0x81: case 0x82: case 0x83: case 0x84:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        if (cls != 70)
            return 1;
        /* class 70 has no break here: the blend scroll of 0x51 follows */
        /* fall through */
    case 0x51:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) + 0.015f);
        return 1;
    default:
        return 0;
    }
}

int mu_imperial_move(uint8_t *o, int32_t index, int32_t cls, int32_t world, int has_model, float *frame_lock,
                     mu_obj_log *log)
{
    return mu_imperial_move_tick(o, index, cls, world, has_model, log) ? mu_imperial_move_cases(o, cls, frame_lock) : 0;
}

int mu_imperial_visual_bones(int32_t cls, int32_t type)
{
    switch (type) {
    case 12: return 3;
    case 37: return 1;
    case 50: return 7;
    case 157: return cls == 72 ? 26 : -1;
    default: return -1;
    }
}

static float client_abs(float x) { return 0.0f > x ? -x : x; }   /* 0x0184f8ff: keeps -0 and NaN */
static const float white[3] = {1.0f, 1.0f, 1.0f};

/* Four 0x7fd5 subtype-5 joints from the position to itself, angle (rand % 60 + 150, 0, z + 180 or z), then the
 * 0x7f25 particle with the last angle and the object's light. */
static void sparks(const uint8_t *o, int32_t i, const mu_q_inputs *in, int turned, mu_obj_log *log)
{
    float p[3], a[3], l[3];
    wb_get(o, MU_OBJF_POSITION, p);
    wb_get(o, MU_OBJF_LIGHT, l);
    for (int k = 0; k < 4; ++k) {
        a[0] = (float)(in->rand_fn(in->context) % 60 + 150);
        a[1] = 0.0f;
        a[2] = turned ? mu_obj_f32(o, MU_OBJF_ANGLE + 8) + 180.0f : mu_obj_f32(o, MU_OBJF_ANGLE + 8);
        mu_obj_event *e = wb_event(log, MU_ICARUS_JOINT, i);
        wb_arg(e, 0x7fd5); wb_vec(e, p); wb_vec(e, p); wb_vec(e, a);
        wb_arg(e, 5); wb_arg(e, 1); wb_float(e, 10.0f);
    }
    q_particle(log, i, 0x7f25, p, a, l, 0xb, 1.0f, 0);
}

/* A particle at the object's position and angle. */
static void here(mu_obj_log *log, int32_t i, const uint8_t *o, uint32_t bitmap, const float l[3], uint32_t sub,
                 float scale, int owner)
{
    float p[3], a[3];
    wb_get(o, MU_OBJF_POSITION, p);
    wb_get(o, MU_OBJF_ANGLE, a);
    q_particle(log, i, bitmap, p, a, l, sub, scale, owner);
}

int mu_imperial_visual(const uint8_t *o, int32_t i, int32_t cls, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!imperial_world(cls, in->world))
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (mu_imperial_visual_bones(cls, t) >= 0 && !in->bone)
        return -1;
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    const float zero[3] = {0.0f, 0.0f, 0.0f};
    float p[3], a[3];
    wb_get(o, MU_OBJF_POSITION, p);
    wb_get(o, MU_OBJF_ANGLE, a);
    switch (t) {
    case 12: {
        const float s = client_abs(q_sin((float)((double)in->time * 0.0008))) * 0.9f + 0.1f;
        const float sc = scale * 0.3f * s, red[3] = {0.9f, 0.1f, 0.1f}, l[3] = {s, s, s};
        const float local2[3] = {8.0f, -3.0f, -3.0f}, local3[3] = {3.0f, -3.0f, -3.5f};
        for (int k = 2; k <= 3; ++k) {
            in->bone(in->context, k, k == 2 ? local2 : local3, p);
            q_sprite(log, i, 0x7f6b, p, 0.5f, red, 0.0f);
            q_sprite(log, i, 0x7f6b, p, sc, l, 0.0f);
        }
        return 1;
    }
    case 20: case 51: {
        if (t == 51 && cls == 72)
            return 0;   /* class 72 has no case 51 */
        const float frame = mu_obj_f32(o, MU_OBJF_FRAME);
        if (frame > 5.4f && 6.5f > frame)
            sparks(o, i, in, 1, log);
        else if (t == 20 && frame > 15.4f && 16.5f > frame)
            sparks(o, i, in, 0, log);
        return 1;
    }
    case 37: {
        in->bone(in->context, 1, zero, p);
        const float s = (q_sin(in->time * 0.039f) + 1.0f) * 0.2f + 0.6f;
        const float l[3] = {s * 0.7f, s * 0.7f, s * 0.7f};
        q_sprite(log, i, 0x7f78, p, 4.0f * scale, l, 0.0f);
        return 1;
    }
    case 50: {
        const float local[3] = {0.0f, 0.0f, 5.0f}, down[3] = {0.0f, -1.0f, 0.0f}, blue[3] = {0.05f, 0.1f, 0.3f};
        for (int k = 2; k <= 7; ++k) {
            in->bone(in->context, k, local, p);
            q_particle(log, i, 0x8089, p, down, blue, 4, scale * 0.6f, 0);
            q_particle(log, i, 0x8089, p, down, white, 4, scale * 0.3f, 0);
        }
        return 1;
    }
    case 64: {
        const float frame = mu_obj_f32(o, MU_OBJF_FRAME);
        if (!((frame > 9.5f && 11.5f > frame) || (frame > 23.5f && 25.5f > frame)))
            return 1;
        const float turn[3] = {0.0f, 0.0f, a[2] + 90.0f}, forward[3] = {0.0f, 30.0f, 0.0f};
        float m[12], v[3];
        mu_angle_matrix(turn, m);
        mu_vector_rotate(forward, m, v);
        for (int k = 0; k < 3; ++k)
            p[k] = v[k] + p[k];
        const float l[3] = {0.04f, 0.03f, 0.02f};
        for (int k = 0; k < 3; ++k)
            q_particle(log, i, 0x7f89, p, a, l, 0x16, scale, 1);
        return 1;
    }
    case 79: {
        const float orange[3] = {1.0f, 0.2f, 0.0f};
        q_sprite(log, i, 0x7ef7, p, 2.0f * scale, orange, 0.0f);
        const int32_t r = in->rand_fn(in->context) % 3;
        if (r == 0) here(log, i, o, 0x8084, white, 0, scale, 0);
        else if (r == 1) here(log, i, o, 0x806e, white, 4, scale, 0);
        else if (r == 2) here(log, i, o, 0x8085, white, 0, scale, 0);
        return 1;
    }
    case 80: {
        const float s = (q_sin(in->time * 0.04f) + 1.0f) * 0.3f + 0.4f;
        const float l[3] = {s * 0.1f, s * 0.1f, s * 0.5f};
        q_sprite(log, i, 0x7ef7, p, 8.0f * scale, l, 0.0f);
        return 1;
    }
    case 82:   /* the original's light is uninitialized stack here: zero (inference) */
        here(log, i, o, 0x801e, zero, 9, scale, 0);
        return 1;
    case 83:
        here(log, i, o, 0x801c, white, 0xe, scale, 0);
        return 1;
    case 84:
        if (in->rand_fn(in->context) % 8 == 0)
            here(log, i, o, 0x801b, white, 4, scale, 0);
        return 1;
    case 85: {
        const int32_t phase = wb_int(in->time) % 200;
        if (phase < 0 || phase > 1)
            return 1;
        const int32_t n = in->rand_fn(in->context) % 4 + 4;
        const float grey[3] = {0.5f, 0.5f, 0.5f};
        for (int32_t k = 0; k < n; ++k) {   /* CreateEffect(0x7f42, ..., 6, no owner, -1, 0, word4 = (u16)scale) */
            mu_obj_event *e = wb_event(log, MU_R2_EFFECT, i);
            wb_arg(e, 0x7f42); wb_vec(e, p); wb_vec(e, a); wb_vec(e, grey); wb_arg(e, 6); wb_arg(e, 0);
            wb_arg(e, (uint16_t)wb_int(scale));
        }
        return 1;
    }
    case 86: case 129: case 130: {
        if (in->rand_fn(in->context) % 6 != 0)
            return 1;
        const float l[3] = {t == 86 ? 0.05f : 0.01f, t == 130 ? 0.05f : 0.02f,
                            t == 86 ? 0.01f : t == 129 ? 0.05f : 0.02f};
        here(log, i, o, 0x7f89, l, 0x15, scale, 1);
        return 1;
    }
    case 131: case 132:
        if (in->rand_fn(in->context) % 3 != 0)
            return 1;
        if (t == 131) {
            here(log, i, o, 0x7f5a, white, 0x16, scale, 0);
        } else {
            here(log, i, o, 0x7f5a, white, 0x3c, scale, 1);
            here(log, i, o, 0x7f5a, white, 0x3c, scale, 1);
        }
        here(log, i, o, 0x7f5a, white, 0x15, scale * 2.0f, 1);
        return 1;
    case 157: {
        if (cls != 72)
            return 0;
        if (in->world == 73 || in->world == 74)   /* no request in 73/74 (worlds without a factory class) */
            return 1;
        static const int32_t first[3] = {22, 23, 25}, second[3] = {26, 24, 21};
        const float local[3] = {4.0f, 0.0f, 0.0f}, gold[3] = {0.9f, 0.5f, 0.0f}, amber[3] = {0.75f, 0.3f, 0.0f};
        for (int k = 0; k < 3; ++k) {
            in->bone(in->context, first[k], local, p);
            for (int n = 0; n < 5; ++n) {
                q_particle(log, i, 0x8089, p, zero, gold, 3, scale * 0.2f, 0);
                q_particle(log, i, 0x8089, p, zero, amber, 3, scale * 0.1f, 0);
            }
        }
        for (int k = 0; k < 3; ++k) {
            in->bone(in->context, second[k], local, p);
            for (int n = 0; n < 4; ++n)
                q_particle(log, i, 0x7f5a, p, a, white, 0x41, (float)((double)scale * 0.1), 1);
        }
        return 1;
    }
    case 158:   /* class 72; the light is uninitialized stack in the original: zero (inference) */
        if (cls != 72)
            return 0;
        here(log, i, o, 0x7f5a, zero, 0x40, scale, 1);
        return 1;
    default:
        return 0;
    }
}
