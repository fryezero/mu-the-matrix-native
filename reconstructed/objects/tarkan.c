/* MoveObject world 8: 0x01800bf8..0x018013a0. */
#include "worlds_b_internal.h"
static float wave(float t)
{
    const float s = (float)sin((double)(t * 0.002f));
    return s * 0.35f + 0.65f;
}
void mu_tarkan_move(uint8_t *o, int32_t i, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    float l;
    switch (t) {
    case 2:
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        mu_obj_set_f32(o, MU_OBJF_BLEND_U, wb_scroll(in->time, 1000, 0.001f));
        break;
    case 4:
        l = wave(in->time);
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, l);
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, wb_scroll(in->time, 10000, 0.0001f));
        wb_light(log, i, o, l, l, l, 3);
        break;
    case 7:
        l = wave(mu_obj_f32(o, MU_OBJF_ANGLE + 8) * 100.0f + in->time);
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, l);
        wb_light(log, i, o, l, l * 0.6f, l * 0.2f, 3);
        break;
    case 0xc:
        mu_obj_set_f32(o, MU_OBJF_BLEND_U, wb_scroll(in->time, 50000, 0.00005f));
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, wb_scroll(in->time, 50000, 0.00005f));
        break;
    case 0xb:
    case 0xd:
    case 0x49:
    case 0x4b:
    case 0x4f:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, wb_scroll(in->time, 10000, 0.0002f));
        break;
    case 0x3d:
    case 0x41:
    case 0x42:
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 1);
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, wb_scroll(in->time, 1000, 0.001f));
        l = wave(in->time);
        wb_light(log, i, o, l, l * 0.6f, l * 0.2f, 2);
        break;
    case 0x3f:
    case 0x40:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    case 0x48:
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, wb_scroll(in->time, 10000, 0.0002f));
        break;
    case 0x52:
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        for (uint32_t k = 0; k < 12; k += 4)
            mu_obj_set_f32(o, MU_OBJF_LIGHT + k, 1);
        break;
    case 0x5d:
    case 0x5e: {
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        /* 0x0185bdc4(-1,0), cosine of the signed clock phase. */
        const float phase = (float)(wb_int(in->time) % -6283) * 0.001f * -1.0f;
        float c = (float)cos((double)phase);
        if (phase < 3.1415927410125732f)
            c = -c;
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, ((c + 1.0f) * 0.5f) * 0.3f + 0.7f);
        break;
    }
    default:
        break;
    }
}
