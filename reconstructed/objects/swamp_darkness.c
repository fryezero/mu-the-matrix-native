/* Swamp of Darkness, world 122 (predicate 0x00e543a1). Create 0x00e54429 (type table 0x00e54575/0x00e54591),
 * move 0x00e54646, visual 0x00e5540e. */
#include "worlds_q_internal.h"

int mu_swamp_darkness_create(uint8_t *o, const mu_q_inputs *in)
{
    if (in->world != 122 || !o)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 0: case 1: case 2: case 3: case 8: case 9: case 14: case 15: case 16: case 17: case 19: case 27: case 30:
    case 33: case 36: case 48: case 49: case 50: case 51: case 53: case 58: case 61: case 63: case 64: case 68:
    case 74: case 75: case 78: case 92: case 93: case 94: case 95: case 100: case 103: case 105: case 109: case 110:
    case 111: case 113: case 116: case 117: case 124:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f);
        break;
    case 131: case 132: case 133:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f);
        mu_obj_set_i32(o, 0x64, (int32_t)q_rand_range(in, 4.0f, 10.0f, 1));   /* ftol 0x0191c5e0 */
        break;
    case 39: case 41: case 107: case 108: case 112:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    case 88:   /* the handler's variant byte picks the type */
        mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f);
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        switch (in->handler->swamp_variant) {
        case 0: mu_obj_set_i32(o, MU_OBJF_TYPE, 108); break;
        case 1: mu_obj_set_i32(o, MU_OBJF_TYPE, 88); break;
        case 2: mu_obj_set_i32(o, MU_OBJF_TYPE, 107); break;
        default: break;
        }
        break;
    case 173: case 174:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f);
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    default:
        if (t == 83 || (t >= 161 && t <= 180))
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    }
    return 1;
}

int mu_swamp_darkness_move(uint8_t *o, const mu_q_inputs *in)
{
    if (in->world != 122 || !o)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t < 131 || t > 133)
        return 0;
    const uint8_t *record = q_action_at(in, o);
    if (!record || !q_action_ended(o, record))
        return 1;
    if (mu_obj_i32(o, 0x64) <= 0) {
        mu_obj_set_i32(o, 0x64, (int32_t)q_rand_range(in, 15.0f, 25.0f, 1));
        q_set_action(in, o, 1);
    } else {
        q_set_action(in, o, 0);
        mu_obj_set_i32(o, 0x64, mu_obj_i32(o, 0x64) - 1);
    }
    return 1;
}

int mu_swamp_darkness_visual(const uint8_t *o, int32_t index, int model_present, const mu_q_inputs *in, mu_obj_log *log)
{
    if (in->world != 122 || !o || !model_present)
        return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 83:
        if (in->rand_fn(in->context) % 100 == 0) {
            const float white[3] = {1.0f, 1.0f, 1.0f};
            q_effect(log, index, o, 0x59a, white, 3, 0);
        }
        break;
    case 176: {
        const uint32_t phase = in->now_ms % 1024u;
        if (in->rand_fn(in->context) % 5 == 1 && phase < 30u) {
            const float dim[3] = {0.100000001f, 0.100000001f, 0.100000001f};
            q_effect(log, index, o, 0x199, dim, 0, (uint16_t)wb_int(mu_obj_f32(o, MU_OBJF_SCALE)));
        }
        break;
    }
    default:
        break;
    }
    return 1;
}
