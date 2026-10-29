/* Twisted Karutan, world 142. Create 0x00e67546, move 0x00e6766a, visual 0x00e6841f; predicate 0x00e6bd5a. */
#include "worlds_r2.h"
#include "worlds_b_internal.h"
#include <math.h>
static float client_abs(float x) { return 0.0f > x ? -x : x; }   /* 0x0184f8ff: keeps -0 and NaN */
int mu_twisted_karutan_create(uint8_t *o, int32_t world)
{
    if (world != 142 || !o) return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 1: case 3: case 54: case 55: case 56: case 57: case 58: case 62: case 66: case 119: case 120: case 121:
    case 122: case 123: case 124: case 125: case 162: case 163: case 167: case 168: case 169: case 170: case 171:
    case 172: case 173: case 174: case 175: case 176: case 177: case 178: case 197: case 198:
        o[MU_OBJF_AFTER_CHARACTER] = 1; break;
    default: break;
    }
    return 1;
}
int mu_twisted_karutan_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    if (in->world != 142 || !o) return 0;
    if (mu_obj_i32(o, MU_OBJF_TYPE) == 160) {
        const float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f;
        wb_light(log, index, o, s, s * 0.6f, s * 0.2f, 2);
    }
    return 1;
}
static void sprite(mu_obj_log *log, int32_t i, uint32_t type, const float p[3], float scale, const float l[3])
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_SPRITE, i);
    wb_arg(e, type); wb_vec(e, p); wb_float(e, scale); wb_vec(e, l);
    wb_float(e, 0.0f); wb_arg(e, 1); wb_arg(e, 0); wb_arg(e, 4);
}
static void particle(mu_obj_log *log, int32_t i, uint32_t type, const float p[3], const float a[3],
                     const float l[3], uint32_t sub, float scale, uint32_t owner)
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, i);
    wb_arg(e, type); wb_vec(e, p); wb_vec(e, a); wb_vec(e, l); wb_arg(e, sub); wb_float(e, scale); wb_arg(e, owner);
}
int mu_twisted_karutan_visual(uint8_t *o, int32_t i, int has_model, float time, mu_obj_rand_fn random,
                              mu_login_bone_fn bone, void *ctx, mu_obj_log *log)
{
    if (!o || !has_model) return 0;
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    float p[3], a[3], l[3];
    wb_get(o, MU_OBJF_POSITION, p); wb_get(o, MU_OBJF_ANGLE, a);
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 72: {
        if (!bone) return 1;   /* no posed bones: the host counts the refusal */
        const float local[3] = {20.0f, 0.0f, 0.0f};
        const float s = client_abs((float)sin((double)(float)((double)time * 0.0004))) * 0.4f;
        const float bright[3] = {s * 1.3f, s * 1.3f, s * 1.9f}, dim[3] = {0.15f, 0.15f, 0.15f};
        float b[3] = {0, 0, 0};
        bone(ctx, 11, local, b);
        sprite(log, i, 0x7ef7, b, 2.0f, bright);
        sprite(log, i, 0x7f26, b, 1.5f, dim);
        bone(ctx, 7, local, b);
        sprite(log, i, 0x7f26, b, 4.0f, bright);
        sprite(log, i, 0x7f26, b, 1.5f, dim);
        break;
    }
    case 113: {
        const float red[3] = {1.0f, 0.2f, 0.0f}, white[3] = {1.0f, 1.0f, 1.0f};
        sprite(log, i, 0x7ef7, p, 2.0f * scale, red);
        switch (random(ctx) % 3) {
        case 0: particle(log, i, 0x8084, p, a, white, 0, scale, 0); break;
        case 1: particle(log, i, 0x806e, p, a, white, 4, scale, 0); break;
        default: particle(log, i, 0x8085, p, a, white, 0, scale, 0); break;
        }
        break;
    }
    case 114:
        if (random(ctx) % 3 == 0) {
            const float grey[3] = {0.2f, 0.2f, 0.2f};
            particle(log, i, 0x801c, p, a, grey, 0x10, scale, 0);
        }
        break;
    case 115:
        if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2) {
            const float faint[3] = {0.04f, 0.04f, 0.04f};
            for (int k = 0; k < 20; ++k) particle(log, i, 0x7f89, p, a, faint, 0x1d, scale, 1);
        }
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    case 116:
        if (random(ctx) % 8 == 0) {
            const float green[3] = {0.5f, 0.9f, 0.5f};
            particle(log, i, 0x7f5a, p, a, green, 0x45, scale, 0);
            wb_get(o, MU_OBJF_LIGHT, l);
            particle(log, i, 0x7f5a, p, a, l, 0x15, scale * 2.0f, 1);
        }
        break;
    case 118:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    case 196:
        if (random(ctx) % 50 == 1) {
            const float dark[3] = {0.1f, 0.1f, 0.1f};
            mu_obj_event *e = wb_event(log, MU_R2_EFFECT, i);
            wb_arg(e, 0x199); wb_vec(e, p); wb_vec(e, a); wb_vec(e, dark); wb_arg(e, 0); wb_arg(e, 1);
            wb_arg(e, (uint16_t)wb_int(scale));
        }
        break;
    default: break;
    }
    return 1;
}
