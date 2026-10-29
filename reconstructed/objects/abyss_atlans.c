/* Abyss of Atlans 1-3, worlds 128-130. Create 0x00d5cf32/0x00d5ebd2/0x00d60316,
 * move 0x00d5d04a/0x00d5ecea/0x00d6042e, visual 0x00d5d564/0x00d5f1f1/0x00d60948.
 * The three bodies differ only in the world constant. */
#include "worlds_o.h"
#include "worlds_b_internal.h"
#include <math.h>
int mu_abyss_create(int32_t cls, uint8_t *o, int32_t world)
{
    if (world != cls || !o) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 23: case 38: case 40: case 41: case 44: case 50:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    default:
        /* 161..167 by compares, 168..180 by the jump table, whose 173/174 entries are the default. */
        if (t >= 161 && t <= 180 && t != 173 && t != 174)
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    }
    return 1;
}
static float pulse(float time, float rate, float amplitude)
{
    return (float)sin((double)(time * rate)) * amplitude + 0.5f;
}
int mu_abyss_move(int32_t cls, uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    if (in->world != cls || !o) return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 22: {
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        mu_obj_set_f32(o, MU_OBJF_TIMER, mu_obj_f32(o, MU_OBJF_TIMER) + 0.1f);
        if (mu_obj_f32(o, MU_OBJF_TIMER) > 10.0f) mu_obj_set_f32(o, MU_OBJF_TIMER, 0.0f);
        if (mu_obj_f32(o, MU_OBJF_TIMER) > 5.0f) {
            float v[3];
            mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, index);
            wb_arg(e, 0x7fcd);
            wb_get(o, MU_OBJF_POSITION, v); wb_vec(e, v);
            wb_get(o, MU_OBJF_ANGLE, v); wb_vec(e, v);
            wb_get(o, MU_OBJF_LIGHT, v); wb_vec(e, v);
            wb_arg(e, 0); wb_float(e, 1.0f); wb_arg(e, 0);
        }
        break;
    }
    case 23:
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, pulse(in->time, 0.002f, 0.3f));
        break;
    case 32: case 34: case 66: case 67: case 68: case 69: case 70:
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 1);
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, pulse(in->time, 0.004f, 0.5f));
        break;
    case 38:
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        break;
    case 40:
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, pulse(in->time, 0.004f, 0.3f));
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.05f);
        break;
    default: break;
    }
    return 1;
}
int mu_abyss_visual(int32_t cls, uint8_t *o, int32_t world, int model_present)
{
    if (world != cls || !o || !model_present) return 0;
    if (mu_obj_i32(o, MU_OBJF_TYPE) == 39)
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
    return 1;
}
