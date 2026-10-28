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
