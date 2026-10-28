/* Santa Village world 62: slots +2c 0x00e4231c and +30 0x00e42370. */
#include "worlds_g.h"
int mu_santa_create(uint8_t *o)
{
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x0c: case 0x0d: case 0x12: case 0x13: case 0x15: case 0x19:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        return 1;
    default:
        return 0;
    }
}
int mu_santa_move(uint8_t *o, int32_t world)
{
    if (world != 62)
        return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x10:
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.06f);
        return 1;
    case 0x1a: case 0x1b: case 0x1c:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    default:
        return 0;
    }
}

/* Slot +34 0x00e423d8. Model is a presence gate only; there is no world check. */
#include "worlds_g_internal.h"
int mu_santa_visual(const uint8_t *o, int32_t index, int model_present, float time, mu_obj_log *log)
{
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (!model_present || type < 0x1a || type > 0x1c)
        return 0;
    const float pulse = ((float)sin((double)(time * 0.005f)) + 1.0f) * 0.1f + 0.9f;
    const float light[3] = {pulse * (type == 0x1a ? 0.8f : 0.0f),
                            pulse * (type == 0x1c ? 0.6f : 0.2f),
                            pulse * (type == 0x1b ? 0.8f : type == 0x1c ? 0.6f : 0.0f)};
    wg_sprite(log, index, o, 8.0f * mu_obj_f32(o, MU_OBJF_SCALE), light);
    return 1;
}
