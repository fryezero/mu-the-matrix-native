/* Vulcanus world 63: slots +2c 0x00e8ec09 and +30 0x00e8ec80. */
#include "worlds_g.h"
int mu_vulcanus_create(uint8_t *o, int32_t world)
{
    if (world != 63)
        return 0;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (type >= 0 && type <= 6) {
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        return 1;
    }
    if (type == 0x46) {
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        return 1;
    }
    if (type == 0x4a) {
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    }
    return 0;
}
int mu_vulcanus_move(uint8_t *o, int32_t world)
{
    if (world != 63)
        return 0;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (type >= 0 && type <= 6) {
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    }
    return 0;
}

/* Slot +34 0x00e8ece1. All seven emitter types, including ordered RNG use. */
#include "worlds_g_internal.h"
int mu_vulcanus_visual(uint8_t *o, int32_t index, int32_t world, int model_present, float time,
                       mu_obj_rand_fn random, void *context, mu_obj_log *log)
{
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (!model_present || world != 63 || type < 0 || type > 6)
        return 0;
    mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
    float a[3];
    wb_get(o, MU_OBJF_ANGLE, a);
    const float white[3] = {1.0f, 1.0f, 1.0f}, black[3] = {0.0f, 0.0f, 0.0f};
    switch (type) {
    case 0: {
        const float phase = (((float)sin((double)(time * 0.001f)) + 1.0f) * 0.5f) * 100.0f;
        const int32_t start = (wb_int(mu_obj_f32(o, MU_OBJF_POSITION)) % 3 + 1) * 30;
        const int32_t width = start == 90 ? 10 : 40;
        if (phase >= (float)start && phase <= (float)(start + width))
            for (int k = 0; k < 20; ++k)
                wg_particle(log, index, o, 0x801b, a, white, 6, 1);
        break;
    }
    case 1:
        if (random(context) % 3 == 0)
            wg_particle(log, index, o, 0x7f5a, a, white, 0x3c, 1);
        break;
    case 2:
        if (random(context) % 3 == 0)
            wg_particle(log, index, o, 0x7f89, a, black, 0x10, 1);
        break;
    case 3:
        if (random(context) % 4 == 0) {
            const float red = (float)(random(context) % 3) * 0.01f + 0.015f;
            const float light[3] = {red, 0.0f, 0.0f};
            wg_particle(log, index, o, 0x7f89, a, light, 0xb, 1);
        }
        break;
    case 4:
        if (random(context) % 3 == 0) {
            float p[3];
            wb_get(o, MU_OBJF_POSITION, p);
            /* Sequence points preserve the client's X-then-Z draws. */
            const float x = (float)(random(context) % 40 + 120);
            const float z = (float)(random(context) % 30);
            a[0] = x + a[0];
            a[1] = 0.0f + a[1];
            a[2] = z + a[2];
            mu_obj_event *e = wb_event(log, MU_ICARUS_JOINT, index);
            wb_arg(e, 0x7fd5);
            wb_vec(e, p);
            wb_vec(e, p);
            wb_vec(e, a);
            wb_arg(e, 4);
            wb_arg(e, 1);
            wb_float(e, mu_obj_f32(o, MU_OBJF_SCALE));
            const float light[3] = {1.0f, 0.4f, 0.4f};
            wg_particle(log, index, o, 0x7f25, a, light, 9, 0);
        }
        break;
    case 5:
        if (random(context) % 3 == 0) {
            const float light[3] = {0.3f, 0.3f, 0.3f};
            memcpy(o + MU_OBJF_LIGHT, light, sizeof light);
            wg_particle(log, index, o, 0x7f5a, a, light, 0x15, 0);
        }
        break;
    case 6: {
        const float light[3] = {1.0f, 0.2f, 0.0f};
        wg_sprite(log, index, o, 2.0f * mu_obj_f32(o, MU_OBJF_SCALE), light);
        switch (random(context) % 3) {
        case 0: wg_particle(log, index, o, 0x8084, a, white, 0, 0); break;
        case 1: wg_particle(log, index, o, 0x806e, a, white, 4, 0); break;
        case 2: wg_particle(log, index, o, 0x8085, a, white, 0, 0); break;
        }
        break;
    }
    }
    return 1;
}
