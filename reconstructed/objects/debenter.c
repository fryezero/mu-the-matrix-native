/* Debenter, world 95 (predicate 0x00dbd14d: worlds 95 and 96). Create 0x00dbd210, move 0x00dbd4e6, visual
 * 0x00dbd735. None of the three tests the object (or the visual its model) for null. */
#include "worlds_s.h"
#include "worlds_q_internal.h"
#include "icarus.h"
#define DEBENTER_KEY 0x60   /* create's switch word: OBJECT +0x60, not the type */
#define DEBENTER_REST 0x64  /* move: swings before the next rest */
static int debenter_world(const mu_q_inputs *in) { return in->world == 95 || in->world == 96; }
static const float zero3[3] = {0.0f, 0.0f, 0.0f};
static void bone_into(const mu_q_inputs *in, int32_t bone, uint8_t *o, uint32_t offset)
{
    float out[3];
    in->bone(in->context, bone, zero3, out);
    memcpy(o + offset, out, 12);
}
static void joint(mu_obj_log *log, int32_t i, const float p[3], const float a[3], uint32_t sub)
{
    mu_obj_event *e = wb_event(log, MU_ICARUS_JOINT, i);
    wb_arg(e, 0x7fd6); wb_vec(e, p); wb_vec(e, p); wb_vec(e, a);
    wb_arg(e, sub); wb_arg(e, 1); wb_float(e, 40.0f);
}
int mu_debenter_create(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!debenter_world(in)) return 0;
    const int32_t key = mu_obj_i32(o, DEBENTER_KEY);
    if (key == 9) {
        if (!in->bone) return -1;   /* needs the type's model posed at creation */
        float p[3], a[3];
        wb_get(o, MU_OBJF_POSITION, p);
        wb_get(o, MU_OBJF_ANGLE, a);
        mu_obj_event *e = wb_event(log, MU_DEBENTER_POSE, index);   /* model +0x78 = position, then Animation */
        wb_vec(e, p);
        bone_into(in, 23, o, MU_OBJF_POINT_A);
        bone_into(in, 22, o, MU_OBJF_POINT_B);
        joint(log, index, p, a, 0x3c);
        joint(log, index, p, a, 0x3d);
    } else if (key >= 56 && key <= 67) {
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
    }
    return 1;
}
int mu_debenter_move(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!debenter_world(in)) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 9 || t == 11) {
        const uint8_t *r = q_action_at(in, o);
        if (!r) return -1;   /* the original copies the record without a test */
        if (q_action_ended(o, r)) {
            if (mu_obj_i32(o, DEBENTER_REST) <= 0) {
                mu_obj_set_i32(o, DEBENTER_REST, in->rand_fn(in->context) % 3 + 4);
                q_set_action(in, o, 1);
            } else {
                q_set_action(in, o, 0);
                mu_obj_set_i32(o, DEBENTER_REST, mu_obj_i32(o, DEBENTER_REST) - 1);
            }
        }
    } else if (t == 50) {
        float s = fabsf(q_sin((float)((double)in->time * 0.001)));   /* 0x0098a6d2 */
        s = s * 0.4f + 0.3f;
        const float l[3] = {s * 0.2f, s * 0.3f, s * 0.0f};
        q_add_light(log, index, mu_obj_f32(o, MU_OBJF_POSITION), mu_obj_f32(o, MU_OBJF_POSITION + 4), l, 2);
    }
    return 1;
}
static float client_abs(float x) { return 0.0f > x ? -x : x; }   /* 0x0184f8ff: keeps -0 and NaN */
int mu_debenter_visual_bones(int32_t type)
{
    switch (type) {
    case 9: return 23;
    case 11: return 27;
    case 21: return 4;
    case 27: case 31: return 1;
    default: return -1;
    }
}
/* rand % 10 * step + base, the light scale of types 58..62 and 66. */
static float pulse(const mu_q_inputs *in, float step, float base)
{
    return (float)(in->rand_fn(in->context) % 10) * step + base;
}
static void glow(mu_obj_log *log, int32_t i, const uint8_t *o, const mu_q_inputs *in, uint32_t bitmap,
                 const float l[3], uint32_t sub, float scale)
{
    float p[3], a[3];
    (void)in;
    wb_get(o, MU_OBJF_POSITION, p);
    wb_get(o, MU_OBJF_ANGLE, a);
    q_particle(log, i, bitmap, p, a, l, sub, scale, 1);
}
int mu_debenter_visual(uint8_t *o, int32_t i, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!debenter_world(in)) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (mu_debenter_visual_bones(t) >= 0 && !in->bone) return -1;
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    float p[3], a[3], ol[3];
    wb_get(o, MU_OBJF_POSITION, p);
    wb_get(o, MU_OBJF_ANGLE, a);
    wb_get(o, MU_OBJF_LIGHT, ol);
    switch (t) {
    case 9: {
        bone_into(in, 23, o, MU_OBJF_POINT_A);
        bone_into(in, 22, o, MU_OBJF_POINT_B);
        if (in->rand_fn(in->context) % 4 == 0) {
            in->bone(in->context, 8, zero3, p);
            p[2] = p[2] + 20.0f;
            for (int q = 0; q < 3; ++q)   /* 0x00d750fa(p, 20, p) */
                p[q] = (float)(in->rand_fn(in->context) % 41 - 20) + p[q];
            const float l[3] = {0.5f, 0.9f, 0.5f};
            q_particle(log, i, 0x7f5a, p, a, l, 0x52, scale, 0);
            q_particle(log, i, 0x7f5a, p, a, ol, 0xd, scale * 2.0f, 1);
        }
        for (int k = 0; k < 2; ++k) {
            wb_get(o, k ? MU_OBJF_POINT_B : MU_OBJF_POINT_A, p);
            p[2] = p[2] - 10.0f;
            const float l[3] = {0.05f, 0.6f, 0.2f}, white[3] = {1.0f, 1.0f, 1.0f};
            q_particle(log, i, 0x8089, p, a, l, 9, scale * 0.8f, 0);
            q_particle(log, i, 0x8089, p, a, white, 9, scale * 0.5f, 0);
        }
        break;
    }
    case 27: case 31: {
        in->bone(in->context, 1, zero3, p);
        const float s = client_abs(q_sin((float)((double)in->time * 0.0008))) * 0.6f + 0.1f;
        const float sc = scale * 0.3f * s;
        const float red[3] = {0.9f, 0.1f, 0.1f}, l[3] = {s, s, s};
        q_sprite(log, i, 0x7f6b, p, 0.4f, red, 0.0f);
        q_sprite(log, i, 0x7f6b, p, sc, l, 0.0f);
        break;
    }
    case 11: {
        const float s = q_sin((float)(wb_int(in->time) % 3000) * 0.0010466667590662837f) * 0.1f;
        in->bone(in->context, 27, zero3, p);   /* the original's local is uninitialized stack (zero here) */
        p[2] = p[2] + 20.0f;
        if (in->rand_fn(in->context) % 10 == 0) {
            const float l[3] = {0.5f, 0.9f, 0.5f};
            q_particle(log, i, 0x7f5a, p, a, l, 0x53, scale * 0.5f, 0);
            q_particle(log, i, 0x7f5a, p, a, ol, 0xd, scale * 2.0f, 1);
        }
        if (in->rand_fn(in->context) % 7 == 0) {
            const float l[3] = {0.6f, 1.0f, 1.0f};
            q_particle(log, i, 0x7efa, p, a, l, 2, 0.25f, 0);
        }
        const float l[3] = {0.2f, 0.65f, 0.65f};
        q_sprite(log, i, 0x7ef7, p, 1.5f + s, l, 0.0f);
        if (mu_obj_u16(o, MU_OBJF_ACTION) == 1) {
            const float c[3] = {0.3f, 0.95f, 0.95f};
            q_particle(log, i, 0x7f26, p, a, c, 0xe, 0.06f, 0);
        }
        break;
    }
    case 21: {
        const float s = client_abs(q_sin((float)((double)in->time * 0.0012))) * 0.5f + 0.3f;
        const float l[3] = {s * 0.05f, s * 0.3f, s * 0.6f};
        in->bone(in->context, 2, zero3, p);   /* uninitialized local in the original, as type 11 */
        q_sprite(log, i, 0x8155, p, 1.0f, l, 0.0f);
        in->bone(in->context, 3, zero3, p);
        q_sprite(log, i, 0x8155, p, 1.0f, l, 0.0f);
        in->bone(in->context, 4, zero3, p);
        const float sc = (float)((double)(in->rand_fn(in->context) % 5) * 0.03 + (double)0.2f);
        q_particle(log, i, 0x7f5a, p, a, l, 0x51, sc, 0);
        break;
    }
    case 56:
        if (in->rand_fn(in->context) % 10 == 0) {
            p[2] = p[2] + 50.0f;
            const float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f;
            const float l[3] = {s, s * 0.6f, s * 0.2f};
            q_particle(log, i, 0x7f5a, p, a, l, 0x21, scale, 0);
        }
        break;
    case 57:
        if (in->rand_fn(in->context) % 6 == 0) {
            const float l[3] = {0.02f, 0.03f, 0.02f};
            glow(log, i, o, in, 0x7f89, l, 9, scale);
        }
        break;
    case 58: case 59: case 60:
        if (in->rand_fn(in->context) % 5 == 0) {
            const float s = pulse(in, 0.004f, t == 59 ? 0.02f : 0.01f);
            float l[3] = {0.2109375f * s, 0.69140625f * s, 0.5859375f * s};
            if (t == 59) {
                l[0] = 0.29296875f * s; l[1] = 0.05859375f * s; l[2] = 0.05859375f * s;
            }
            glow(log, i, o, in, 0x7f89, l, 0x18, scale);
            if (t == 60) {
                const float m[3] = {0.86328125f * s, 0.47265625f * s, 0.78515625f * s};
                glow(log, i, o, in, 0x7f89, m, 0x18, scale);
            }
        }
        break;
    case 61: case 66:
        if (in->rand_fn(in->context) % 5 == 0) {
            const float s = pulse(in, 0.002f, 0.01f);
            float l[3] = {1.2f * s, 1.2f * s, 1.2f * s};
            if (t == 66) {
                l[0] = 0.12f * s; l[1] = 0.12f * s; l[2] = 0.6f * s;
            }
            glow(log, i, o, in, 0x7f89, l, 0x18, scale);
        }
        break;
    case 62:
        if (in->rand_fn(in->context) % 35 == 5) {
            const float s = pulse(in, 0.05f, 0.03f);
            const float l[3] = {1.0f * s, 1.0f * s, 1.0f * s};
            glow(log, i, o, in, 0x7dea, l, 0, scale);
        }
        break;
    case 63: {
        const float l[3] = {0.05f, 0.3f, 0.5f}, m[3] = {0.39f, 0.65f, 0.39f};
        q_particle(log, i, 0x8089, p, a, l, 9, scale, 0);
        q_particle(log, i, 0x8089, p, a, m, 9, scale * 0.5f, 0);
        break;
    }
    case 64:
        if (in->rand_fn(in->context) % 10 == 0) {
            const float l[3] = {0.5f, 0.9f, 0.5f};
            q_particle(log, i, 0x7f5a, p, a, l, 0x53, scale * 0.5f, 0);
        }
        break;
    case 65: {
        const int32_t phase = (int32_t)(in->now_ms % 1024u);   /* timeGetTime */
        if (in->rand_fn(in->context) % 5 == 1 && phase >= 0 && phase < 30) {
            const float l[3] = {0.1f, 0.1f, 0.1f};
            q_effect(log, i, o, 0x199, l, 0, (uint16_t)wb_int(scale));
        }
        break;
    }
    case 67:
        if (in->rand_fn(in->context) % 2 == 0) {
            const float l[3] = {0.4f, 0.4f, 0.4f};
            const float sc = scale * 0.6f;
            glow(log, i, o, in, 0x807e + (uint32_t)(in->rand_fn(in->context) % 3), l, 8, sc);
        }
        break;
    default: break;
    }
    return 1;
}
