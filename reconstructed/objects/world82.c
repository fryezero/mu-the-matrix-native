/* World-82 class: 0x00e2bf57 / 0x00e2bf8d / 0x00e2c002. */
#include "worlds_h.h"
#include "worlds_g_internal.h"
#include "charsel_world.h"
int mu_world82_create(uint8_t *o)
{
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (type >= 0 && type <= 6) {
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        return 1;
    }
    return 0;
}
int mu_world82_move(uint8_t *o, int32_t world)
{
    if (world < 82 || world > 90)
        return 0;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if ((type >= 0 && type <= 6) || type == 47 || type == 48) {
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    }
    return 0;
}
int mu_world82_visual(uint8_t *o, int32_t index, int32_t world, int model_present, float time,
                      mu_obj_rand_fn random, void *context, mu_obj_log *log)
{
    if (!model_present || world < 82 || world > 90)
        return 0;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    float angle[3], p[3];
    wb_get(o, MU_OBJF_ANGLE, angle);
    wb_get(o, MU_OBJF_POSITION, p);
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    const float warm[3] = {0.9f, 0.2f, 0.2f}, white[3] = {1, 1, 1};
    if (type >= 0 && type <= 6)
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
    switch (type) {
    case 0: {
        const float pulse = ((float)sin((double)(time * 0.001f)) + 1.0f) * 0.5f * 100.0f;
        const int32_t start = (wb_int(p[0]) % 3 + 1) * 30;
        const int32_t width = start == 90 ? 10 : 40;
        if (pulse >= (float)start && pulse <= (float)(start + width))
            for (int k = 0; k < 20; ++k)
                wg_particle(log, index, o, 0x801b, angle, warm, 7, 1);
        return 1;
    }
    case 1:
        if (random(context) % 3 == 0)
            wg_particle(log, index, o, 0x7f5a, angle, warm, 69, 1);
        return 1;
    case 2: {
        const float black[3] = {0, 0, 0};
        if (random(context) % 3 == 0)
            wg_particle(log, index, o, 0x7f89, angle, black, 16, 1);
        return 1;
    }
    case 3:
        if (random(context) % 4 == 0) {
            const float light[3] = {(float)(random(context) % 3) * 0.01f + 0.015f, 0, 0};
            wg_particle(log, index, o, 0x7f89, angle, light, 11, 1);
        }
        return 1;
    case 4: {
        const int32_t phase = wb_int(time) % 200;
        if (phase >= 0 && phase <= 5) {
            const int32_t count = random(context) % 4 + 4;
            const float light[3] = {0.5f, 0.5f, 0.5f};
            for (int32_t k = 0; k < count; ++k) {
                mu_obj_event *e = wb_event(log, MU_OBJ_CALL_EFFECT, index);
                wb_arg(e, 0x7f42); wb_vec(e, p); wb_vec(e, angle); wb_vec(e, light);
                wb_arg(e, 7); wb_arg(e, 0); wb_float(e, scale);
            }
        }
        return 1;
    }
    case 5:
        if (random(context) % 3 == 0) {
            const float light[3] = {0.3f, 0.3f, 0.3f};
            memcpy(o + MU_OBJF_LIGHT, light, sizeof light);
            wg_particle(log, index, o, 0x7f5a, angle, light, 21, 0);
        }
        return 1;
    case 6: {
        const float orange[3] = {1, 0.2f, 0};
        wg_sprite(log, index, o, 2.0f * scale, orange);
        const int32_t choice = random(context) % 3;
        wg_particle(log, index, o, choice == 0 ? 0x8084 : choice == 1 ? 0x806e : 0x8085,
                    angle, white, choice == 1 ? 4u : 0u, 0);
        return 1;
    }
    case 47: {
        const float blue[3] = {0.1f, 0.4f, 1};
        const int32_t choice = random(context) % 3;
        wg_particle(log, index, o, choice == 0 ? 0x8086 : choice == 1 ? 0x8087 : 0x8089,
                    angle, blue, choice == 1 ? 6u : 2u, 0);
        wg_particle(log, index, o, 0x8086, angle, blue, 2, 0);
        return 1;
    }
    case 48:
        if (random(context) % 3 == 0) {
            const int32_t diameter = wb_int(scale * 60.0f);
            /* The x86 method traps for a zero divisor. Do not invoke C undefined behavior. */
            if (!diameter)
                return 1;
            p[0] += (float)(random(context) % diameter - diameter / 2);
            p[1] += (float)(random(context) % diameter - diameter / 2);
            const float light[3] = {0.6f, 0.8f, 1};
            mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, index);
            wb_arg(e, 0x7ef7); wb_vec(e, p); wb_vec(e, angle); wb_vec(e, light);
            wb_arg(e, 15); wb_float(e, scale); wb_arg(e, 1);
        }
        return 1;
    default:
        return 0;
    }
}
