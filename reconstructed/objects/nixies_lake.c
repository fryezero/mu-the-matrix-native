/* Nixies Lake, world 113. Slots 0x00e3441c/0x00e3473f; predicate 0x00e34404. */
#include "worlds_n.h"
#include "worlds_b_internal.h"
int mu_nixies_create(uint8_t *o, int32_t world)
{
    if (world != 113 || !o) return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0: case 1: case 2: case 3: case 7: case 8: case 10: case 11: case 23: case 33: case 34:
    case 51: case 52: case 70: case 71: case 78: case 80: case 84: case 85: case 99: case 102:
    case 115: case 118: case 128: case 130: case 133: case 146: case 150: case 157: case 159:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f); break;
    case 20: case 37: case 38: case 39: case 40: case 41: case 42: case 44: case 45: case 53:
    case 105: case 107: case 108: case 114: case 126: case 139: case 141:
        o[MU_OBJF_AFTER_CHARACTER] = 1; break;
    case 21: case 113: case 117: case 119: case 120: case 121: case 122: case 123: case 161:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2); break;
    case 106:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f);
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    default: break;
    }
    return 1;
}
int mu_nixies_move(uint8_t *o, const mu_obj_move_inputs *in)
{
    if (in->world != 113 || !o || mu_obj_i32(o, MU_OBJF_TYPE) != 77) return 0;
    mu_obj_set_f32(o, MU_OBJF_BLEND_V, (float)(wb_int(in->time) % 2000) * 0.0005f);
    return 1;
}
