/* Duel Arena, world 64: 0x00dc6643 / 0x00dc6685 / 0x00dc6790. */
#include "worlds_h.h"
#include "worlds_g_internal.h"
int mu_duel_create(uint8_t *o)
{
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (type == 0 || type == 1 || type == 32) {
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        return 1;
    }
    return 0;
}
int mu_duel_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    if (in->world != 64)
        return 0;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (type == 34) {
        const float strength = (float)(in->rand_fn(in->context) % 3 + 5) * 0.1f;
        wb_light(log, index, o, strength * 0.9f, strength * 0.2f, strength * 0.1f, 3);
    }
    if (type == 34 || type == 35 || type == 36)
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
    return 0;
}
int mu_duel_visual(const uint8_t *o, int32_t index, int model_present,
                    mu_obj_rand_fn random, void *context, mu_obj_log *log)
{
    if (!model_present)
        return 0;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    const float white[3] = {1, 1, 1};
    float angle[3];
    wb_get(o, MU_OBJF_ANGLE, angle);
    if (type == 35 && random(context) % 3 == 0)
        wg_particle(log, index, o, 0x7f5a, angle, white, 22, 1);
    if (type == 36) {
        const float orange[3] = {1, 0.2f, 0};
        wg_sprite(log, index, o, 2.0f * mu_obj_f32(o, MU_OBJF_SCALE), orange);
        const int32_t choice = random(context) % 3;
        wg_particle(log, index, o, choice == 0 ? 0x8084 : choice == 1 ? 0x806e : 0x8085,
                    angle, white, choice == 1 ? 4u : 0u, 0);
    }
    return 0;
}
