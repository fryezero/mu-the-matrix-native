/* Scorched Canyon, world 131 (0x83), vtable 0x01aab4d4. Create 0x00e432d9, move 0x00e4370c, visual 0x00e43f8e;
 * world predicate 0x00e45d40. */
#include "worlds_r.h"
#include "worlds_b_internal.h"
int mu_scorched_canyon_create(uint8_t *o, int32_t world, mu_obj_rand_fn rnd, void *c)
{
    if (world != 0x83 || !o)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 0x0c: case 0x16: case 0x19: case 0x1a: case 0x1c: case 0x22: case 0x26: case 0x27: case 0x2c: case 0x2d:
    case 0x32: case 0x3b: case 0x3c: case 0x3d: case 0x3f: case 0x43: case 0x52: case 0x53: case 0x54: case 0x55:
    case 0x58: case 0x5f: case 0x60: case 0x62: case 0x6a: case 0x72: case 0x77: case 0x78: case 0x79: case 0x7f:
    case 0x80: case 0x83: case 0x85: case 0x8d: case 0x98: case 0x9a: case 0x9b: case 0xac: case 0xad:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f);
        break;
    default:
        break;
    }
    switch (t) {
    case 0: case 2: case 3: case 5: case 8: case 0xa: case 0x46: case 0x4b: case 0x4e:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        break;
    default:
        break;
    }
    if (t >= 0xa0 && t <= 0xa7)
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
    switch (t) {
    case 0x4f:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    case 0x6a:
        mu_obj_set_i32(o, 0x60, (rnd(c) % 18 + 1) * 10);
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    case 0x88: case 0x8a: case 0x8b: case 0x8c: case 0x8e: case 0x8f: case 0x93: case 0x94: case 0x95:
        mu_obj_set_i32(o, 0x60, (rnd(c) % 18 + 1) * 10);
        break;
    case 0x28: case 0x5a: case 0xa8: case 0xb2: case 0xb3: case 0xb5: case 0xba: case 0xc5: case 0xc7:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    case 0xaa:
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, mu_obj_f32(o, MU_OBJF_VELOCITY) / 3.0f);
        break;
    default:
        break;
    }
    return 1;
}

int mu_scorched_canyon_move(uint8_t *o, int32_t i, int32_t world, int has_model, mu_obj_rand_fn rnd, void *c,
                            mu_obj_log *log)
{
    if (world != 0x83 || !o || !has_model)
        return 0;
    if (mu_obj_i32(o, MU_OBJF_TYPE) == 0xa0) {   /* the Bloody Tarkan 0x51 flicker */
        const float s = (float)(rnd(c) % 4 + 3) * 0.1f;
        wb_light(log, i, o, s * 0.8f, s * 0.3f, s * 0.04f, 3);
    }
    return 1;
}

int mu_scorched_canyon_visual(const uint8_t *o, int present)
{
    return o && present;
}
