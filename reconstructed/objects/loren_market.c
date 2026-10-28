/* Loren Market, world 79. Slots 0x00e6c0ec/0x00e6c1bf/0x00e6c678. */
#include "worlds_i.h"
#include "worlds_g_internal.h"
#include "world_visual_internal.h"
int mu_market_create(uint8_t *o, int32_t index, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 50: case 51: case 52: case 53: case 59:
        o[MU_OBJF_LIGHT_ENABLE] = 0;
        break;
    case 67:
        wb_arg(wb_event(log, MU_OBJ_CALL_REGISTER, index), 1);
        mu_obj_set_f32(o, MU_OBJF_BOX_MAX, 100);
        mu_obj_set_f32(o, MU_OBJF_BOX_MAX + 4, 100);
        mu_obj_set_f32(o, MU_OBJF_BOX_MAX + 8, 160);
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    case 68: o[MU_OBJF_AFTER_CHARACTER] = 1; break;
    default: break;
    }
    return 0;
}
int mu_market_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    if (in->world != 79)
        return 0;
    mu_obj_alpha_step(o);
    if (0.01f > mu_obj_f32(o, MU_OBJF_ALPHA) || !in->has_model)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 8) {
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.2f);
        return 1;
    }
    if (t == 30 || t == 35) {
        const float rate = t == 30 ? 0.002f : 0.039f;
        const float s = ((float)sin((double)(in->time * rate)) + 1.0f) * 0.2f + 0.6f;
        /* This service includes the original BMD body origin/scale write,
         * Animation(...,0,1), and zero-local TransformPosition at bone 1 or 2. */
        mu_obj_event *e = wb_event(log, MU_MARKET_BONE_LIGHT, index);
        wb_arg(e, t == 30 ? 1u : 2u);
        wb_float(e, s * 0.7f); wb_float(e, s * 0.5f); wb_float(e, s * 0.2f);
        wb_arg(e, t == 30 ? 3u : 1u);
        return 1;
    }
    if (t >= 54 && t <= 58) {
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    }
    return 0;
}
int mu_market_visual(const uint8_t *o, int32_t index, int32_t world, float time,
                     mu_obj_rand_fn random, mu_login_bone_fn bone, void *context, mu_obj_log *log)
{
    if (world != 79)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    const float zero[3] = {0, 0, 0}, white[3] = {1, 1, 1};
    float a[3], p[3];
    wb_get(o, MU_OBJF_ANGLE, a);
    if (t == 30 || t == 35) {
        if (!bone) return 0; /* Native missing-pose boundary, not an original model gate. */
        const float s = ((float)sin((double)(time * (t == 30 ? 0.002f : 0.039f))) + 1.0f) * 0.2f + 0.6f;
        const float l[3] = {s * (t == 30 ? 0.5f : 0.7f), s * (t == 30 ? 0.5f : 0.7f), s * (t == 30 ? 0.5f : 0.7f)};
        for (int32_t k = t == 30 ? 1 : 2; k <= (t == 30 ? 3 : 2); ++k) {
            bone(context, k, zero, p);
            wv_sprite(index, 0x7f78, p, 1.5f * scale, l, log);
        }
        return 1;
    }
    switch (t) {
    case 54:
        {
            mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, index);
            wb_arg(e, 0x801e);
            wb_get(o, MU_OBJF_POSITION, p); wb_vec(e, p); wb_vec(e, a); wb_vec(e, zero);
            wb_arg(e, 0); wb_float(e, 1); wb_arg(e, 0);
        }
        return 1;
    case 55: wg_particle(log, index, o, 0x801c, a, white, 8, 0); return 1;
    case 56:
        if (random(context) % 8 == 0) wg_particle(log, index, o, 0x801b, a, white, 4, 0);
        return 1;
    case 57: {
        const float orange[3] = {1, 0.2f, 0};
        wg_sprite(log, index, o, 2.0f * scale, orange);
        const int32_t choice = random(context) % 3;
        wg_particle(log, index, o, choice == 0 ? 0x8084 : choice == 1 ? 0x806e : 0x8085,
                    a, white, choice == 1 ? 4u : 0u, 0);
        return 1;
    }
    case 58: {
        const float s = ((float)sin((double)(time * 0.005f)) + 1.0f) * 0.3f + 0.5f;
        const float l[3] = {s * 0.4f, s * 0.4f, s * 0.2f};
        wb_get(o, MU_OBJF_POSITION, p);
        wv_sprite(index, 0x7ef7, p, 20.0f * scale, l, log);
        return 1;
    }
    default: return 0;
    }
}
