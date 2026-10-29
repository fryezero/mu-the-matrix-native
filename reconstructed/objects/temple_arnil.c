/* Temple of Arnil, world 133 (0x85), vtable 0x01aa62a0. Create 0x00d809fc, move 0x00d80c9c, visual 0x00d81c2c;
 * world predicate 0x00d83ada. */
#include "worlds_r.h"
int mu_temple_arnil_create(uint8_t *o, int32_t world)
{
    if (world != 0x85 || !o)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 6:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        o[MU_OBJF_LIGHT_FULL] = 0;
        o[MU_OBJF_LIGHT_ENABLE] = 0;
        o[MU_OBJF_VISIBLE] = 0;
        break;
    case 0x0e: case 0x7b: case 0x80: case 0x84: case 0x86: case 0x8f:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    default:
        if (t >= 0xa0 && t <= 0xa9)   /* 0xa0, 0xa1 and the jump table 0x00d80c7c */
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    }
    switch (t) {
    case 1: case 2: case 3: case 5: case 7: case 8: case 0xa: case 0xb: case 0x10: case 0x11: case 0x16: case 0x17:
    case 0x1d: case 0x1e: case 0x1f: case 0x3d: case 0x40: case 0x41: case 0x42: case 0x43: case 0x4b: case 0x50:
    case 0x51: case 0x73: case 0x7e: case 0x80: case 0x81: case 0x85: case 0x88: case 0x89: case 0x91: case 0x94:
    case 0x9d: case 0xac:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -500.0f);
        break;
    default:
        break;
    }
    return 1;
}

int mu_temple_arnil_move(const uint8_t *o, int32_t world, int has_model)
{
    return world == 0x85 && o && has_model;
}

int mu_temple_arnil_visual(const uint8_t *o, int present)
{
    return o && present;
}
