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
