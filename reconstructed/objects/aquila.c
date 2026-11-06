/* Aquila's Temple, world 145. Create 0x00d75a6c, move 0x00d75ac6, visual 0x00d77b3e; no world predicate. */
#include "worlds_s.h"
#include "worlds_b_internal.h"
int mu_aquila_create(uint8_t *o, int32_t world)
{
    (void)world;
    if (!o) return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 51: case 99: case 120: case 143: case 148:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -150.0f); break;
    default: break;
    }
    return 1;
}
static void point_light(mu_obj_log *log, int32_t i, const uint8_t *o, const float *l, int32_t range)
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_ADD_LIGHT, i);
    wb_float(e, mu_obj_f32(o, MU_OBJF_POINT_A));
    wb_float(e, mu_obj_f32(o, MU_OBJF_POINT_A + 4));
    wb_vec(e, l);
    wb_arg(e, (uint32_t)range);
}
int mu_aquila_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    if (!o) return 0;
    o[MU_OBJF_AFTER_CHARACTER] = 0.9f > mu_obj_f32(o, MU_OBJF_ALPHA) ? 1 : 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 90) {
        const float base = 0.4f;
        float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f * base;
        s = s + base;
        wb_light(log, index, o, s * 0.1f, s * 0.41f, s * 0.8f, 2);
        return 1;
    }
    if (t == 152) {
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        return 1;
    }
    if (!mu_aquila_bone_type(t)) return 1;
    const float base = 0.6f;
    float s = (float)(in->rand_fn(in->context) % 2 + 4) / 5.0f;
    s = (1.0f - base) * s;
    s = s + base;
    float l[3];
    int32_t range = 2;
    switch (t) {
    case 139: l[0] = s * 0.74f; l[1] = s * 0.17f; l[2] = s * 0.62f; break;
    case 140: l[0] = s * 1.2f; l[1] = s * 0.84f; l[2] = s * 0.53f; break;
    case 136: l[0] = s; l[1] = s * 0.22f; l[2] = s * 0.1f; break;
    case 137: l[0] = s * 0.1f; l[1] = s * 0.41f; l[2] = s * 0.8f; break;
    case 138: l[0] = s * 0.12f; l[1] = s * 0.58f; l[2] = s * 0.32f; break;
    default: range = 3; l[0] = s; l[1] = s; l[2] = s * 0.6f; break;   /* 142 */
    }
    point_light(log, index, o, l, range);
    return 1;
}
int mu_aquila_bone_type(int32_t type) { return (type >= 136 && type <= 140) || type == 142; }
int mu_aquila_visual(uint8_t *o, int has_model, const float *bone6)
{
    if (!o || !has_model) return 0;
    if (mu_aquila_bone_type(mu_obj_i32(o, MU_OBJF_TYPE)) && bone6) {
        mu_obj_set_f32(o, MU_OBJF_POINT_A, bone6[12]);
        mu_obj_set_f32(o, MU_OBJF_POINT_A + 4, bone6[13]);
    }
    return 1;
}
