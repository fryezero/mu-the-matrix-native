/* Deep Dungeon 1-5, worlds 116-120. Create 0x00e3e34b/0x00e3efe6/0x00e3fce8/0x00e409e8/0x00e41823,
 * move 0x00e3e46d/0x00e3f125/0x00e3fe3c/0x00e40b38/0x00e41a1f. Neither has a world predicate. */
#include "worlds_n.h"
#include "worlds_b_internal.h"
static int far_range(int32_t world, int32_t t)
{
    switch (world) {
    case 116: return t == 6;
    case 117: return t == 0 || t == 1 || t == 3 || t == 50;
    case 118: return t == 0 || t == 3 || t == 5 || t == 6 || t == 23 || t == 50;
    case 119: return t == 0 || t == 5 || t == 18 || t == 35 || t == 50;
    case 120: return (t >= 0 && t <= 7) || t == 9 || t == 10 || t == 11 || t == 14 || (t >= 20 && t <= 24) ||
                     t == 30 || t == 36 || t == 37 || t == 48 || t == 50 || t == 53;
    default: return 0;
    }
}
int mu_deep_dungeon_create(uint8_t *o, int32_t index, int32_t world, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (far_range(world, t)) {
        mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f);
        return 1;
    }
    switch (t) {
    case 39: case 40: case 51: case 52: case 62: case 63: case 64: case 65: case 66: case 67:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    case 59:
        wb_arg(wb_event(log, MU_OBJ_CALL_REGISTER, index), 1);
        return 1;
    case 60:
        wb_arg(wb_event(log, MU_OBJ_CALL_REGISTER, index), 1);
        mu_obj_set_f32(o, MU_OBJF_BOX_MAX, 40.0f);
        mu_obj_set_f32(o, MU_OBJF_BOX_MAX + 4, 40.0f);
        mu_obj_set_f32(o, MU_OBJF_BOX_MAX + 8, 160.0f);
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    default:
        return 0;
    }
}
int mu_deep_dungeon_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t >= 62 && t <= 67) {
        static const float k[6][3] = {{0.12f, 0.58f, 0.32f}, {0.1f, 0.41f, 0.8f}, {1.0f, 0.6f, 0.2f},
                                      {0.74f, 0.17f, 0.62f}, {0.77f, 0.74f, 0.63f}, {0.8f, 0.3f, 0.04f}};
        const float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f;
        const float *c = k[t - 62];
        /* Type 64's red factor is the unscaled s (no multiply in the original). */
        wb_light(log, index, o, t == 64 ? s : s * c[0], s * c[1], s * c[2], 3);
        return 1;
    }
    switch (t) {
    case 22: case 23: case 24:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, -(float)(wb_int(in->time) % 1000) * 0.001f);
        return 1;
    case 41: case 42:
        return 1;
    case 52:
        if (in->rand_fn(in->context) % 3 == 0) {
            float p[3], a[3], l[3];
            wb_get(o, MU_OBJF_POSITION, p); wb_get(o, MU_OBJF_ANGLE, a); wb_get(o, MU_OBJF_LIGHT, l);
            mu_obj_event *e = wb_event(log, MU_DEEP_DUNGEON_KEYED_EFFECT, index);
            wb_arg(e, 0x43a); wb_vec(e, p); wb_vec(e, a); wb_vec(e, l);
            wb_arg(e, 0); wb_arg(e, 0);
            wb_arg(e, (uint16_t)wb_int(mu_obj_f32(o, MU_OBJF_SCALE)));
        }
        return 1;
    default:
        return 0;
    }
}
int mu_worlds_n_visual(const uint8_t *o, int32_t index)
{
    (void)o; (void)index;
    return 0;
}
