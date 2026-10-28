/* Elbeland hook 0x00e30b86 and ambient sound helper 0x00e34169. */
#include "worlds_b_internal.h"
void mu_elbeland_move(uint8_t *o, int32_t i, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    uint32_t sound = 0;
    int safe_gated = 0;
    switch (t) {
    case 2:
        sound = 0x317;
        safe_gated = 1;
        break;
    case 0x35:
        sound = 0x318;
        safe_gated = 1;
        break;
    case 0x38:
        sound = 0x319;
        break;
    case 0x3b:
        sound = 0x314;
        safe_gated = 1;
        break;
    case 0x55:
        sound = 0x316;
        break;
    case 0x59:
        sound = 0x315;
        safe_gated = 1;
        break;
    case 0x6e:
        sound = 0x313;
        break;
    default:
        break;
    }
    /* owner word 1 denotes this object, normalized by the instruction oracle. */
    if (sound && (!safe_gated || !in->hero_safe))
        wb_sound(log, i, sound, 1, 1);
    switch (t) {
    case 0:
    case 0x3d: {
        const float l = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f;
        wb_light(log, i, o, t == 0 ? l : l * 0.2f, l * 0.6f, t == 0 ? l * 0.2f : l, 3);
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    }
    case 2:
    case 0x35:
    case 0x37:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) + 0.015f);
        break;
    case 0x36:
    case 0x3a:
    case 0x3b:
    case 0x3c:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    case 0x38:
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, (float)sin((double)(in->time * 0.003f)) * 0.3f + 0.5f);
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.05f);
        break;
    case 0x59:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) + 0.005f);
        break;
    case 0x3e:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        if (in->elbeland_pool)
            mu_elbeland_pool(in->elbeland_pool, o, in->rand_fn, in->context);
        break;
    default:
        break;
    }
}
/* Fixed boid pool slot 1 created by type 0x3e, 0x00e30f13..0x00e31165. */
void mu_elbeland_pool(uint8_t *p, const uint8_t *o, mu_obj_rand_fn rnd, void *ctx)
{
    if (p[MU_OBJF_LIVE])
        return;
    p[MU_OBJF_LIVE] = 1;
    mu_obj_set_f32(p, MU_OBJF_VELOCITY, 0);
    p[5] = 1;
    mu_obj_set_i32(p, 0x6c, 0);
    mu_obj_set_i32(p, 0x60, 1);
    for (uint32_t k = 0; k < 12; k += 4)
        mu_obj_set_f32(p, MU_OBJF_LIGHT + k, 0.5f);
    mu_obj_set_f32(p, MU_OBJF_ALPHA, 0);
    mu_obj_set_f32(p, MU_OBJF_ALPHA_TARGET, 1);
    mu_obj_set_f32(p, 0xc8, 10.0f * mu_obj_f32(o, MU_OBJF_SCALE));
    p[0xc] = 1;
    mu_obj_set_f32(p, MU_OBJF_SCALE, 0.5f);
    mu_obj_set_f32(p, MU_OBJF_C4, mu_obj_f32(o, MU_OBJF_POSITION + 8) > 100.0f ? 30.0f : 0);
    mu_obj_set_i32(p, MU_OBJF_HIDDEN_MESH, -1);
    mu_obj_set_i32(p, MU_OBJF_BLEND_MESH, -1);
    mu_obj_set_f32(p, MU_OBJF_TIMER, (float)(rnd(ctx) % 314) * 0.01f);
    mu_obj_set_i32(p, MU_OBJF_TYPE, 0x1a3);
    memset(p + MU_OBJF_ANGLE, 0, 12);
    memcpy(p + MU_OBJF_POSITION, o + MU_OBJF_POSITION, 12);
}
