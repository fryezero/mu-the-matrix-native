/* Test Area, world 121 (vtable 0x01aa51fc): create 0x00d585b0, move 0x00d58809, visual 0x00d58888. None of the
 * three tests the world; the move's default case calls the empty base method 0x00d5c7a9 before returning false. */
#include "worlds_s3.h"
#include "worlds_q_internal.h"

/* CreateEffect(type, (x, y + dy, z + 520), o + 0x164, o + 0xec, 1, 0, -1, 0, 0, 0, 0.0, -1, 0, 0), logged as
 * object_render.c's create effects are: type, position, angle offset, light offset, subtype, then the tail. */
static void warp_effect(mu_obj_log *log, int32_t i, const uint8_t *o, uint32_t type, float dy)
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_CREATE_EFFECT, i);
    wb_arg(e, type);
    wb_float(e, mu_obj_f32(o, MU_OBJF_POSITION));
    wb_float(e, mu_obj_f32(o, MU_OBJF_POSITION + 4) - dy);
    wb_float(e, mu_obj_f32(o, MU_OBJF_POSITION + 8) + 520.0f);
    static const uint32_t rest[12] = {MU_OBJF_ANGLE, MU_OBJF_LIGHT, 1, 0, 0xffffffffu, 0, 0, 0, 0, 0xffffffffu, 0, 0};
    for (int k = 0; k < 12; ++k)
        wb_arg(e, rest[k]);
}

int mu_test_area_create(const uint8_t *o, int32_t i, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 0x1a8)
        return 1;
    if (t != 0x1ab)
        return 0;
    warp_effect(log, i, o, 0x1ab, 40.0f);
    warp_effect(log, i, o, 0x1ac, 36.0f);
    warp_effect(log, i, o, 0x1ad, 20.0f);
    return 1;
}

int mu_test_area_move(uint8_t *o, float time)
{
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 22:
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, q_sin(time * 0.001f) + 1.0f);
        return 1;
    case 70: case 80:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    default:
        return 0;
    }
}

int mu_test_area_visual(const uint8_t *o, int32_t i, int has_model, mu_obj_rand_fn rnd, void *context,
                        mu_obj_log *log)
{
    if (!has_model)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t != 70 && t != 80)
        return 0;
    const float blue[3] = {0.1f, 0.4f, 1.0f}, red[3] = {0.7f, 0.2f, 0.1f};
    const float *l = t == 70 ? blue : red;
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    float p[3], a[3];
    wb_get(o, MU_OBJF_POSITION, p);
    wb_get(o, MU_OBJF_ANGLE, a);
    const int32_t r = rnd(context) % 3;
    if (r == 0) q_particle(log, i, 0x8086, p, a, l, 2, scale, 0);
    else if (r == 1) q_particle(log, i, 0x8087, p, a, l, 6, scale, 0);
    else if (r == 2) q_particle(log, i, 0x8089, p, a, l, 2, scale, 0);
    q_particle(log, i, 0x8086, p, a, l, 2, scale, 0);
    return 1;
}
