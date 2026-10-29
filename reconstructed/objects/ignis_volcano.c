/* Ignis Volcano, world 138. Create 0x00e05afe, move 0x00e05d76, visual 0x00e07081; predicate 0x00e0895c. */
#include "worlds_p2.h"
#include "worlds_b_internal.h"
int mu_ignis_create(uint8_t *o, int32_t index, int32_t world, int32_t model_actions, mu_obj_log *log)
{
    if (world != 138 || !o) return 0;
    if (model_actions > 0) mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.16f);   /* written once per action */
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0: case 1: case 2: case 3: case 4: case 5: case 6: case 7: case 8: case 9: case 10: case 11: case 13:
    case 16: case 17: case 29: case 30: case 46: case 58: case 59: case 95: case 153: case 154: case 157:
    case 171: case 173:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -800.0f); break;
    case 45:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -800.0f);
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    case 79: case 148:
        wb_arg(wb_event(log, MU_OBJ_CALL_MODEL_STREAM, index), 0); break;
    case 88: case 126: case 127: case 136: case 146: case 147: case 175: case 176:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2); break;
    default: break;
    }
    return 1;
}
int mu_ignis_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    if (in->world != 138 || !o) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 88) {
        const float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f;
        wb_light(log, index, o, s * 0.8f, s * 0.3f, s * 0.04f, 3);
        return 1;
    }
    if (t != 177) return 0;
    const uint16_t action = mu_obj_u16(o, MU_OBJF_ACTION);
    const float frame = mu_obj_f32(o, MU_OBJF_FRAME);
    if ((action == 1 && 8.0f > frame) || (action == 3 && frame > 28.0f)) {
        wb_sound(log, index, 0x570, 1, 0);
        return 1;
    }
    return 0;
}
int mu_ignis_visual(const uint8_t *o, int32_t index)
{
    (void)o; (void)index;
    return 0;
}
