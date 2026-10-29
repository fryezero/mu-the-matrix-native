/* Swamp of Destruction, world 144. Create 0x00e46625, move 0x00e4696f, visual 0x00e47bc2; predicate 0x00e4bb8d. */
#include "worlds_r2.h"
#include "worlds_b_internal.h"
#include "icarus.h"
int mu_swamp_create(uint8_t *o, int32_t world)
{
    if (world != 144 || !o) return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 32: case 64:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        break;
    case 76:
        o[MU_OBJF_AFTER_CHARACTER] = 1; break;
    case 6: case 13: case 16: case 18: case 21: case 23: case 24: case 25: case 26: case 27: case 28: case 31:
    case 33: case 34: case 35: case 36: case 37: case 38: case 39: case 43: case 54: case 55: case 57: case 59:
    case 66: case 67: case 73: case 74: case 77: case 78: case 79: case 82: case 90: case 91: case 94: case 106:
    case 107: case 109: case 110: case 111: case 112: case 113: case 116: case 120: case 121: case 122: case 125:
    case 126: case 127: case 129: case 130: case 131: case 132: case 140: case 141: case 142: case 145: case 146:
    case 147: case 148: case 153: case 181: case 183: case 200:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f); break;
    default: break;
    }
    return 1;
}
int mu_swamp_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    if (in->world != 144 || !o) return 0;
    if (mu_obj_i32(o, MU_OBJF_TYPE) == 183) {
        const float base = 0.4f;
        float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f * base;
        s = s + base;
        wb_light(log, index, o, s * 1.0f, s * 0.2f, s * 0.1f, 3);
    }
    return 1;
}
/* Types 160-169 and 187-193: on rand % 50 == 0 the object's light, then CreateJoint 0x7f7d at the object. */
static const struct { int16_t type; uint8_t sub; float rgb[3]; } k_joints[] = {
    {160, 0x12, {0.93f, 0.11f, 0.14f}}, {161, 0x12, {0.17f, 0.8f, 0.3f}}, {162, 0x12, {0.0f, 0.6f, 0.9f}},
    {163, 0x12, {0.7f, 0.25f, 0.6f}}, {164, 0x12, {1.0f, 0.8f, 0.3f}}, {165, 0x19, {0.93f, 0.11f, 0.14f}},
    {166, 0x19, {0.17f, 0.8f, 0.3f}}, {167, 0x19, {0.0f, 0.6f, 0.9f}}, {168, 0x19, {0.7f, 0.25f, 0.6f}},
    {169, 0x19, {1.0f, 0.8f, 0.4f}}, {187, 0x1a, {1.0f, 0.65f, 0.0f}}, {188, 0x10, {1.0f, 0.65f, 0.0f}},
    {189, 0x11, {1.0f, 0.65f, 0.0f}}, {190, 0x18, {1.0f, 0.65f, 0.0f}}, {191, 0x19, {1.0f, 0.65f, 0.0f}},
    {192, 0x12, {1.0f, 0.65f, 0.0f}}, {193, 0x13, {1.0f, 0.65f, 0.0f}}};
int mu_swamp_visual(uint8_t *o, int32_t i, int has_model, mu_obj_rand_fn random, void *ctx, mu_obj_log *log)
{
    if (!o || !has_model) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    float p[3], a[3];
    wb_get(o, MU_OBJF_POSITION, p); wb_get(o, MU_OBJF_ANGLE, a);
    if (t == 185) {
        if (random(ctx) % 200 != 0) return 1;
        float l[3] = {0.01f, 0.25f, 0.01f};
        for (int k = 0; k < 3; ++k) {
            const double f = (double)(random(ctx) % 100) * 0.005 + 0.2;
            l[k] = (float)(f * (double)l[k]);
        }
        mu_obj_event *e = wb_event(log, MU_R2_EFFECT, i);
        wb_arg(e, 0x199); wb_vec(e, p); wb_vec(e, a); wb_vec(e, l); wb_arg(e, 1); wb_arg(e, 1);
        wb_arg(e, (uint16_t)wb_int(mu_obj_f32(o, MU_OBJF_SCALE)));
        return 1;
    }
    for (size_t k = 0; k < sizeof k_joints / sizeof k_joints[0]; ++k) {
        if (k_joints[k].type != t) continue;
        if (random(ctx) % 50 != 0) return 1;
        for (int q = 0; q < 3; ++q) mu_obj_set_f32(o, MU_OBJF_LIGHT + 4u * (uint32_t)q, k_joints[k].rgb[q]);
        mu_obj_event *e = wb_event(log, MU_ICARUS_JOINT, i);
        wb_arg(e, 0x7f7d); wb_vec(e, p); wb_vec(e, p); wb_vec(e, a);
        wb_arg(e, k_joints[k].sub); wb_arg(e, 1); wb_float(e, mu_obj_f32(o, MU_OBJF_SCALE));
        return 1;
    }
    return 1;
}
